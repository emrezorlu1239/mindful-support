# Architecture proposal

Status: original architecture proposal, superseded where noted by the local implementation in AI_DEVELOPMENT.md (2026-09-09). The implementation uses Transformers/PEFT, Qwen3-1.7B, multilingual E5 vectors in SQLite, LangGraph, chat-only UI and optional background transitions. Ollama, pgvector and avatars below are historical candidates, not active dependencies.

## Confirmed constraints

- Zero paid-service budget. Appointment scheduling is intended to control capacity.
- International audience, adults aged 18+, Turkish and English.
- The first working release must contain an actually fine-tuned model. Do not defer fine-tuning to a later release or substitute prompting/RAG for training.
- Simple noncommercial experimental project and explicitly experimental demo; not a clinical service launch. A psychologist is not available and is not a prerequisite for development. Keep essential safety behavior and honest limitations.
- No public inference or backend hosting on the owner's computer. The supplied Hugging Face account is Zorlu5454. Public API reports creation at 2026-08-10T14:25:49Z; it reaches 30 days on 2026-09-09 at 17:25:49 in Istanbul. Email verification, good standing, and actual ZeroGPU entitlement still need confirmation.

## Decisions awaiting the owner

1. Verify email confirmation and actual Hugging Face ZeroGPU availability after the account-age threshold. Public profile/API verification of Zorlu5454's creation date is complete; this does not prove email verification or final entitlement. Account age limits cloud publication, not local preparation.
2. Finalize the free cloud architecture and credentials before public-hosting work. The owner explicitly authorized local preparation without waiting for these credentials. No local-computer public-hosting fallback. Training location needs separate consideration before a prolonged GPU training job.
3. Suggested privacy improvement: optional surname and optional self-described gender; a display name may be sufficient. Avatar preferences have since been retired. Do not silently change the requested fields.

## Hardware and model feasibility

Read-only inspection found approximately 31.7 GB system RAM, an NVIDIA GeForce RTX 5060 Laptop GPU with 8151 MiB VRAM, and approximately 249.7 GB free on C:. Git, GitHub CLI, Node.js, Python, and Docker commands are available. Their presence does not establish compatible versions, working container services, or training compatibility. Ollama was not found on PATH.

Qwen3-8B is an initial Apache-2.0-licensed candidate, not a clinically validated recommendation or a claim that it is the latest/best model. Its Ollama Q4_K_M package is approximately 5.2 GB. Additional context cache and runtime allocations mean file size is not the VRAM requirement. Measure a bounded context window, single-request concurrency, latency, and Turkish/English behavior before selecting it. Fine-tuning has different memory requirements; do not promise 8B training on this GPU. Evaluate a smaller model or separately budgeted GPU training if necessary.

## Updated free-hosting findings

Hugging Face's current documentation states that creating a new Docker/Gradio compute Space generally requires a paid plan despite CPU Basic having no hourly compute charge. Do not recommend it as unconditionally free. The ZeroGPU exception allows up to two Gradio Spaces for eligible free personal accounts with verified email and account age over 30 days. It has daily GPU quotas and queues; default published quotas are two GPU minutes for unauthenticated use and five for free accounts. These are compute-time quotas, not conversation-duration guarantees. External web-client quota attribution, authentication, endpoint access control, privacy, and compatibility require testing before selecting this architecture. Do not route every end user through the owner's personal access token to assume quota scaling.

The owner rejected laptop hosting. Do not use it as a fallback. The delivery target is a quota-limited experimental demo, not a reliable zero-cost international production service. Frontend hosting and appointment persistence do not eliminate inference costs.

For first-release fine-tuning on the 8 GB laptop GPU, benchmark a smaller Apache-2.0 candidate such as Qwen3-1.7B using a parameter-efficient adapter before deciding whether a larger model fits. Its clinical suitability and Turkish behavior remain unproven. Use compatible GPU tooling isolated to this project; record actual training and held-out evaluation results.

## Proposed components

- Web UI: TypeScript/React using the available Sites-compatible starter if selected for delivery.
- Model orchestration: Python/FastAPI with LangGraph, in a separate process/service.
- Local inference: Ollama serving an explicitly pinned, downloaded open-weight model.
- Knowledge vectors: PostgreSQL with pgvector and a separately licensed multilingual embedding model; Qwen3-Embedding-0.6B is a candidate to benchmark.
- Appointment store: relational records with transactional capacity enforcement.
- Avatar: original licensed assets with controlled expression states; no external avatar API is needed for a text-driven first release. Voice is not currently in scope.

Sites runs server code in a constrained Cloudflare Worker runtime; it cannot host this multi-gigabyte model or the proposed Python/GPU service inside the frontend runtime. A hosted UI therefore needs a separately secured inference/backend service. A single self-hosted deployment is an alternative to decide before implementation. Public production inference is not assumed to be free, and the owner's laptop is not assumed to be an always-on production server.

## Memory and privacy boundary

- The vector database contains reviewed public reference material only. Never embed private user messages into it.
- Conversations exist only for the active session in bounded volatile memory. No persistent LangGraph checkpointer, conversation database, browser localStorage, analytics payload, or tracing body.
- Use explicit end-session and server-enforced expiry; handle abandoned tabs and interrupted connections. JavaScript/Python deletion cannot promise forensic zeroization of RAM. Review swap, crash dumps, reverse-proxy logs, model-server logs, and any external processor before making retention claims.
- A fixed context/token budget is needed even within one session. Removing cross-session memory alone does not prevent context growth or reduce concurrency costs.
- Appointment metadata, access credentials, and consent/version records need a separate minimization and retention policy. Exact duration is pending operational and legal review.
- Sign-in or a securely scoped booking credential must bind the appointment to its owner. Name, gender, and a public appointment ID do not authenticate a session.
- Admission, appointment approval, slot capacity, cancellation, replay protection, time windows, rate limits, and model concurrency must be enforced on the server. Start at a measured capacity, not an arbitrary promise.
- The model endpoint must be private or authenticated, never an unauthenticated public Ollama endpoint.

## Proposed response pipeline

1. Validate appointment ownership, time window, request size, and capacity.
2. Inspect the input for crisis signals and disallowed clinical behavior using layered rules and evaluated classifiers; a keyword list alone is insufficient.
3. For high-risk content, follow reviewed supportive crisis guidance with country-appropriate human resources. Keep urgent-help information accessible outside appointments. Never claim that emergency services have been contacted.
4. Retrieve only from the curated, versioned knowledge collection. Treat retrieved text as untrusted data, not instructions.
5. Generate a supportive draft without diagnosis, prescriptions, professional impersonation, or claims of human feelings or exclusive attachment.
6. Check scope, harmful recommendations, unsupported claims, source identifiers, and expression state. Do not expose unvalidated draft tokens through streaming.
7. Deliver the checked response and relevant verified sources. If the checks fail, provide a conservative fallback; do not return the unchecked draft.

LangGraph is orchestration, retrieval is evidence access, and fine-tuning adjusts learned behavior. None is a guarantee of clinical accuracy or replaces professional evaluation.

## Fine-tuning plan

Use appropriately licensed examples suitable for the explicitly experimental project scope; exclude private therapy transcripts and user sessions. Record that no psychologist reviewed the data when that is the case. Track dataset provenance, permitted use, consent where applicable, train/validation/test separation, deduplication, and contamination checks. Compare the unchanged base model and candidate adapter on the same held-out Turkish/English evaluations. A training recipe alone is not a completed fine-tune. Publish weights or adapters only after their separate license and safety review. Qualified clinical review would be required to substantiate clinical claims, which are outside this project.

## Design direction

A quiet consultation-room atmosphere with restrained typography, warm natural surfaces, generous spacing, and readable contrast. This is a design hypothesis, not a claim that a palette treats mental health conditions.

| Role | Color |
| --- | --- |
| Main background | Warm ivory `#F6F3ED` |
| Surface | White `#FFFFFF` |
| Primary actions | Deep teal `#245B56` |
| Soft accents | Sage `#DCE6DD` |
| Main text | Deep slate `#243332` |
| Secondary text | Slate `#52635F` |
| Warm detail | Muted clay `#C88F73` |

Validate actual combinations for contrast. Use original semi-realistic, nonsexualized, professionally dressed avatars with gender selection independent from the user's gender. Restrict expressions to calm neutral, attentive, and gentle encouragement. Avoid smiles on crisis responses, exaggerated emotional mimicry, and diagnostic readings of the user's emotions. Respect reduced-motion preferences and maintain a fully usable text interface.

## Legal and operational release requirements

Keep documentation proportional to a noncommercial experimental demo: experimental-use notice, concise privacy/retention explanation, third-party attribution, and contact information. Do not make professional review a new prerequisite for developing or presenting this experimental project. Essential privacy and safety behavior still applies, and a disclaimer alone does not establish legal compliance. Avoid collecting real sensitive histories during acceptance testing. Any later clinical/commercial expansion would need a separate scope and appropriate professional review. No automatic claim of KVKK/GDPR compliance or clinical effectiveness.
