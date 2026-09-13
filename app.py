"""ZeroGPU hosting: stateless GPU work, owner-bound memory in the parent process."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ['HF_HOME'] = str(ROOT / 'models/hf')
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'
os.environ['GRADIO_ANALYTICS_ENABLED'] = 'False'
os.environ['GRADIO_RUN_HISTORY'] = 'False'
os.environ['GRADIO_SSR_MODE'] = 'False'

# Must precede torch/transformers; ZeroGPU emulates startup CUDA.
import spaces
import gradio as gr
from fastapi.staticfiles import StaticFiles
from backend.app import create_app
from backend.gpu_tickets import GPUTickets


def prepare_models():
    """Use a single cache and fetch only required immutable model artifacts."""
    import json
    from huggingface_hub import snapshot_download
    from ai.config import EMBED_MODEL, LOCK
    from ai.candidate_download import validate_snapshot
    hub = ROOT / 'models/hf/hub'
    hub.mkdir(parents=True, exist_ok=True)
    patterns = ['*.safetensors', '*.json', '*.jinja', 'vocab.*', 'merges.txt', 'tokenizer.model', 'LICENSE*', 'NOTICE*']
    snapshot_download(EMBED_MODEL, revision=LOCK[EMBED_MODEL]['revision'],
                      cache_dir=str(hub), allow_patterns=patterns, max_workers=3)
    spec = json.loads((ROOT / 'ai/serving.json').read_text())
    entry = json.loads((ROOT / 'ai/candidates.json').read_text())[spec['model']]
    snapshot = snapshot_download(spec['model'], revision=entry['revision'],
                                 cache_dir=str(hub), allow_patterns=patterns, max_workers=3)
    validate_snapshot(Path(snapshot), entry)


def build_app(runtime, public_origin=None):
    tickets = GPUTickets()
    backend = create_app(ai_runtime=runtime, public_origin=public_origin, gpu_tickets=tickets)

    @backend.get('/healthz')
    @backend.get('/health')
    @backend.get('/ready')
    def health_probe():
        return {'status': 'ok', 'model_ready': bool(runtime.ready)}

    def reply(ticket: str, request: gr.Request):
        # Gradio sees only an opaque ticket and a fixed status string.
        # Session updates remain in the parent, never inside the GPU fork.
        if not request.username or len(ticket) != 43:
            return 'unavailable'
        try:
            return backend.state.complete_ticket(ticket, request.username)
        except Exception:
            return 'unavailable'

    with gr.Blocks(analytics_enabled=False) as demo:
        ticket_in = gr.Textbox(visible=False)
        status_out = gr.Textbox(visible=False)
        gr.Button('Run', visible=False).click(reply, [ticket_in], [status_out],
                                             api_name='reply', concurrency_limit=1)
    demo.queue(max_size=4, default_concurrency_limit=1)
    app = gr.mount_gradio_app(backend, demo, path='/api/gpu',
        auth_dependency=backend.state.gpu_owner, ssr_mode=False,
        run_history=False, show_error=False, enable_monitoring=False, mcp_server=False,
        blocked_paths=[str(ROOT / name) for name in ('models', 'data', 'private', 'work')],
        max_file_size=1, footer_links=[])
    static = ROOT / 'web/dist/client'
    if not (static / 'index.html').is_file():
        raise RuntimeError('The static frontend build is missing.')
    app.mount('/', StaticFiles(directory=str(static), html=True), name='static')
    return app


def main():
    import uvicorn
    from ai.serving import load_selected_runtime
    from spaces.config import Config
    hosted = bool(os.environ.get('SPACE_ID'))
    if hosted:
        prepare_models()
    runtime = load_selected_runtime(profile='hosted' if hosted else 'local')
    original_graph = runtime.graph

    @spaces.GPU(duration=60)
    def checked_generation(state):
        try:
            result = original_graph.invoke(state, config={'callbacks': [], 'recursion_limit': 8})
            return {'result': result['result']}
        except Exception as exc:
            # Provider traceback formatting must not expose a user's prompt.
            print('GPU generation failed: ' + type(exc).__name__, flush=True)
            return {'unavailable': True}

    class GPUExecution:
        def invoke(self, state, config=None):
            result = checked_generation(state)
            if 'result' not in result:
                raise RuntimeError('GPU generation unavailable')
            return result

    runtime.graph = GPUExecution()
    origin = os.environ.get('SPACE_HOST')
    if origin and not origin.startswith('https://'):
        origin = 'https://' + origin
    app = build_app(runtime, origin)
    if Config.zero_gpu:
        # spaces==0.51.3 normally does this in Blocks.launch(). For a mounted
        # FastAPI app, perform the same initialization once before uvicorn.
        from spaces.zero import startup
        startup()
    print('Mindful ready: model, adapter, references and GPU handoff loaded.', flush=True)
    uvicorn.run(app, host='0.0.0.0' if hosted else '127.0.0.1',
                port=int(os.environ.get('PORT', '7860')), access_log=False, log_level='warning')


if __name__ == '__main__':
    main()
