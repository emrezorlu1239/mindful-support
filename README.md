# Mindful Support

An experimental, noncommercial application exploring appointment-based AI emotional support, session-only conversation context, source-grounded psychoeducation, and a chat interface with optional gentle background transitions.

**Status: Initial release published to [GitHub](https://github.com/emrezorlu1239/mindful-support) and [Hugging Face Space](https://huggingface.co/spaces/Zorlu5454/mindful-support). Powered by fine-tuned Qwen3.5-text-4B with QLoRA. English is the default; Turkish carries a strong language-limit notice. Zero persistent conversation storage; experimental demo only.** See [model selection](docs/MODEL_SELECTION.md), [language review](docs/FINAL_LANGUAGE_REVIEW.json) and [release readiness](docs/RELEASE_READINESS.md).

This demo is not a psychologist, therapy service, diagnostic tool, or emergency response service. It has no clinical validation or psychologist endorsement. Development evaluation must not be presented as proof of treatment effectiveness.

## Requested experience

- Appointment booking with conversation-language preferences.
- English by default, with a visible English / Türkçe switch.
- Immediate entry when capacity is available, otherwise a FIFO waiting room with people-ahead counts. One active session by default; see [admission behavior](docs/ADMISSION.md).
- A text conversation with optional gentle background transitions; avatars have been retired.
- No long-term conversational memory or reuse of private conversations for training.
- A curated vector knowledge base and a LangGraph response pipeline with input, retrieval, output, and crisis-routing checks.
- Open-weight model evaluation and a separately verified fine-tuning stage.
- Engineering validation followed by the owner's final acceptance test before publication.

See [local AI development](docs/AI_DEVELOPMENT.md), [the architecture proposal](docs/ARCHITECTURE_PROPOSAL.md), [the delivery plan](docs/DELIVERY_PLAN.md), and [the source register](docs/SOURCE_REGISTER.md).

## Run locally on Windows

Requirements: Node.js 24, Python 3.11, and uv (or an equivalent isolated Python environment). No API key is needed for this preparation stage.

From the project folder:

```powershell
uv venv .venv --python 3.11
uv pip sync --python .venv/Scripts/python.exe requirements.lock
cd web
npm ci
cd ..
./Start-Local.ps1
```

Open http://localhost:3000. Both servers bind to loopback only. The launcher stops its backend when the frontend is stopped. It refuses to start when ports 3000 or 8000 are already occupied, without touching existing processes.

To run the services separately in two terminals:

```powershell
# Terminal 1: project root
.venv/Scripts/python.exe -m uvicorn backend.app:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
# Terminal 2: web directory
npm run dev
```

## Check the foundation

```powershell
# Project root
.venv/Scripts/python.exe -m pytest tests/test_bookings.py tests/test_admission.py -q
# web directory
npx tsc --noEmit
npm run build
npm audit
```

Practice bookings use a local SQLite database under the ignored `data/` directory. Use fictional identity details. Reservations are scoped to a 24-hour HttpOnly cookie and cannot be recovered from another browser. Conversation content has no database table; enabled sessions would use bounded process memory. Read [the exact implemented scope and limitations](docs/LOCAL_PREPARATION.md) before treating this as the final AI demo.

## Evaluated AI configuration

The selected model is the pinned `techwithsergiu/Qwen3.5-text-4B-bnb-4bit` derivative with an actual 64-example, three-epoch QLoRA adapter. English scored 9.0/10 and Turkish 6.4/10 on a small manual engineering review of fourteen synthetic scenarios per language. These are not clinical scores or general accuracy measurements.

The measured local median checked response was 8.60 seconds with one model worker. The maximum allocated GPU memory was about 4.42 GiB. The base weights occupy 3.12 GB and the adapter weights 17.1 MB. Cloud latency and quota behavior have not been measured.

The basic environment above supports booking tests. AI also requires the separately pinned AI dependencies, the verified model snapshot, adapter and reference index described in [AI development](docs/AI_DEVELOPMENT.md). On the prepared Windows environment, start with `./Start-Local.ps1 -EnableAI`. Activation fails if the serving receipt, evaluated code, runtime packages or weights do not match.

## Publication

The planned free host is Hugging Face ZeroGPU, subject to provider eligibility, Gradio integration and quotas. The laptop will not act as the public server. Publication follows engineering validation and the owner's final acceptance test. Follow [release readiness](docs/RELEASE_READINESS.md) for the outstanding work; there is no automatic deployment.

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and the [source register](docs/SOURCE_REGISTER.md). Model, reference, synthetic-data and dependency licenses are separate from application code.

Credentials belong only in the ignored local `private/API_KEYS.txt` file or an appropriate deployment secret store. Do not commit secrets, conversation records, model weights, or third-party content without redistribution permission.
