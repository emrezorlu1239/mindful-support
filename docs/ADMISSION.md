# Admission and waiting room

The interface opens in English. Both **English** and **Türkçe** are visible in the top bar; switching changes the interface and the language selected for a new appointment. Existing appointment language is preserved. The interface presents an experimental AI support application without claiming clinical care or endorsement.

## User flow

- **Join now** creates an immediate appointment. A free place opens the session room; otherwise the visitor enters a FIFO waiting room.
- Scheduled appointments remain available. Joining before the scheduled time is rejected by the server. A scheduled time permits joining; it does not promise immediate capacity or priority over people already waiting.
- The waiting room shows active places, waiting position, and people ahead (active visitors plus earlier waiting visitors). No unsupported wait-time estimate is shown.
- The browser checks every 10 seconds and opens the session room when admitted. Refreshing preserves the server-side ticket; a return banner leads back to the active room or queue.
- Leaving, cancelling, reaching the 20-minute session deadline, or losing the 90-second heartbeat lease releases the place. Cleanup runs every 5 seconds and during admission requests. Background-tab throttling can cause lease expiry. Promotion does not extend an absent visitor's lease.
- One browser access cookie can hold at most one active or waiting ticket. Tabs sharing that cookie represent the same visitor; use separate browser profiles for independent visitors.

## Capacity and implementation

The default is **one active session**, with at most **32 waiting visitors**. The environment variable `MINDFUL_MAX_CONCURRENT_SESSIONS` accepts 1–4. Keep it at one until the actual model and chosen host have been load tested; a queue cannot guarantee service availability or create free inference capacity.

SQLite `BEGIN IMMEDIATE` transactions serialize expiry, admission and FIFO promotion. The queue works across application instances sharing this database and the same capacity configuration. Do not use separate databases as independent replicas of this limit. This local architecture is not yet a distributed production gateway.

The versioned migration preserves existing bookings and their recorded consent versions, treating them as scheduled appointments. Only scheduled starts are unique; multiple immediate appointments can share a timestamp. Admission metadata contains booking identity, order, state and expiry times, never conversation content.

Authenticated rate limits are per owner so visitors behind the same development proxy do not exhaust one shared heartbeat limit. Unauthenticated traffic remains limited by IP. Production identity, abuse controls and upstream inference locking remain separate work.

## Current AI boundary

Admission reserves a session space. It does not imply model readiness. Requests without active admission return 403; admitted requests return 503 until an evaluated runtime is explicitly enabled. The integrated runtime rechecks admission after generation and bounds in-flight inference with one process-wide semaphore; cancelled or expired sessions discard unfinished replies.

## Verification

30 backend tests passed, including two application instances concurrently admitting eight visitors at capacities one and two, FIFO transitions, owner isolation, idempotency, expiry, queue bounds, restart recovery and legacy-data migration. TypeScript, application lint, frontend build and a real HTTP smoke check through the local frontend proxy passed. The smoke check verifies initial English HTML and both language labels, then creates and removes fictional appointments.

Browser interaction, accessibility tools and real model load testing remain outstanding. No public release or final owner acceptance has taken place.
