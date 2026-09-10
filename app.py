"""Hugging Face ZeroGPU Space entry point.

Combines the FastAPI booking/chat backend with a Gradio GPU shim.
The Gradio app only handles the GPU allocation handoff; all session state
and conversation content remain in the FastAPI layer.

ZeroGPU key constraint: CUDA is only available inside @spaces.GPU functions.
The AI model is loaded lazily on the first GPU call, not at startup.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Set HF_HOME and other env vars before any huggingface/transformers import.
os.environ.setdefault("MINDFUL_ENABLE_AI", "1")
os.environ.setdefault("MINDFUL_DB_PATH", str(ROOT / "data" / "appointments.sqlite"))
os.environ["HF_HOME"] = str(ROOT / "models" / "hf")
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["GRADIO_SSR_MODE"] = "False"

# On ZeroGPU the spaces package patches torch.cuda.is_available() globally.
# Import it before any torch-using module so the patch is in place.
try:
    import spaces  # available on ZeroGPU Spaces  # noqa: F401
    _zerogpu = True
except ImportError:
    _zerogpu = False

import threading
import gradio as gr
from fastapi.staticfiles import StaticFiles

from backend.app import create_app, COOKIE
from backend.gpu_tickets import GPUTickets

PUBLIC_ORIGIN = os.environ.get("SPACE_HOST")
if PUBLIC_ORIGIN and not PUBLIC_ORIGIN.startswith("https://"):
    PUBLIC_ORIGIN = "https://" + PUBLIC_ORIGIN


# ---------------------------------------------------------------------------
# Lazy AI runtime — loads the model the first time a GPU ticket is processed.
# This defers all CUDA calls to inside the @spaces.GPU decorated handler.
# ---------------------------------------------------------------------------

class _LazyAIRuntime:
    """Wraps the real AIRuntime but defers model loading until first GPU use."""

    def __init__(self):
        self._runtime = None
        self._lock = threading.Lock()
        self._error = None
        self.ready = True  # Accept sessions; model loads on first inference.

    def _get_runtime(self):
        if self._runtime is not None:
            return self._runtime
        if self._error is not None:
            raise self._error
        with self._lock:
            if self._runtime is not None:
                return self._runtime
            if self._error is not None:
                raise self._error
            try:
                from ai.runtime import load_approved_runtime
                self._runtime = load_approved_runtime()
                print("[GPU] AI runtime loaded successfully.", flush=True)
            except Exception as exc:
                self._error = exc
                print(f"[GPU] AI runtime load failed: {exc}", flush=True)
                raise
            return self._runtime

    def prune(self, active_ids):
        if self._runtime:
            self._runtime.prune(active_ids)

    def forget(self, booking_id):
        if self._runtime:
            self._runtime.forget(booking_id)

    def history(self, booking_id):
        if self._runtime:
            return self._runtime.history(booking_id)
        return []

    def respond(self, booking_id, request_id, message, language, is_active):
        return self._get_runtime().respond(booking_id, request_id, message, language, is_active)


# ---------------------------------------------------------------------------
# Startup: download models/index without loading them onto GPU.
# ---------------------------------------------------------------------------

def _prepare_space():
    """Download pinned models and build the knowledge index (CPU, no CUDA)."""
    import json
    import shutil
    from huggingface_hub import snapshot_download
    from ai.config import EMBED_MODEL, LOCK

    hub_dir = ROOT / "models" / "hf" / "hub"
    hub_dir.mkdir(parents=True, exist_ok=True)
    default_hub = Path.home() / ".cache" / "huggingface" / "hub"
    default_hub.mkdir(parents=True, exist_ok=True)

    # 1. Embedding model
    e5_rev = LOCK[EMBED_MODEL]["revision"]
    e5_repo_dir = "models--" + EMBED_MODEL.replace("/", "--")
    e5_snapshot = hub_dir / e5_repo_dir / "snapshots" / e5_rev
    if not e5_snapshot.exists():
        print(f"[Startup] Downloading embedding model {EMBED_MODEL}...", flush=True)
        e5_path = snapshot_download(
            EMBED_MODEL,
            revision=e5_rev,
            cache_dir=str(hub_dir),
            max_workers=3,
        )
        if not e5_snapshot.exists() and Path(e5_path).exists():
            e5_snapshot.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.symlink(e5_path, e5_snapshot)
            except OSError:
                shutil.copytree(e5_path, e5_snapshot)
        # Mirror to ~/.cache so transformers local_files_only=True finds it.
        if not (default_hub / e5_repo_dir).exists():
            try:
                os.symlink(hub_dir / e5_repo_dir, default_hub / e5_repo_dir)
            except OSError:
                shutil.copytree(hub_dir / e5_repo_dir, default_hub / e5_repo_dir)

    # 2. Knowledge index (CPU embedding)
    (ROOT / "data").mkdir(parents=True, exist_ok=True)
    index_path = ROOT / "data" / "knowledge.sqlite"
    if not index_path.exists():
        print("[Startup] Building knowledge index...", flush=True)
        from ai.retrieval import Embedder, build_index
        build_index(Embedder(), path=index_path)

    # 3. Download candidate model weights only (no GPU load)
    spec = json.loads((ROOT / "ai" / "serving.json").read_text(encoding="utf-8"))
    candidates = json.loads((ROOT / "ai" / "candidates.json").read_text(encoding="utf-8"))
    cand_entry = candidates[spec["model"]]
    model_snapshot = hub_dir / ("models--" + spec["model"].replace("/", "--")) / "snapshots" / cand_entry["revision"]
    if not model_snapshot.exists():
        print(f"[Startup] Downloading candidate model {spec['model']}...", flush=True)
        from ai.candidate_download import validate_snapshot
        dl_path = snapshot_download(
            spec["model"],
            revision=cand_entry["revision"],
            cache_dir=str(hub_dir),
            max_workers=3,
            allow_patterns=["*.safetensors", "*.json", "*.jinja", "vocab.*", "merges.txt", "LICENSE", "README.md"],
        )
        if not model_snapshot.exists() and Path(dl_path).exists():
            model_snapshot.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.symlink(dl_path, model_snapshot)
            except OSError:
                shutil.copytree(dl_path, model_snapshot)
        validate_snapshot(model_snapshot, cand_entry)
        print("[Startup] Model download and validation complete.", flush=True)


_lazy_runtime = None
if os.environ.get("MINDFUL_ENABLE_AI") == "1":
    _prepare_space()
    _lazy_runtime = _LazyAIRuntime()

gpu_tickets = GPUTickets()

fastapi_app = create_app(
    public_origin=PUBLIC_ORIGIN,
    gpu_tickets=gpu_tickets,
    ai_runtime=_lazy_runtime,
)

@fastapi_app.get("/healthz")
@fastapi_app.get("/health")
@fastapi_app.get("/ready")
def _hf_health_probe():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Gradio GPU shim — model is loaded here, inside the @spaces.GPU boundary.
# ---------------------------------------------------------------------------

def _gpu_handler(ticket: str, gr_request: gr.Request | None = None) -> str:
    """Accept a ticket and complete the GPU computation for it."""
    if not ticket or len(ticket) > 64:
        return "invalid"
    current = None
    if gr_request is not None:
        try:
            cookies = dict(gr_request.cookies)
            raw_token = cookies.get(COOKIE, "")
            if raw_token:
                gpu_owner_fn = getattr(fastapi_app.state, "gpu_owner", None)
                if gpu_owner_fn is None:
                    return "not_ready"

                class _FakeRequest:
                    def __init__(self, token):
                        self.cookies = {COOKIE: token}

                current = gpu_owner_fn(_FakeRequest(raw_token))
        except Exception:
            return "auth_error"
    if current is None:
        return "unauthorized"
    complete_fn = getattr(fastapi_app.state, "complete_ticket", None)
    if complete_fn is None:
        return "not_ready"
    return complete_fn(ticket, current)


if _zerogpu:
    _gpu_fn = spaces.GPU(duration=120)(_gpu_handler)
else:
    _gpu_fn = _gpu_handler


with gr.Blocks() as _gradio_blocks:
    _ticket_in = gr.Textbox(visible=False, label="ticket")
    _status_out = gr.Textbox(visible=False, label="status")
    _trigger_btn = gr.Button("run", visible=False)
    _trigger_btn.click(
        _gpu_fn,
        inputs=[_ticket_in],
        outputs=[_status_out],
        api_name="reply",
    )

_gradio_blocks.queue()
demo = _gradio_blocks

# Mount Gradio under /api/gpu (matches chat-transport.ts expectation).
app = gr.mount_gradio_app(fastapi_app, _gradio_blocks, path="/api/gpu", ssr_mode=False)

# Serve the pre-built static frontend.
_static_dir = ROOT / "web" / "dist" / "client"
if _static_dir.exists():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")

# ---------------------------------------------------------------------------
# Space entry point & local development runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    host = "0.0.0.0"
    print(f"[Startup] Starting uvicorn server on {host}:{port}...", flush=True)
    uvicorn.run(app, host=host, port=port, log_level="info")
