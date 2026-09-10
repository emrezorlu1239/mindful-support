# Contributing

Mindful Support is an experimental emotional-support application for adults. Keep changes focused on the documented product scope and describe the behavior before and after your change.

## Local checks

- Use the isolated Python environment and the committed dependency locks.
- Run `.venv/Scripts/python.exe -m pytest -q` for backend and pipeline changes.
- In `web`, run `npx tsc --noEmit` and `npm run build` for interface changes.
- Use synthetic identities and messages in every test, issue and example.
- Never include credentials, user conversations, model caches or local databases in a contribution.

## Model changes

Record model provenance, immutable revisions, weight hashes, training data rights, actual training measurements and separate language evaluations. A configured training job is not evidence of completed fine-tuning. Preserve failed examples as regression tests and distinguish those tests from unseen evaluation.

The selected model and application checks are bound to an evaluation receipt. Do not regenerate that receipt merely to bypass a mismatch; review and measure the affected behavior first. English and Turkish have different documented limitations. Do not imply clinical validation.

## Release process

Engineering checks precede owner acceptance. Publication requires the owner's final acceptance and release authorization. There is no automatic deployment workflow. See [release readiness](docs/RELEASE_READINESS.md).
