# Delivery plan

## Design update: implemented interface

The avatar/chat selection step and avatar rendering are removed. Booking now has two steps. The chat client supports optional gentle background transitions from a checked response, a manual off control and reduced-motion preferences. No diagnosis or therapeutic color effect is claimed. Actual AI-driven behavior depends on the evaluated model becoming available.

Form validation must follow the selected interface language independently of the browser's language. Required-name errors appear next to their fields, update when the language changes, and focus the first invalid field.

All phases remain unpublished until the owner completes final acceptance and approves publication. Confirmed scope: simple noncommercial experimental demo, zero paid-service budget, international adults aged 18+, Turkish and English, and a genuinely fine-tuned model in the first completed AI release. No psychologist collaborator is available; clinical review is not a prerequisite for this experimental scope. The owner rejects using their computer as the public server. The owner subsequently authorized local demo preparation while cloud eligibility is pending; no external API keys are required for that local milestone. See LOCAL_PREPARATION.md for completed work and remaining AI tasks.

| Phase | Work | Exit evidence |
| --- | --- | --- |
| 0. Discovery | Confirm budget, scope, training order, hosting, and complete credential/service inventory | Owner decisions and configuration requirements documented before app implementation |
| 1. Foundation | Isolated web/backend environments, configuration validation, local database and model | Reproducible local startup and model hardware benchmark |
| 2. Knowledge and AI | Licensed source ingestion, vector retrieval, LangGraph checks, chosen fine-tuning stage | Provenance records, actual retrieval, evaluated responses; trained artifact only if training actually ran |
| 3. Product | Booking and approval flow, scoped access, chat with optional background transitions, chosen languages, notices | Complete local user journey with real backend/model integration |
| 4. Engineering verification | Authorization, concurrent slot booking, token budgets, expiry, privacy, injection resistance, accessibility, responsiveness, load, dependency and license review | Recorded results, fixed blocking defects, repeatable evaluation suite |
| 5. Release preparation | English README, architecture, setup, security policy, contribution guide, third-party notices, CI, deployment instructions and configuration | Concrete publication candidate, no secrets or private data, legal/clinical review status disclosed |
| 6. Owner acceptance | Owner tests the complete product locally after engineering verification | Explicit test outcome; fix issues and repeat relevant checks and acceptance if needed |
| 7. Publication | Create the professional English GitHub repository, push reviewed code, deploy the approved release | Only after explicit publication approval; production smoke checks and working links |

Keep final user testing immediately before publication, with routine post-deployment health checks as an operational necessity. Do not enable automatic deployment on push ahead of approval. Do not represent a demo, mocked reply, unexecuted training script, or unchecked model as a complete implementation.

## Services and credentials

- GitHub CLI is already authenticated. No extra GitHub plugin or personal token is currently necessary.
- The current local Transformers/PEFT experiment needs no API key. The owner authorized local GPU training; Ollama is not used by this implementation.
- The small reference collection uses SQLite vectors and pinned multilingual E5 embeddings; no managed database or database API key is needed.
- The hosted model/backend needs an infrastructure choice based on budget and data region before its required endpoint and credentials can be finalized.
- A Hugging Face token is conditional on private/gated model access or private artifact publishing, not required merely to evaluate the public candidate.
- Do not request email/SMS, paid avatar, voice, analytics, or unrelated connectors unless their features are explicitly added.
- Do not buy services or put provider secrets in the browser bundle. The local credential form is `private/API_KEYS.txt` and is ignored by Git.
