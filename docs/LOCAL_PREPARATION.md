# Local preparation milestone

This milestone was explicitly requested before cloud publication. It requires **no external API key**. It is not the completed AI demo or the owner's final acceptance test.

## Implemented

- React/TypeScript interface with English by default and a visible English / Türkçe language switch.
- Two-step booking: basic details and immediate or scheduled entry.
- Server-enforced admission: one active visitor by default, FIFO waiting room with people-ahead counts, automatic promotion, explicit leave and expiring heartbeat leases. See ADMISSION.md.
- Chat-only interface; optional gentle background transitions with motion controls. Avatar assets are retired.
- FastAPI booking service on loopback with a local SQLite database.
- Opaque HttpOnly, SameSite=Strict access cookie; only token hashes stored in the database.
- Per-owner booking visibility, atomic time-slot exclusivity, maximum three active reservations, cancellation, expiry cleanup, input limits, origin checks and no-store responses.
- Chat client and server pipeline integration; actual replies remain gated on verified adapter training and evaluation. No mocked replies are shown to users.
- Public-source links, experimental-use notice, privacy explanation and always-available urgent-help information.

## AI experiment result

A real multilingual E5 reference index has been built and its eight development queries now retrieve the expected passage in the first three results. The LangGraph pipeline is implemented and tested with deterministic fixtures; those tests are not model-quality evidence. Base-model transfer and two real adapter training runs completed. Automatic format checks improved, but direct review rejected the current candidate for language quality and unsupported advice. The API keeps chat unavailable. The first **completed AI demo** still requires real fine-tuning as requested by the owner.

See AI_DEVELOPMENT.md for pinned models, the 48-example synthetic training dataset, held-out scenarios, reproducible training and evaluation commands, and the current evidence boundary. The owner authorized local GPU training; public laptop hosting remains excluded.

## Retention and limitations

Only use invented names in local tests. Booking identity fields are stored on disk under the ignored data directory. The owner cookie expires after 24 hours; cleanup removes expired owners and their bookings, and additionally removes bookings 24 hours after their end. Cleanup runs on startup, bootstrap and every five seconds while the backend is running. Stopped servers cannot run cleanup. Canceled records are deleted with SQLite secure_delete enabled, but no forensic erasure guarantee is made for filesystem copies or storage devices.

This local identity mechanism has no cross-device recovery and is not a production authentication design. The dev proxy is not a production API gateway. Public-hosting architecture, database persistence across cloud restarts, country-specific crisis resources, model evaluation, and final privacy text remain future release work. No public tunnel, remote repository, hosted Space or deployment exists.

The earlier ImageGen avatar assets have been retired and moved to ignored work/retired-avatars. Their provenance record remains for historical accuracy; the current site does not serve or display them.

## Validation scope

Backend tests cover session isolation, exclusive concurrent reservations, cancellation, limits, malformed requests, age acknowledgement, expiry and disabled-chat behavior. Type checking, frontend build and dependency auditing are performed separately. Browser interaction and assistive-technology evaluation must not be claimed unless actually executed. Optional WebMCP support is feature-detected; its runtime registration requires a supported context to verify.

Recorded results: see VALIDATION.md. The user can view the local foundation at http://localhost:3000 while the retained development processes are running. This is not an invitation to the final acceptance test; that remains after the AI stages and engineering checks are complete.
