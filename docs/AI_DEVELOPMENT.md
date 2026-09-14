> Historical development log. For the current selected Qwen3.5 model, use [LOCAL_MODEL_SETUP.md](LOCAL_MODEL_SETUP.md). Earlier rejection and publication status below describe previous stages.

# Local AI development

Updated 2026-09-09. The owner explicitly authorized GPU training and testing on their computer. No Google account, external AI API key or paid service is needed for this local experiment. This permission does not authorize laptop hosting for public users.

## Implemented

- Chat-only, two-step appointment flow. Avatar UI and served assets have been retired.
- A session chat client with optional, slow background transitions. Only a checked reply may select one of four predefined palettes. The user can disable transitions; reduced-motion preferences override them. Colors are not diagnostic or therapeutic indicators.
- Thirteen selected NIMH text passages, with per-item URLs, hashes, dates and reuse review in `knowledge/passages.json`. No NIMH images were copied. The texts are for general information, not specific medical advice.
- Actual multilingual E5 vectors in a local SQLite collection. Query vectors stay in memory. The initial development retrieval check scored 7/8; preserving the journal bullet's source paragraph improved it to 8/8. These are development queries, not an independent or comprehensive benchmark.
- A LangGraph input/retrieval/generation/output-check pipeline with no persistent checkpointer. Obvious crisis signals bypass generation. Other drafts must pass a strict schema, scope checks, citation binding and a separate model review pass before delivery. Failed checks return a bounded fallback.
- One in-flight generation, admission checks before and after generation, at most 20 message pairs per session, at most six previous messages in model context, and a 2,800-token prompt ceiling.
- In-memory session isolation and idempotent request IDs. Leaving, cancelling or expiry clears session memory; an in-flight response is discarded if admission ends.

## Models and training

The pinned model IDs, revisions and declared licenses are recorded in `ai/model-lock.json`:

- Qwen/Qwen3-1.7B: Apache-2.0, used as the base for an experimental LoRA adapter.
- intfloat/multilingual-e5-small: MIT, used for multilingual reference retrieval on CPU.

The bootstrap training file has 48 AI-authored bilingual examples, six validation prompts and 12 held-out test prompts. It contains no user transcripts. Its topics include supportive listening, scope limits, crisis routing, medication boundaries and resistance to professional impersonation. The examples are synthetic and not clinically reviewed.

`ai/train.py` performs actual gradient updates on rank-eight query/value LoRA adapters for six epochs in the latest run (the initial run used two). It masks prompt tokens from the supervised loss, uses a fixed seed and checks that adapter tensors changed. A report is only written after weights have been saved successfully. A recipe, downloaded base model or training loss is not proof of useful or safe behavior.

`ai/evaluate.py` compares base and adapted outputs on the same held-out prompts and exercises the full response pipeline. Predeclared local-demo gates require at least 90% valid JSON, 80% route agreement, all tested crisis cases routed to crisis support, no detected unsafe outputs, and no more than 50% fallback on supportive scenarios. These gates are limited engineering evidence, not clinical validation. The generator and reviewer share a model; their failures can be correlated. Passing these checks does not approve public release.

## Reproduce locally

Use the existing project virtual environment. The CUDA configuration verified here is PyTorch 2.8.0+cu128 on an NVIDIA RTX 5060 Laptop GPU. A different machine may need a different supported PyTorch build.

```powershell
uv pip sync --python .venv/Scripts/python.exe requirements-ai.lock --extra-index-url https://download.pytorch.org/whl/cu128
.\.venv\Scripts\python.exe -m ai.download_model
.\.venv\Scripts\python.exe -m ai.build_knowledge
.\.venv\Scripts\python.exe -m ai.evaluate_retrieval
.\.venv\Scripts\python.exe -m ai.model
.\.venv\Scripts\python.exe -m ai.train
.\.venv\Scripts\python.exe -m ai.evaluate
.\Start-Local.ps1 -EnableAI
```

The fallback downloader `ai.download_resumable` requests byte ranges from the official pinned model URL and verifies full LFS SHA-256 digests before exposing completed weights. Partial files stay in ignored work/model-parts. `ai.run_experiment` waits for those verified weights, then runs the benchmark, training and evaluation in order. Its wait expires after two hours; it never publishes artifacts or enables the server itself.

Building the reference collection requires the reviewed HTML snapshots under ignored work/. The checked-in corpus remains available without re-fetching; call `build_index(Embedder())` from `ai.retrieval` to rebuild vectors from it. To update sources, fetch their canonical URLs, review changes and exceptions, and only then regenerate passages and hashes. Do not scrape arbitrary URLs from user messages.

The local server refuses AI startup when its evaluation receipt is missing or failed, direct output review has not passed, or adapter/configuration hashes, base revision, code, reference corpus or runtime versions differ from the evaluation. Ordinary startup keeps chat disabled. Do not use multiple model workers: the GPU semaphore is process-local. A future hosted architecture needs its own quota-aware, authenticated inference service.

Generation now uses non-thinking sampling (temperature 0.7, top-p 0.8, top-k 20), modest repetition controls and a 384-token output ceiling. A prompt-derived seed makes paired local comparisons repeatable; this does not imply identical results across hardware. An offline Lingua English/Turkish language check supplements the model review and cannot verify meaning or fluency. After development evaluation, run `python -m ai.evaluate_fresh` on the separate fresh scenarios. Automatic checks alone never set the approval flag; record a direct output review with evidence before activation.

## Current limitations

- Two actual training experiments completed. The latest automatic gates passed (100% JSON, 83.3% route agreement, 12.5% support fallback), but direct review of 18 development and 12 fresh outputs rejected the candidate for incoherent Turkish and unsupported suggestions. AI remains disabled in both languages. See AI_OUTPUT_REVIEW.json.
- The data and evaluations are intentionally small. Safety rules do not cover all indirect crisis expressions, languages, dialects or adversarial inputs.
- No psychologist review, clinical effectiveness claim, production authentication, country-specific crisis directory or public load test.
- Prompt and response logging/tracing is disabled, but Python cannot guarantee forensic erasure from memory, swap or crash dumps.
- No GitHub publication, cloud deployment, public tunnel or final owner acceptance has occurred.

## Source references

- [Qwen model card](https://huggingface.co/Qwen/Qwen3-1.7B)
- [E5 model card](https://huggingface.co/intfloat/multilingual-e5-small)
- [NIMH reuse policy](https://www.nimh.nih.gov/site-info/policies)
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [PEFT quantization and adapters](https://huggingface.co/docs/peft/main/en/developer_guides/quantization)
- [Official PyTorch builds](https://pytorch.org/get-started/previous-versions/)
