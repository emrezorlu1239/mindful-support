# Local model setup

This project is a local experimental web application. No public inference service is operated. Model downloads use public Hugging Face repositories; no API key is required. After setup, inference runs on your GPU without a provider quota.

## Prepared owner computer

Run ./Start-Local.ps1 -EnableAI from the project directory and open http://localhost:3000 . Stop with Ctrl+C. Both services bind to loopback only.

## Fresh Windows clone

Use Python 3.11, Node.js 22.23.2 and a compatible NVIDIA CUDA GPU. The tested machine was an RTX 5060 Laptop GPU. About 4.42 GiB of allocated GPU memory was measured; allow additional device memory and at least 10 GB free disk for environments and public weights. CPU-only inference is not implemented.

Install uv, then run from the repository root:

    uv venv .venv --python 3.11
    uv pip sync --python .venv/Scripts/python.exe requirements-ai.lock --extra-index-url https://download.pytorch.org/whl/cu128
    .venv/Scripts/python.exe scripts/prepare_local_model.py
    cd web
    npm ci
    cd ..
    ./Start-Local.ps1 -EnableAI

The preparation script downloads the exact selected base, pinned E5 embedding model and published adapter, verifies base and adapter integrity, and builds an index from the reviewed public corpus. It does not download rejected candidates or retrain the model. Startup verifies the evaluated package/code/adapter receipt; mismatched environments fail closed.

For the interface and booking preview without GPU inference, install requirements.lock instead and omit -EnableAI. This mode does not generate AI replies.

The adapter is not a complete model. It depends on the pinned 3.12 GB base and the application pipeline. Raw adapter use does not reproduce input/output checks or reference retrieval. No clinical validation is claimed.

Historical AI_DEVELOPMENT.md records earlier rejected experiments; do not follow its old training commands to reproduce the current selected release.

## Latest local verification

On 2026-09-14 the public-artifact preparation script completed without an API key. Two real local HTTP chat requests completed in 16.23 seconds combined: one returned a guarded fallback and one passed output validation. Session history and cleanup passed. See LOCAL_RELEASE_CHECK.json. This is an integration check, not a model quality score or a clean-machine installation test.
