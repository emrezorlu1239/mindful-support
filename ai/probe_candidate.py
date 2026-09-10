import argparse,hashlib,json,time,statistics
import psutil
from ai.config import ROOT
from ai.candidate_model import CandidateModel
from ai.retrieval import Retriever,Embedder
from ai.pipeline import Draft,build_pipeline

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("model")
    parser.add_argument("--quantized",action="store_true")
    parser.add_argument("--adapter")
    parser.add_argument("--suite",default="training/fresh-evaluation.json")
    parser.add_argument("--report-suffix",default="")
    args=parser.parse_args()
    code_hashes={name:hashlib.sha256((ROOT/"ai"/name).read_bytes()).hexdigest()
                 for name in ("config.py","model.py","pipeline.py","retrieval.py","candidate_model.py","candidates.json")}
    model=CandidateModel(args.model,args.quantized,args.adapter)
    reviews=[]
    original_generate=model.generate
    def observed_generate(messages,max_tokens=384):
        result=original_generate(messages,max_tokens=max_tokens)
        if max_tokens==80: reviews.append(result)
        return result
    model.generate=observed_generate
    retriever=Retriever(Embedder())
    graph=build_pipeline(model,retriever)
    suite=(ROOT/args.suite).resolve()
    suite.relative_to((ROOT/"training").resolve())
    if args.report_suffix and not all(c.isalnum() or c in "-_" for c in args.report_suffix):
        raise ValueError("Invalid report suffix")
    data=json.loads(suite.read_text(encoding="utf-8"))["cases"]
    rows=[]
    for case in data:
        reviews.clear()
        start=time.monotonic()
        refs=retriever.search(case["user"])
        raw=model.draft(case["user"],case["language"],case.get("history",[]),refs)
        draft_seconds=time.monotonic()-start
        try: parsed=Draft.model_validate_json(raw);valid=True
        except ValueError: valid=False
        pipeline_start=time.monotonic()
        result=graph.invoke({"message":case["user"],"language":case["language"],"history":case.get("history",[])},
            config={"callbacks":[],"recursion_limit":8})["result"]
        rows.append({**case,"raw":raw,"valid_json":valid,"draft_seconds":draft_seconds,"result":result,
                     "review_outputs":list(reviews),
                     "pipeline_seconds":time.monotonic()-pipeline_start,
                     "total_probe_seconds":time.monotonic()-start})
        print(case["id"],json.dumps({"raw":raw,"result":result},ensure_ascii=True),flush=True)
    report={"model":args.model,"revision":model.entry["revision"],"quantized":model.quantized,
            "adapter_sha256":model.adapter_sha256,
            "suite":str(suite.relative_to(ROOT)),"suite_sha256":hashlib.sha256(suite.read_bytes()).hexdigest(),
            "weight_bytes":model.entry["weight_bytes"],"load_seconds":model.load_seconds,
            "peak_vram_mb":model.torch.cuda.max_memory_allocated()/2**20,
            "peak_cuda_reserved_mb":model.torch.cuda.max_memory_reserved()/2**20,
            "process_rss_mb":psutil.Process().memory_info().rss/2**20,
            "median_pipeline_seconds":statistics.median(row["pipeline_seconds"] for row in rows),
            "max_pipeline_seconds":max(row["pipeline_seconds"] for row in rows),
            "code_hashes":code_hashes,
            "rows":rows,"clinical_validation":False,"approved":False,
            "scope":"Engineering evaluation of synthetic scenarios; freshness must be recorded in direct output review"}
    path=ROOT/"docs"/("CANDIDATE_"+args.model.split("/")[-1]+("_nf4" if model.quantized else "_bf16")+("_adapter" if args.adapter else "")+("_"+args.report_suffix if args.report_suffix else "")+".json")
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Candidate report saved",str(path),flush=True)
if __name__=="__main__": main()
