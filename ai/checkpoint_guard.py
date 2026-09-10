"""Constrain sharded checkpoint loading to the pinned Qwen snapshot."""
import json
import re
from pathlib import Path
from ai.config import ROOT,BASE_MODEL,LOCK

def validate_shard_map(data):
    entries=data.get("weight_map")
    if not isinstance(entries,dict) or not entries:
        raise ValueError("Missing checkpoint weight map")
    names=set(entries.values())
    expected={"model-00001-of-00002.safetensors","model-00002-of-00002.safetensors"}
    if names != expected:
        raise ValueError("Unexpected checkpoint shard paths")
    return names

def base_snapshot(require_weights=True):
    path=ROOT/"models"/"hf"/"hub"/("models--"+BASE_MODEL.replace("/","--"))/"snapshots"/LOCK[BASE_MODEL]["revision"]
    config=json.loads((path/"config.json").read_text(encoding="utf-8"))
    if config.get("model_type")!="qwen3":
        raise ValueError("Unexpected model architecture")
    names=validate_shard_map(json.loads((path/"model.safetensors.index.json").read_text(encoding="utf-8")))
    if require_weights and any(not (path/name).is_file() for name in names):
        raise ValueError("Pinned model shards are incomplete")
    return path
