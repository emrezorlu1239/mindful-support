"""Load only the selected, evaluated local configuration; never download at request time."""
import hashlib
import json
from importlib.metadata import version
from ai.config import ROOT

FILES=("ai/serving.json","ai/candidates.json","ai/config.py","ai/model.py","ai/candidate_model.py",
       "ai/candidate_download.py","ai/pipeline.py","ai/retrieval.py","ai/language.py","ai/runtime.py",
       "ai/serving.py","knowledge/passages.json","web/app/language-notice.tsx",
       "backend/app.py","backend/admission.py")
PACKAGES=("torch","transformers","peft","accelerate","bitsandbytes","tokenizers","langgraph","numpy","lingua-language-detector")

def selection():
    spec=json.loads((ROOT/"ai/serving.json").read_text())
    adapter=(ROOT/spec["adapter_directory"]).resolve()
    adapter.relative_to((ROOT/"models/experiments").resolve())
    receipt=(ROOT/spec["evaluation_receipt"]).resolve()
    receipt.relative_to((ROOT/"docs").resolve())
    entry=json.loads((ROOT/"ai/candidates.json").read_text())[spec["model"]]
    return spec,adapter,receipt,entry

def serving_fingerprint():
    _spec,adapter,_receipt,_entry=selection()
    files={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in FILES}
    files["adapter_config.json"]=hashlib.sha256((adapter/"adapter_config.json").read_bytes()).hexdigest()
    return {"files":files,"packages":{name:version(name) for name in PACKAGES}}

def verify_receipt(receipt,spec,entry,adapter_digest,fingerprint):
    if receipt.get("approved_for_local_demo") is not True:
        raise RuntimeError("Selected model is not approved for local use")
    if (receipt.get("model")!=spec["model"] or receipt.get("revision")!=entry["revision"]
            or receipt.get("adapter_sha256")!=adapter_digest):
        raise RuntimeError("Selected model or adapter does not match its evaluation")
    if receipt.get("fingerprint")!=fingerprint:
        raise RuntimeError("Evaluated serving configuration changed")
    if (receipt.get("supported_languages")!=spec["supported_languages"]
            or spec["concurrent_generations"]!=1 or receipt.get("engineering_checks_passed") is not True):
        raise RuntimeError("Serving policy or engineering checks do not match")

def load_selected_runtime():
    from ai.runtime import AIRuntime
    spec,adapter,path,entry=selection()
    if not path.is_file():raise RuntimeError("Selected model evaluation is missing")
    receipt=json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("approved_for_local_demo") is not True:
        raise RuntimeError("Selected model is not approved for local use")
    digest=hashlib.sha256((adapter/"adapter_model.safetensors").read_bytes()).hexdigest()
    verify_receipt(receipt,spec,entry,digest,serving_fingerprint())
    for filename,digest in receipt["evidence_sha256"].items():
        evidence=(ROOT/filename).resolve()
        evidence.relative_to((ROOT/"docs").resolve())
        if hashlib.sha256(evidence.read_bytes()).hexdigest()!=digest:
            raise RuntimeError("Evaluation evidence changed")
    from ai.candidate_model import CandidateModel
    from ai.retrieval import Retriever,Embedder
    return AIRuntime(CandidateModel(spec["model"],quantized=True,adapter=adapter),Retriever(Embedder()))
