"""Bind local evaluation to the code, references, adapter configuration and runtime versions."""
import hashlib
from importlib.metadata import version
from ai.config import ROOT, ADAPTER

FILES = ("ai/config.py", "ai/model.py", "ai/pipeline.py", "ai/retrieval.py", "ai/language.py",
         "ai/model-lock.json", "ai/evaluate.py", "training/examples.json", "knowledge/passages.json")
PACKAGES = ("torch", "transformers", "peft", "accelerate", "tokenizers", "langgraph", "numpy", "lingua-language-detector")

def evaluation_fingerprint():
    files = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in FILES}
    files["adapter_config.json"] = hashlib.sha256((ADAPTER/"adapter_config.json").read_bytes()).hexdigest()
    return {"files": files, "packages": {name: version(name) for name in PACKAGES}}
