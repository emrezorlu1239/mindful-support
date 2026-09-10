"""Run the fresh integration scenarios once per frozen candidate; no automatic approval."""
import hashlib
import json
import time
from ai.config import ROOT, ADAPTER
from ai.model import LocalModel
from ai.pipeline import build_pipeline
from ai.retrieval import Embedder, Retriever
from ai.provenance import evaluation_fingerprint

def main():
    scenarios = ROOT/"training/fresh-evaluation.json"
    cases = json.loads(scenarios.read_text(encoding="utf-8"))["cases"]
    model = LocalModel()
    graph = build_pipeline(model, Retriever(Embedder()))
    rows = []
    for case in cases:
        start = time.monotonic()
        reply = graph.invoke({"message":case["user"], "language":case["language"], "history":case["history"]},
                             config={"callbacks":[], "recursion_limit":8})["result"]
        row = {**case, **reply, "latency_seconds":time.monotonic()-start}
        rows.append(row)
        print(case["id"], json.dumps(reply, ensure_ascii=True), flush=True)
    report = {"approved_for_local_demo":False, "clinical_validation":False,
              "scope":"Fresh post-development integration scenarios; direct review required",
              "adapter_sha256":hashlib.sha256((ADAPTER/"adapter_model.safetensors").read_bytes()).hexdigest(),
              "scenarios_sha256":hashlib.sha256(scenarios.read_bytes()).hexdigest(),
              "fingerprint":evaluation_fingerprint(), "results":rows,
              "peak_vram_mb":model.torch.cuda.max_memory_allocated()/2**20}
    (ROOT/"docs/AI_FRESH_EVALUATION.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__ == "__main__": main()
