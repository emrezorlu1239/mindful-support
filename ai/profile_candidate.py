"""Local single-worker resource measurements using synthetic input only."""
import argparse
import gc
import json
import math
import statistics
import threading
import time
from uuid import uuid4
import psutil
from ai.config import ROOT
from ai.candidate_model import CandidateModel
from ai.retrieval import Embedder, Retriever
from ai.runtime import AIRuntime


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("model")
    parser.add_argument("--adapter",required=True)
    args=parser.parse_args()
    process=psutil.Process()
    peak_rss=[process.memory_info().rss]
    stop=threading.Event()
    def sample():
        while not stop.wait(0.05):
            peak_rss[0]=max(peak_rss[0],process.memory_info().rss)
    sampler=threading.Thread(target=sample,daemon=True);sampler.start()
    try:
        model=CandidateModel(args.model,quantized=True,adapter=args.adapter)
        runtime=AIRuntime(model,Retriever(Embedder()))
        torch=model.torch
        torch.cuda.reset_peak_memory_stats()
        rows=[]
        prompts={
            "en":["I have a busy week ahead and want to talk about feeling overwhelmed.",
                  "I would like you to listen without giving advice right now.",
                  "It is hard to make time for the things I enjoy.",
                  "That is enough for today. I would like to stop."],
            "tr":["Bu hafta yoğun geçiyor; kendime zaman ayıramadığım için üzülüyorum.",
                  "Şimdilik bir öneri değil, sadece dinlenmek istiyorum.",
                  "Keyif aldığım şeylere zaman ayırmakta zorlanıyorum.",
                  "Bugünlük bu kadar yeter. Konuşmayı bitirmek istiyorum."],
        }
        for session in range(3):
            key=f"synthetic-resource-{session}"
            language="tr" if session==1 else "en"
            for message in prompts[language]:
                start=time.monotonic()
                result=runtime.respond(key,str(uuid4()),message,language,lambda:True)
                rows.append({"session":session,"language":language,"seconds":time.monotonic()-start,
                    "fallback":result["fallback"],"route":result["route"],
                    "idle_cuda_allocated_mb":torch.cuda.memory_allocated()/2**20,
                    "idle_cuda_reserved_mb":torch.cuda.memory_reserved()/2**20})
            runtime.forget(key)
            if runtime.history(key) or runtime.sessions: raise RuntimeError("Session memory was retained")
            gc.collect()
            print("Completed synthetic session",session+1,flush=True)
        # Force the configured generation ceiling, rather than a short naturally terminated answer.
        tokens=model.tokenizer.encode("Synthetic resource benchmark. ",add_special_tokens=False)
        tokens=(tokens*math.ceil(2800/len(tokens)))[:2800]
        inputs=torch.tensor([tokens],device="cuda")
        torch.cuda.synchronize();start=time.monotonic()
        with torch.inference_mode():
            output=model.model.generate(inputs,attention_mask=torch.ones_like(inputs),
                min_new_tokens=384,max_new_tokens=384,do_sample=False,
                pad_token_id=model.tokenizer.eos_token_id,use_cache=True)
        torch.cuda.synchronize()
        stress={"prompt_tokens":2800,"generated_tokens":int(output.shape[-1]-2800),
                "seconds":time.monotonic()-start,"includes_review":False}
        del output,inputs
        elapsed=[row["seconds"] for row in rows]
        report={"model":args.model,"revision":model.entry["revision"],"adapter_sha256":model.adapter_sha256,
            "scope":"Local RTX laptop; synthetic single-worker measurements, not hosted throughput or clinical validation",
            "device":torch.cuda.get_device_name(0),"device_total_mb":torch.cuda.get_device_properties(0).total_memory/2**20,
            "load_seconds":model.load_seconds,"weight_bytes":model.entry["weight_bytes"],
            "adapter_bytes":sum(path.stat().st_size for path in (ROOT/args.adapter).glob("*") if path.is_file()),
            "sampled_peak_process_rss_mb":peak_rss[0]/2**20,
            "peak_cuda_allocated_mb":torch.cuda.max_memory_allocated()/2**20,
            "peak_cuda_reserved_mb":torch.cuda.max_memory_reserved()/2**20,
            "median_checked_reply_seconds":statistics.median(elapsed),
            "max_checked_reply_seconds":max(elapsed),"checked_reply_count":len(rows),
            "session_memory_cleared":not runtime.sessions,"concurrency":1,
            "maximum_generation_stress":stress,"rows":rows,"approved":False}
        path=ROOT/"docs"/("PERFORMANCE_"+args.model.split("/")[-1]+".json")
        path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({key:value for key,value in report.items() if key!="rows"}),flush=True)
    finally:
        stop.set();sampler.join(timeout=1)


if __name__=="__main__":main()
