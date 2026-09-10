"""Inspect Git-visible source without printing matching credentials or file content."""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = {"private", "models", "data", "work", ".venv", "node_modules", "__pycache__", ".git", ".wrangler", "dist"}
TOKENS = re.compile(rb"\b(?:hf_[A-Za-z0-9]{25,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")


def main():
    output = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT
    )
    names = sorted(set(x.decode("utf-8") for x in output.split(b"\0") if x))
    failures = []
    size = 0
    for name in names:
        path = ROOT / name
        if not path.exists():
            continue
        if path.is_symlink():
            failures.append((name, "symbolic link requires review"))
            continue
        path.resolve().relative_to(ROOT)
        if FORBIDDEN.intersection(path.relative_to(ROOT).parts) or path.name.startswith(".env") and path.name != ".env.example":
            failures.append((name, "private or generated path"))
            continue
        if path.suffix.lower() in {".safetensors", ".gguf", ".sqlite", ".pem", ".key"} or path.stat().st_size > 10_000_000:
            failures.append((name, "runtime artifact or oversized source"))
            continue
        content = path.read_bytes()
        size += len(content)
        if TOKENS.search(content):
            failures.append((name, "credential pattern detected"))
    print(json.dumps({"checked_files": len(names), "source_bytes": size,
                      "passed": not failures, "findings": failures}, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
