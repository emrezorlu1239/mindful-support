# Hosted deployment

- Application: https://zorlu5454-mindful-support.hf.space/
- Space: https://huggingface.co/spaces/Zorlu5454/mindful-support
- Source: https://github.com/emrezorlu1239/mindful-support
- Provider hardware: free `zero-a10g` (ZeroGPU), verified running on 2026-09-13.

## Runtime

The existing React interface is statically exported and served by the same FastAPI application as booking and session APIs. The fixed HTTPS origin uses an HttpOnly, Secure, SameSite=Strict session cookie. Open the direct application URL in a normal tab; browser restrictions on third-party cookies may affect embedded views.

Pinned base weights and the actual QLoRA adapter load at startup using ZeroGPU's CUDA emulation. Adapter Safetensors are read on CPU before assignment to emulated CUDA tensors; direct CUDA file loading is incompatible with the provider's startup environment. Only selected weights are loaded. The reference index contains thirteen public NIMH passages, not conversation embeddings.

The GPU child executes only the checked generation graph. Conversation memory, idempotency, admission and short-lived handoff tickets stay in the parent process. Gradio receives an opaque ticket and returns a fixed status string; it does not receive messages or replies. Run history, analytics, monitoring and model request-body logs are disabled. Private directories are blocked from Gradio file serving.

`spaces==0.51.3` normally initializes ZeroGPU through `Blocks.launch`. This application mounts Gradio into FastAPI, so its entry point calls the same pinned package startup routine explicitly before starting uvicorn. Recheck this integration before upgrading `spaces`.

## Updating

1. Review the change and run relevant Python tests and frontend type/build checks.
2. Build `web` with `MINDFUL_STATIC_EXPORT=1` and `npm run build`.
3. Review the serving receipt when protected code or dependencies change. Keep local and hosted fingerprints separate; do not erase checks to work around mismatches.
4. Run `scripts/check_release_source.py`, commit and push the source to GitHub.
5. Run `scripts/publish_space.py` with the project-specific publishing credential in the ignored local file. The script updates only this existing Space, verifies free hardware and the adapter hash, and excludes private data and rejected weights.
6. Confirm the Space is running and use `scripts/check_live_space.py` for a synthetic end-to-end check. It removes its test bookings afterward.

The adapter and public reference index belong in the Space distribution, not the source repository. Preserve model license notices. No paid hardware fallback or local public tunnel is configured.

## Validation and limitations

81 local Python checks, frontend types and the static build passed. The actual hosted integration returned a checked English model response and verified session ownership and queue promotion. Its elapsed time was about 15 seconds including HTTP and queue overhead. The earlier relocation prompt returned a guarded fallback; hosted replies are not guaranteed to pass the response filter. See LIVE_DEPLOYMENT_CHECK.json.

Free quotas, waiting times and cold starts remain provider constraints. A restart clears volatile conversations and may reset bookings. Turkish has known meaning and fluency errors, disclosed in the interface. The system has no clinical validation. The documented Accelerate advisory remains mitigated by pinned, hash-verified checkpoint paths, not patched upstream.
