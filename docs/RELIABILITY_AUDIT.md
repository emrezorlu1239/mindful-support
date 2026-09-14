# Reliability audit â€” 2026-09-14

Scope: experimental application engineering, not clinical validation or a production availability guarantee.

## Confirmed failures and changes

- Live anonymous inference returned `gpu_quota` even while model health was ready. Health is not a quota probe. Previous exceptions hid this cause behind a generic connection error.
- Provider quota, GPU duration, pending work, expired sessions and network timeouts now have distinct, localized messages. No exception bodies or conversation text are logged.
- The browser now uses pinned `@gradio/client` 2.6.0 for the Hugging Face visitor handshake. Account quota requires opening the application inside the Hugging Face Space and signing in; the standalone hf.space URL does not provide that iframe authentication.
- Short requests reserve a maximum of 30 GPU seconds instead of 60. Requests with more than 1,800 characters of current message plus recent history keep 60 seconds. This changes reservation headroom, not the provider's daily allowance. It does not guarantee a number of messages.
- Fixed emergency guidance bypasses GPU allocation, including when quota is exhausted. This is still not an emergency service.
- The Windows Node 24 build crashed during native shutdown after prerender. Node 22.23.2 completed the same build successfully; `.nvmrc` and CI now select that version. Static export also avoids importing unused hosting plugins.

## Verification

- 85 Python tests passed, including a 40-client simultaneous admission burst: one admitted, 32 queued, seven rejected cleanly; the complete queue drained in FIFO order.
- Actual local Gradio HTTP transport and the official JavaScript client passed three consecutive turns with six history entries, using synthetic fixture inference.
- Failed GPU calls preserve empty history and permit successful retry. Duplicate ticket execution invokes inference only once; expired tickets are removed.
- Session ownership, disconnection, cancellation, hard deadlines, memory bounds, malformed requests, reference integrity and output guards are covered by the existing tests.
- TypeScript checking and static export passed. npm reported zero known vulnerabilities in the resolved frontend dependencies.
- The first authenticated live model request passed in 11.44 seconds including verification overhead. Final-release authenticated live testing passed three consecutive non-fallback replies at 11.0s, 8.33s, 7.23s. History isolation and queue promotion passed. See LIVE_RELIABILITY_CHECK.json.

## Remaining limits

No 9/10 overall availability score is claimed. Daily GPU quotas and provider queueing can still prevent ordinary conversation. Local fixture load tests do not measure public GPU throughput, and a short live test is not a long-running availability measurement. Browser iframe authentication still needs validation in a signed-in browser; the HTTP test token is not embedded in the app.

The application permits 20 user messages per session; this is separate from the daily GPU limit. Hugging Face documents two minutes for unauthenticated visitors and five for free accounts. Appointment queueing cannot increase either allowance.

An alternative is Groq's free hosted-model API: its documented free text-model limits include 1,000 requests/day, 8,000 tokens/minute and 200,000 tokens/day for selected models, shared across the organization. Our two-pass generation/review consumes two API requests plus input/output tokens per user message. This is not 1,000 user messages. The current Qwen3.5 adapter is not automatically portable to another hosted model; a provider/model change requires updated evaluation and disclosures. No alternate provider has been activated.

Sources:
- https://huggingface.co/docs/hub/spaces-zerogpu
- https://gradio.app/guides/server-mode
- https://console.groq.com/docs/rate-limits
- https://console.groq.com/docs/your-data
