# Published release — 2026-09-13

The application is live at https://zorlu5454-mindful-support.hf.space/ and source is published at https://github.com/emrezorlu1239/mindful-support. The owner explicitly waived the separate final acceptance test and authorized publication. Live model inference, parent-process session history, ownership and FIFO promotion were verified. See LIVE_DEPLOYMENT_CHECK.json and DEPLOYMENT.md.

The following earlier checklist is historical. It is not a current publication blocker. Quotas, model limitations and the recorded dependency advisory remain relevant.

# Release readiness

Last reviewed: 2026-09-11. **Published.**

## Verified

- Real NF4 QLoRA training completed for the final Qwen3.5 text-only 4B candidate: 64 synthetic examples, 48 optimizer steps and 128 changed parameter tensors.
- Direct engineering review: English 9.0/10; Turkish 6.4/10. These are manual scores on fourteen synthetic scenarios per language, including two fixed emergency replies, not accuracy percentages or clinical results.
- Turkish remains available with a strong language-limit notice in booking and chat. English is the default.
- Single-worker resource measurement: 8.60 seconds median checked reply, 4,527 MiB maximum allocated GPU memory, 3,689 MiB sampled peak process RAM.
- Real HTTP integration passed: admission, waiting counts, ownership, response generation, idempotent retries, queue promotion and session-memory removal.
- 79 Python tests passed. Frontend build, types and lint passed.
- Pre-release source scan verified 0 credentials and no oversized model weights across git-visible files.
- Hugging Face ZeroGPU Space configured (`Zorlu5454/mindful-support`) with Gradio GPU ticket handoff.
- GitHub public repository initialized (`emrezorlu1239/mindful-support`).

## Deployment Architecture

1. **GitHub Repository**: Source code, test suite, evaluation receipts, and build configurations.
2. **Hugging Face Space**: `Zorlu5454/mindful-support` running on ZeroGPU (`zero-a10g`). Model weights are downloaded directly from the Hugging Face Hub at startup; the ~17 MB fine-tuned QLoRA adapter is included in the Space deployment.
3. **Session Boundaries**: In-memory ephemeral conversation state; zero conversation persistence; single-occupancy GPU lock.

