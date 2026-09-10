"""Hugging Face ZeroGPU Space entry point.

Combines the FastAPI booking/chat backend with a Gradio GPU shim.
The Gradio app only handles the GPU allocation handoff; all session state
and conversation content remain in the FastAPI layer.
"""
import os
import sys
import threading

# On ZeroGPU the spaces package patches torch.cuda.is_available() globally.
# Import it before any torch-using module so the patch is in place.
try:
    import spaces  # available on ZeroGPU Spaces  # noqa: F401
    _zerogpu = True
except ImportError:
    _zerogpu = False

from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import gradio as gr
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from backend.app import create_app, COOKIE
from backend.gpu_tickets import GPUTickets

os.environ.setdefault("MINDFUL_ENABLE_AI", "1")
os.environ.setdefault("MINDFUL_DB_PATH", str(ROOT / "data" / "appointments.sqlite"))
os.environ["HF_HOME"] = str(ROOT / "models" / "hf")
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

PUBLIC_ORIGIN = os.environ.get("SPACE_HOST")
if PUBLIC_ORIGIN and not PUBLIC_ORIGIN.startswith("https://"):
    PUBLIC_ORIGIN = "https://" + PUBLIC_ORIGIN

gpu_tickets = GPUTickets()

def _prepare_space():
    """Ensure pinned models and knowledge index are present at startup."""
    import json
    from huggingface_hub import snapshot_download
    from ai.config import EMBED_MODEL, LOCK

    # 1. Pinned embedding model
    e5_rev = LOCK[EMBED_MODEL]["revision"]
    e5_snapshot = ROOT / "models" / "hf" / "hub" / ("models--" + EMBED_MODEL.replace("/", "--")) / "snapshots" / e5_rev
    if not e5_snapshot.exists():
        print(f"[Startup] Downloading embedding model {EMBED_MODEL}...", flush=True)
        snapshot_download(
            EMBED_MODEL,
            revision=e5_rev,
            max_workers=3,
        )

    # 2. Vector knowledge database
    index_path = ROOT / "data" / "knowledge.sqlite"
    if not index_path.exists():
        print("[Startup] Building knowledge index...", flush=True)
        from ai.retrieval import Embedder, build_index
        build_index(Embedder(), path=index_path)

    # 3. Pinned text candidate model
    spec = json.loads((ROOT / "ai" / "serving.json").read_text(encoding="utf-8"))
    candidates = json.loads((ROOT / "ai" / "candidates.json").read_text(encoding="utf-8"))
    cand_entry = candidates[spec["model"]]
    model_snapshot = ROOT / "models" / "hf" / "hub" / ("models--" + spec["model"].replace("/", "--")) / "snapshots" / cand_entry["revision"]
    if not model_snapshot.exists():
        print(f"[Startup] Downloading candidate model {spec['model']}...", flush=True)
        from ai.candidate_download import validate_snapshot
        path = snapshot_download(
            spec["model"],
            revision=cand_entry["revision"],
            max_workers=3,
            allow_patterns=["*.safetensors", "*.json", "*.jinja", "vocab.*", "merges.txt", "LICENSE", "README.md"],
        )
        validate_snapshot(path, cand_entry)
        print("[Startup] Model download and validation complete.", flush=True)

if os.environ.get("MINDFUL_ENABLE_AI") == "1":
    _prepare_space()

fastapi_app = create_app(
    public_origin=PUBLIC_ORIGIN,
    gpu_tickets=gpu_tickets,
)

# ---------------------------------------------------------------------------
# Gradio GPU shim
# The shim receives an opaque ticket (not the message), runs the compute
# under @spaces.GPU, and stores the result back via gpu_tickets.complete().
# Conversation content never passes through Gradio or its queue.
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
                import hashlib
                token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
                # Validate ownership via the FastAPI layer's helper.
                gpu_owner_fn = getattr(fastapi_app.state, "gpu_owner", None)
                if gpu_owner_fn is None:
                    return "not_ready"
                # Build a minimal request-like object for the owner check.
                class _FakeRequest:
                    def __init__(self, token):
                        self.cookies = {COOKIE: token}
                _fake = _FakeRequest(raw_token)
                current = gpu_owner_fn(_fake)
        except Exception:
            return "auth_error"
    if current is None:
        return "unauthorized"
    complete_fn = getattr(fastapi_app.state, "complete_ticket", None)
    if complete_fn is None:
        return "not_ready"
    return complete_fn(ticket, current)


if _zerogpu:
    # ZeroGPU: decorate with @spaces.GPU so the A10G is allocated for inference.
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

# Mount Gradio under /api/gpu (matches chat-transport.ts expectation).
app = gr.mount_gradio_app(fastapi_app, _gradio_blocks, path="/api/gpu")

# Serve the pre-built static frontend.
_static_dir = ROOT / "web" / "dist" / "client"
if _static_dir.exists():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")

# ---------------------------------------------------------------------------
# Local development helper: run with `python app.py`
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
