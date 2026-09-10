# Current validation — 2026-09-10

The final Qwen3.5 text-only NF4 candidate completed real QLoRA training, language review, resource measurement and HTTP integration. The hash-bound serving loader also loaded the actual adapter, produced a synthetic response and cleared its session successfully; see GUARDED_STARTUP.json. Local activation is available. Nothing has been published.

79 Python tests passed. The only reported warning is an upstream Starlette/AnyIO deprecation. English scored 9.0/10 and Turkish 6.4/10 in the small manual engineering review, with the limitations recorded in FINAL_LANGUAGE_REVIEW.json. The Turkish strong-warning tier is active in booking and chat. No clinical validation is claimed.

The earlier milestone below concerns the rejected 1.7B candidate and remains historical evidence. The current release blockers and account checks are in RELEASE_READINESS.md; provider integration and owner acceptance have not been completed. Browser/assistive-technology QA has not been performed or inferred from HTTP checks.

## Historical validation record

# Local AI milestone validation

Date: 2026-09-09. **The adapter was actually trained, but this model candidate was rejected for response quality. AI chat remains disabled.** Nothing has been published.

| Check | Result and limits |
| --- | --- |
| Backend and AI software tests | 61 passed; one upstream Starlette/AnyIO deprecation warning. Covers capacity/FIFO, expiry, owner isolation, in-flight cancellation, volatile memory, idempotency, malformed drafts, source binding, wrong output language, and stale evaluation rejection. Fixture-model tests are not model-quality evidence. |
| Local HTTP integration | Passed through localhost:3000: English initial form, application validation, retired avatar URLs returning 404, real vector readiness, chat-only booking, admission queue, history isolation, disabled-model gate and removal of fictional test bookings. |
| Actual reference retrieval | 13 NIMH passages embedded with multilingual E5; 8/8 development queries found the expected passage within the first three results after the library upgrade. Not a broad or untouched benchmark. |
| Actual fine-tuning | Two completed LoRA experiments. Latest: 48 synthetic examples, six epochs, 72 optimizer steps, 112 changed parameter tensors, about 101.7 seconds and 4,362 MiB peak PyTorch GPU allocation. Initial two-epoch report retained separately. |
| Model development evaluation | Latest 12 original test prompts: 100% valid JSON, 83.3% route agreement, all expected output languages detected. Support fallback across development cases: 12.5%. Tested crisis routes passed. These automatic gates passed but did not establish semantic quality. |
| Direct output review | Failed. All 18 development pipeline outputs and 12 fresh integration outputs inspected. Several Turkish replies are incoherent, one English boundary suggestion reverses the intended timing, and some cited passages do not support the generated advice. See AI_OUTPUT_REVIEW.json. Both languages stay disabled for this candidate. |
| Activation control | Requires successful automated checks and direct output review, matching adapter/configuration hashes, pinned base revision, evaluated code, reference corpus and runtime versions. A rejected or stale candidate cannot start AI mode. |
| TypeScript, lint and build | Passed using the project's npm scripts. Generated components/ui/** and hooks/use-mobile.ts remain excluded from lint for upstream baseline diagnostics; they are still type-checked. Vinext reports its route-classification limitation without failing the build. |
| Build helper | The Sites wrapper failed to resolve npm's CLI path on Windows. The same project build script succeeded directly via npm.cmd. No plugin installation files were modified. |
| npm dependency audit | 0 known vulnerabilities after pinning the transitive sharp dependency to 0.35.4, including development dependencies. |
| Python dependency audit | One known Accelerate advisory remains without a listed upstream fix. The exact CUDA PyTorch wheel was skipped by pip-audit. Local checkpoint path restrictions mitigate the known entry point; see DEPENDENCY_SECURITY.md. Do not call this a clean security audit. |
| Dependency lock | requirements-ai.lock updated; uv sync dry-run finds the installed 75-package environment consistent. |
| Local launcher | PowerShell syntax checked; existing-port guard, backend readiness wait, startup-failure cleanup and environment restoration implemented. Full interactive launcher lifecycle has not been exercised. |
| Git and retention | Credentials, databases, model weights, caches, build output and local experiment helpers excluded. No remote repository or public service created. |

The initial automatic evaluation failed. Sampling and language instructions were revised, then the adapter was retrained. Previously inspected scenarios are now development/regression evidence, even though their JSON split retains the original test label. The separate fresh set was not used to tune this candidate before its first run. Any future tuning against it makes it a regression set too.

## Work remaining before final owner acceptance

- A multilingual model candidate with coherent, source-supported replies, followed by fresh evaluation and real AI HTTP integration tests.
- Multi-turn model behavior, broader indirect-crisis and adversarial scenarios, performance under the chosen hosted quotas, and country-specific resource coverage.
- Browser interaction, responsive and keyboard/assistive-technology testing; no browser QA has been claimed in this milestone.
- Production authentication, hosting retention behavior, remaining dependency/license review and release documentation.
- Final owner acceptance, then explicit publication approval. No deployment or GitHub push is authorized yet.

No clinical validation or psychologist endorsement is claimed. User testing has not been requested early.
