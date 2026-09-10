# Source register

Updated 2026-09-09. Thirteen selected excerpts from NIMH Caring for Your Mental Health and I’m So Stressed Out! have been ingested for general-information retrieval only. knowledge/passages.json records their exact text, hashes, URLs, dates and reuse review. No images or user conversations were ingested. Model revisions are pinned in ai/model-lock.json. Earlier candidate references below are retained as discovery context; AI_DEVELOPMENT.md describes the implemented choices.

| Source | Use and findings | Restrictions / next action |
| --- | --- | --- |
| [Qwen3-8B model card](https://huggingface.co/Qwen/Qwen3-8B) | Open-weight baseline candidate with Apache-2.0 license | Pin revision, preserve required notices, independently evaluate target-language support behavior; no clinical validation implied |
| [Ollama Qwen3-8B package](https://ollama.com/library/qwen3:8b) | Approximately 5.2 GB Q4_K_M package | Pin digest; runtime memory and training requirements differ from download size |
| [Ollama authentication](https://docs.ollama.com/api/authentication) | Local API does not require authentication | Never expose this local endpoint directly to the internet; hosted/private access differs |
| [LangGraph memory](https://docs.langchain.com/oss/python/langgraph/add-memory) | Distinguishes thread and long-term memory mechanisms | Design without persistent conversation checkpoints; explicitly enforce session expiry |
| [pgvector](https://github.com/pgvector/pgvector) | Vector search in PostgreSQL | Pin extension and database versions; separate reference vectors from appointment data |
| [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) | Candidate multilingual embedding model | Verify license at pinned revision and measure retrieval on Turkish and English; not yet selected |
| [NIMH website policies](https://www.nimh.nih.gov/site-info/policies) | Text generally reusable unless otherwise marked; attribution requested | Exclude images and excepted material; avoid implied endorsement or specific medical advice; review each selected page and keep source links current |
| [WHO AI health governance guidance](https://www.who.int/publications/i/item/9789240084759) | Governance and evaluation reference | Reference only; professional authority does not grant automatic commercial training or redistribution rights |
| [KVKK international transfers](https://www.kvkk.gov.tr/Icerik/2053/Yurtdisina-Aktarim) | Official overview of the amended transfer framework | Hosting region and processor contracts require qualified assessment; a checkbox alone is not a compliance plan |

## Additional zero-budget references

- [Spaces overview](https://huggingface.co/docs/hub/spaces-overview): CPU Basic has no hourly cost, but new compute Spaces generally require a paid plan; static hosting and the eligible ZeroGPU exception differ.
- [ZeroGPU requirements and quotas](https://huggingface.co/docs/hub/spaces-zerogpu): verify email/account-age eligibility, Gradio compatibility, daily GPU quotas, and queue behavior before choosing this deployment route.
- [Qwen3-1.7B](https://huggingface.co/Qwen/Qwen3-1.7B): smaller Apache-2.0 model candidate for first-release adapter training on the available hardware; no claim of adequate support quality before measurement.
- [Hugging Face access tokens](https://huggingface.co/docs/hub/security-tokens): prefer narrowly scoped credentials only if that service is selected.

For each future corpus item, record publisher, canonical URL, title, language, revision/retrieval date, hash, exact reuse terms, exceptions, permitted RAG/training/redistribution purposes, reviewer, and review date. Do not label an item expert-reviewed until an actual qualified reviewer has reviewed it.
