"""Download only a manifest-pinned candidate, without changing the active application model."""
import argparse
import hashlib
import json
from pathlib import Path
from ai.config import ROOT
from huggingface_hub import snapshot_download

MANIFEST = ROOT/"ai/candidates.json"
def validate_snapshot(path, entry, verify_hashes=True):
    path=Path(path)
    config=json.loads((path/"config.json").read_text(encoding="utf-8"))
    if config.get("model_type") != entry["model_type"]:
        raise ValueError("Candidate architecture mismatch")
    expected={item["name"] for item in entry["weights"]}
    index=path/"model.safetensors.index.json"
    if index.exists():
        names=set(json.loads(index.read_text())["weight_map"].values())
        if names != expected: raise ValueError("Unexpected checkpoint shard paths")
    for item in entry["weights"]:
        weight=path/item["name"]
        if weight.parent != path or not weight.is_file() or weight.stat().st_size != item["size"]:
            raise ValueError("Candidate checkpoint is incomplete")
        if verify_hashes:
            with weight.open("rb") as src:
                if hashlib.file_digest(src,"sha256").hexdigest()!=item["sha256"]:
                    raise ValueError("Candidate weight hash mismatch")
    return path

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("model",choices=list(json.loads(MANIFEST.read_text())))
    args=parser.parse_args()
    entry=json.loads(MANIFEST.read_text())[args.model]
    print("Downloading pinned candidate:",args.model,flush=True)
    path=snapshot_download(args.model,revision=entry["revision"],max_workers=3,
        allow_patterns=["*.safetensors","*.json","*.jinja","vocab.*","merges.txt","LICENSE","README.md"])
    validate_snapshot(path,entry)
    print("Candidate weights verified:",args.model,flush=True)
if __name__=="__main__": main()
