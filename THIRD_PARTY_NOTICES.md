# Third-party notices

The root MIT license applies to original application code and documentation. It does not relicense external models, reference text, dependencies or generated components derived from third-party libraries.

| Material | Provenance and terms |
| --- | --- |
| Selected base model | `techwithsergiu/Qwen3.5-text-4B-bnb-4bit`, pinned in `ai/candidates.json`; a text-only, NF4 derivative of Qwen/Qwen3.5-4B. The distributor identifies Apache-2.0 upstream terms. Preserve the exact upstream license and applicable notices when distributing model artifacts. No weights are included in Git. |
| Fine-tuned adapter | The project's actual QLoRA adaptation; training and artifact hashes are recorded in `docs/TRAINING_Qwen3.5-text-4B-bnb-4bit.json`. Distribution must include the base-model attribution, model card and applicable license notices. |
| Embedding model | `intfloat/multilingual-e5-small`, pinned in `ai/model-lock.json`; see its upstream model card and MIT license. No embedding-model weights are included in Git. |
| Reference passages | Thirteen reviewed NIMH text passages, separately attributed with hashes and reuse evidence in `knowledge/passages.json` and `docs/SOURCE_REGISTER.md`. No images, logos or endorsement rights are included. |
| Synthetic training examples | Original AI-authored records under CC0 1.0, as described in `training/README.md`. They contain no real user conversations. |
| Interface components and dependencies | React, Vinext, shadcn/Base UI and other packages retain their upstream licenses and copyright notices. Exact package versions are recorded in `web/package-lock.json` and the Python lockfiles. |

Before distributing a runtime image, include the license files supplied by each bundled dependency and model artifact. This register is provenance documentation, not a representation that every future deployment artifact has already been reviewed.
