# Dependency security review

Reviewed 2026-09-09 for the local development environment.

The full npm audit (including development packages) reports zero known vulnerabilities after a transitive override from sharp 0.35.2 to 0.35.4. Production-only npm auditing had missed that development dependency, so both scopes were checked. The project build, types and lint passed after the patch.

After upgrading Transformers to 5.16.1 and PEFT to 0.20.0, `pip-audit` reports **one known advisory**, affecting Accelerate 1.14.0. The CUDA-specific PyTorch wheel (2.8.0+cu128) was skipped by that audit because its exact distribution was not found on PyPI; this is not a clean bill of health for PyTorch.

[GHSA-4j2p-28q2-5m79](https://github.com/advisories/GHSA-4j2p-28q2-5m79) describes checkpoint index path traversal and possible blocking through malicious shard paths. The advisory currently lists no patched version.

Local mitigations:

- Load only the pinned Qwen snapshot and local Safetensors weights.
- Validate checkpoint indices against the exact allowlisted shard basenames in the candidate manifest; the selected final derivative has one pinned Safetensors file.
- Verify downloaded weights against the pinned upstream LFS SHA-256 values.
- Do not expose model uploads, arbitrary checkpoint paths, conversion scripts or remote Python code.
- Bind activation to adapter weights, adapter configuration, evaluated code, references and runtime versions.

These controls reduce this application's exposure; they do not patch the upstream package. Recheck the advisory and update the dependency before any public release decision. Never label the dependency audit as vulnerability-free.

Reproduce with `uvx --from pip-audit pip-audit --path .venv/Lib/site-packages`. The environment is pinned in requirements-ai.lock; platform-specific CUDA wheels need their official index. Audit reports and local package caches are not user-conversation storage.

Rechecked the official Accelerate advisory on 2026-09-10: affected versions remain <=1.14.0 and no patched version is listed. The selected single-file manifest and path/hash guards remain the application mitigation.
