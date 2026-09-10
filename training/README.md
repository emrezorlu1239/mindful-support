# Synthetic bootstrap dataset

`examples.json` contains 48 original AI-authored training examples (24 topics in English and Turkish), plus six validation and 12 held-out test prompts. It is not a record of real conversations and has not been reviewed by a psychologist.

Only records in `records` with split `train` enter gradient updates. The separate `evaluation` list is never appended to training. Evaluations are a small development instrument, not a clinical benchmark. Translations within training share topic groups; neither language version of a held-out scenario is used for training.

The original synthetic examples are offered under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). Third-party reference passages and base-model licenses remain separate. No NIMH passage is copied into this training file. Citation fields are initially empty; runtime references are provided by retrieval.

Do not add private messages, therapy transcripts or scraped conversations. Expanding the dataset requires source provenance, appropriate reuse permission, duplicate checks, and fresh evaluation data.

Two actual training runs completed. The latest used six epochs and 72 optimizer steps; reports and the rejected output-quality review are in docs/. The original held-out scenarios were inspected while improving decoding and language instructions, so they now provide development/regression evidence. The separate fresh-evaluation.json contains 12 post-development scenarios that were not used to tune this candidate before their first run. They must also become regression cases if future changes use their results.

## Candidate adaptation

`grounding-examples.json` adds 16 original synthetic records for reference use, irrelevant/adversarial references, user choice and service boundaries. Their short reference notes are invented training material, not NIMH excerpts or clinical guidance. Combined candidate training has 64 records. `ai.train_candidate` uses NF4 QLoRA, masked prompt loss, frozen base weights, gradient accumulation and a fixed seed. It writes a separate experiment directory; it never activates an adapter in the application.

`candidate-holdout.json` contains 16 additional single/multi-turn English/Turkish cases created before this candidate's training. They remain outside all gradient updates. The trainer rejects exact normalized prompt overlap with all evaluation files. This check does not establish semantic independence or clinical coverage. Once outputs are inspected, subsequent iterations must describe these cases as regressions rather than new unseen evidence.

An experiment counts as trained only after its weight-change, adapter hash, step count and actual resource report have been written. Do not infer completed training from the presence of these scripts or datasets.
