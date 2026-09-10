# Selected model and historical experiments

## Final selection — 2026-09-10

Selected for bounded local demonstration: `techwithsergiu/Qwen3.5-text-4B-bnb-4bit`, revision `70db06548a71a853f12fc10b63d8c0961642ed74`, with the project's actually trained QLoRA adapter. No further model families will be tested under the owner's final-candidate instruction.

- Training: 64 original synthetic records, three epochs, 48 optimizer steps, 128 changed parameter tensors, 434.27 seconds, 4,932 MiB peak allocated GPU memory.
- Language review: English 9.0/10, Turkish 6.4/10; fourteen synthetic scenarios per language, including two fixed emergency outputs. Manual engineering review only. Turkish has a strong notice because meaning, grammar and responsiveness errors remain.
- Serving measurements: one worker, 8.60-second median checked reply, 11.97-second maximum across twelve measured replies; 4,527 MiB maximum GPU allocation including a separate maximum-context stress case; 3,689 MiB sampled peak process RAM.
- Storage: 3,115,043,601-byte base weights; 17,056,920-byte adapter weights; 37,066,596-byte complete adapter directory. Only the selected artifact belongs in a future serving image.
- Real HTTP integration passed. Hash-bound local activation is configured in `ai/serving.json` and `docs/SERVING_APPROVAL.json`.
- Public deployment is still pending Gradio ZeroGPU integration, runtime checks and final owner acceptance. Local speed is not a cloud measurement.

See FINAL_LANGUAGE_REVIEW.json, PERFORMANCE_Qwen3.5-text-4B-bnb-4bit.json and AI_HTTP_INTEGRATION.json for actual evidence. Earlier reports below are historical and do not override this selection.

## Historical decision record

# Model selection: quality and serving cost

Updated 2026-09-09. No deployment or account mutation has occurred.

The goal is a model with acceptable English/Turkish support behavior **and** a bounded serving footprint. Parameter count alone is not a selection criterion. No candidate is automatically approved by a benchmark score.

## Current evidence

| Candidate / experiment | Local result | Decision |
| --- | --- | --- |
| Qwen3-1.7B, base | Weak Turkish and unstable structured output | Rejected |
| Qwen3-1.7B, two-epoch LoRA | Actual fine-tuning completed; repetition and poor Turkish | Rejected |
| Qwen3-1.7B, six-epoch LoRA | Automatic gates passed, direct semantic/grounding review failed | Rejected |
| Qwen3.5-2B, BF16 | 4.55 GB source weights; 4,320 MiB peak CUDA allocation; approximately 3.63 s median checked-response time over 12 development scenarios | Rejected for incoherent or misleading Turkish and unjustified citations |
| Qwen3-4B-Instruct-2507, NF4 base | 2.65 GB weights; 2,774 MiB peak allocation; 5.91 s median / 10.64 s maximum checked reply in 12 regressions | Rejected for Turkish meaning errors and inappropriate citations |
| Qwen3-4B-Instruct-2507, NF4 QLoRA | Actual 64-example / three-epoch training; 11.8 MB adapter; 2,786 MiB inference allocation; 5.94 s median checked reply | Rejected: invented session memory and poor Turkish remain |
| Qwen3.5-4B, original multimodal | 9.32 GB original source weights; original download paused | Superseded in screening by the smaller text-only derivative below |
| Qwen3.5-text-4B, NF4 | Pinned third-party text-only derivative; 3.115 GB weights downloading | Not yet evaluated |

The owner requested scores out of ten. Subjective suitability ratings communicated for the first three experiments were 2/10, 3/10 and 4/10 respectively. These are not published benchmark scores or clinical efficacy scores. Future decisions must retain concrete failures and resource measurements alongside any rating.

The existing regression cases are reused for initial screening. A winning candidate must then undergo real adaptation, renewed regression tests, fresh single/multi-turn cases, direct output review and measured API integration before activation.

The 4B-Instruct adapter changed 144 trainable tensors in 48 optimizer steps (184 seconds, 3,762 MiB peak training allocation). Its failure is retained in CANDIDATE_BASE_REVIEW.json. Both the initial and adapted reports are actual GPU results, not forecast estimates. The small sample gives no reliable production tail-latency estimate.

After rejecting that adapter, the development pipeline added an explicit session-memory rule and separate safety, coherence, citation-grounding and responsiveness review flags. Future end-to-end comparisons therefore reflect this updated system, not an isolated base-model benchmark. The separate review pass still uses the same model and can make correlated errors; explicit fields alone do not establish semantic correctness. Candidate holdout outputs have not yet been inspected.

## Resource measurements required

- Actual installed model/adapter bytes, distinct from original download size.
- Model startup time and peak GPU memory; CPU process memory for the final serving configuration.
- End-to-end time for a checked reply, including retrieval and the output review pass.
- Behavior at the maximum allowed prompt and output lengths, and repeated requests without growing conversation storage.
- Quantized artifact reload and response-quality regression; do not assume reduced precision is free of quality loss.
- One active session / one in-flight generation initially. Increase only with measured headroom.

Candidate downloads stay in ignored models/. Only the selected artifact belongs in a future model service; caches, rejected models and development reports do not need to be bundled into its runtime image. GitHub code will not contain model weights.

## Free hosting constraints

The [current ZeroGPU documentation](https://huggingface.co/docs/hub/spaces-zerogpu) describes 48 GB VRAM for the default large allocation and 96 GB for xlarge, which charges twice the quota. The default allocation is the target. This hardware is different from the owner's 8 GB laptop; local latency is not a hosted latency measurement.

A qualifying free account may host up to two Gradio ZeroGPU Spaces. Account entitlement is not yet verified. GPU quotas are currently two minutes per unauthenticated visitor tier and five minutes per free-account tier per daily window. How visitor identity reaches a custom frontend/backend must be verified; using one backend token for every visitor must not be presented as giving every visitor a separate quota.

Use GPU allocation per checked answer, not for an entire 20-minute appointment. Combine draft generation and its review within one allocation to avoid two queue entries. Keep retrieval and bounded session ownership on the application side. Preload the model following the provider's CUDA emulation instructions rather than reloading it per message. No persistent KV cache or conversation embeddings are planned.

Queueing limits instantaneous work; it does not create daily quota, guarantee availability, or replace overload/timeout handling. Quota exhaustion must return a clear unavailable state rather than permit unlimited retries. Real provider integration remains a pre-release task, without publishing before owner approval.

## Candidate provenance

Pinned revisions, file sizes and SHA-256 values are in ai/candidates.json. The Unsloth NF4 artifact is a **third-party quantization** of Qwen's model, not an official Qwen weight release. Its model card links the upstream Apache-2.0 license. It is loaded through Transformers and bitsandbytes with remote Python execution disabled; Unsloth's training runtime is not installed.

The [techwithsergiu text-only NF4 artifact](https://huggingface.co/techwithsergiu/Qwen3.5-text-4B-bnb-4bit) is also a third-party derivative, with the visual tower removed and Apache-2.0 upstream provenance documented by its distributor. No remote Python from that repository is executed. Actual loading, quality and memory must be checked before selecting it.

Sources: [Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B), [Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B), [Qwen3-4B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507), [Unsloth NF4 distribution](https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-bnb-4bit), [bitsandbytes platform support](https://huggingface.co/docs/bitsandbytes/installation).
