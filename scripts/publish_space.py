"""Publish only the selected application artifacts to its existing free Space."""
import hashlib
import json
import sqlite3
from pathlib import Path

from huggingface_hub import HfApi, CommitOperationAdd, CommitOperationDelete

ROOT = Path(__file__).resolve().parents[1]
REPO = 'Zorlu5454/mindful-support'


def main():
    values = {}
    for line in (ROOT / 'private/API_KEYS.txt').read_text(encoding='utf-8-sig').splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    api = HfApi(token=values['HF_TOKEN'])
    info = api.space_info(REPO)
    if info.id != REPO or str(info.runtime.requested_hardware) != 'zero-a10g':
        raise RuntimeError('Unexpected repository or non-free hardware configuration')
    files = {}
    def add(path, destination=None):
        relative = path.relative_to(ROOT).as_posix()
        if '__pycache__' in path.parts or path.suffix == '.pyc':
            return
        files[destination or relative] = path
    for folder in ('ai', 'backend', 'knowledge'):
        for path in (ROOT / folder).rglob('*'):
            if path.is_file() and path.suffix in ('.py', '.json', '.md'):
                add(path)
    receipt = json.loads((ROOT / 'docs/SERVING_APPROVAL.json').read_text())
    for name in receipt['fingerprint']['files']:
        if name != 'adapter_config.json':
            add(ROOT / name)
    for name in receipt['evidence_sha256']:
        add(ROOT / name)
    for name in ('app.py', 'requirements.txt', 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'docs/SERVING_APPROVAL.json'):
        add(ROOT / name)
    add(ROOT / 'space_README.md', 'README.md')
    static = ROOT / 'web/dist/client'
    if not (static / 'index.html').is_file():
        raise RuntimeError('Build the static frontend before publishing')
    for path in static.rglob('*'):
        if path.is_file() and 'avatars' not in path.parts and '.vite' not in path.parts:
            add(path)
    index = ROOT / 'data/knowledge.sqlite'
    with sqlite3.connect(f'file:{index.as_posix()}?mode=ro', uri=True) as con:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if tables != {'passages', 'metadata'}:
            raise RuntimeError('Only the public reference index can be distributed')
    add(index)
    spec = json.loads((ROOT / 'ai/serving.json').read_text())
    adapter = ROOT / spec['adapter_directory']
    if hashlib.sha256((adapter / 'adapter_model.safetensors').read_bytes()).hexdigest() != receipt['adapter_sha256']:
        raise RuntimeError('Adapter hash mismatch')
    for name in ('adapter_model.safetensors', 'adapter_config.json', 'training-report.json'):
        add(adapter / name)
    add(ROOT / 'docs/MODEL_CARD.md', spec['adapter_directory'] + '/README.md')
    add(ROOT / 'work/release-notices/BASE_MODEL_LICENSE.txt', spec['adapter_directory'] + '/LICENSE')
    operations = [CommitOperationAdd(path_in_repo=name, path_or_fileobj=path) for name, path in files.items()]
    for remote in info.siblings:
        name = remote.rfilename
        if '__pycache__' in name or name.startswith('web/dist/client/') and name not in files:
            operations.append(CommitOperationDelete(path_in_repo=name))
    result = api.create_commit(REPO, repo_type='space', operations=operations,
        parent_commit=info.sha, commit_message='Fix ZeroGPU startup and preserve parent-process session state')
    print(json.dumps({'commit': result.oid, 'space': 'https://huggingface.co/spaces/' + REPO,
                      'files': len(files), 'bytes': sum(p.stat().st_size for p in files.values())}))


if __name__ == '__main__':
    main()
