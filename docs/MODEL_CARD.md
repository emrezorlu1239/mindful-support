# Mindful experimental adapter

## Intended use

Local, noncommercial development of an English/Turkish emotional-support interface for adults. The model is an AI system, not a psychologist. It must not provide diagnosis, medication decisions, psychotherapy or emergency response. Public deployment has not been approved.

## Base and adaptation

- Base: third-party text-only NF4 derivative `techwithsergiu/Qwen3.5-text-4B-bnb-4bit`, revision `70db06548a71a853f12fc10b63d8c0961642ed74`, derived from Qwen/Qwen3.5-4B with Apache-2.0 provenance.
- Method: NF4 QLoRA, rank 8, alpha 16, targets `q_proj`, `v_proj`, `in_proj_qkv`, `in_proj_z`.
- Data: 64 original synthetic English/Turkish records under CC0; no real user transcripts or NIMH text in gradient updates.
- Actual training: three epochs, 48 optimizer steps, 4,259,840 trainable parameters, 128 changed tensors, seed 42; 434.27 seconds and 4,932 MiB peak allocated GPU memory on an RTX 5060 Laptop GPU.
- Adapter SHA-256: `a83372b328469288983a9403f075e85b6ab37e110cd440758d451938367d7000`.
- Evidence: TRAINING_Qwen3.5-text-4B-bnb-4bit.json. Historical 1.7B and other rejected experiments remain separate.

## Runtime and references

The application retrieves reviewed NIMH public-information passages using multilingual E5 embeddings. Source vectors are persisted; user queries and conversation content are not written to the vector collection. A LangGraph pipeline validates the draft schema, source IDs and selected output rules and requests a second review from the same model. Clearly matched danger cues receive a fixed human-help response.

The raw adapter is not intended for direct user access. Application checks, session access controls and limitations are part of this experiment.

## Evaluation

**Selected for bounded local demonstration:** English 9.0/10 and Turkish 6.4/10 on fourteen manually reviewed synthetic scenarios per language, including two fixed emergency replies in each language. Turkish uses a strong language-limit notice. See FINAL_LANGUAGE_REVIEW.json for all scores and remaining defects.

The final held-out prompts were not used in gradient updates. Once first-run failures were used to improve routing and filtering, repeated results became regression evidence. These scores describe a small development sample; they do not establish population-level quality, clinical effectiveness or safety. Resource and real HTTP integration checks passed. Public provider compatibility and final owner acceptance remain pending.

A passing local engineering gate is not clinical validation or public-release approval. Small synthetic samples, rule-based checks and a reviewer sharing the generator's model can miss harmful or misleading replies. Turkish quality must be examined separately from English quality.

## Known limits

The model can misunderstand context, produce awkward Turkish, invent information or miss indirect danger. It cannot verify a user's age or location, contact emergency services, or establish therapeutic effectiveness. Color choices are optional decoration and do not diagnose or treat psychological conditions.

Conversation memory is process-local and bounded, with no conversation checkpoint or training collection. This is an application retention policy, not a guarantee of forensic memory erasure.

## Distribution

Weights and caches are excluded from the Git repository. Retain the base model's license and notices with any future authorized adapter distribution. The training dataset, source passages, embeddings, code and dependencies have separate licensing requirements. See SOURCE_REGISTER.md and DEPENDENCY_SECURITY.md before preparing a release.
