"""Download only the selected public artifacts and build the reference index."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai.config import ROOT, EMBED_MODEL, LOCK
from huggingface_hub import snapshot_download
from ai.serving import selection
from ai.candidate_download import validate_snapshot
import hashlib
import json

def main():
    spec, adapter, receipt_path, entry = selection()
    patterns = ['*.safetensors', '*.json', '*.jinja', 'vocab.*', 'merges.txt', 'tokenizer.model', 'LICENSE*']
    snapshot = snapshot_download(spec['model'], revision=entry['revision'], cache_dir=str(ROOT/'models/hf/hub'), allow_patterns=patterns)
    validate_snapshot(Path(snapshot), entry)
    snapshot_download(EMBED_MODEL, revision=LOCK[EMBED_MODEL]['revision'], cache_dir=str(ROOT/'models/hf/hub'), allow_patterns=patterns)
    snapshot_download('Zorlu5454/mindful-support-qwen3.5-4b-lora', revision='3ea6acc7b33b9bff5fbb963e969374c3acf05cef',
        local_dir=str(adapter), allow_patterns=['adapter_model.safetensors', 'adapter_config.json', 'training-report.json'])
    receipt = json.loads(receipt_path.read_text())
    if hashlib.sha256((adapter/'adapter_model.safetensors').read_bytes()).hexdigest() != receipt['adapter_sha256']:
        raise RuntimeError('Adapter hash mismatch')
    from ai.retrieval import Embedder, build_index
    build_index(Embedder())
    print('Pinned model, adapter and public reference index are ready.')

if __name__ == '__main__':
    main()
