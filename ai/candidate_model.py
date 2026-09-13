"""Candidate benchmarks are isolated from the application's approved model configuration."""
import json
import time
from ai.config import ROOT
from ai.model import LocalModel
from ai.candidate_download import validate_snapshot

class CandidateModel(LocalModel):
    def __init__(self,name,quantized=False,adapter=None,measure=True):
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM, Qwen3_5ForConditionalGeneration, BitsAndBytesConfig
        self.torch=torch
        self.name=name
        self.entry=json.loads((ROOT/"ai/candidates.json").read_text())[name]
        snapshot=ROOT/"models/hf/hub"/("models--"+name.replace("/","--"))/"snapshots"/self.entry["revision"]
        validate_snapshot(snapshot,self.entry)
        if not torch.cuda.is_available(): raise RuntimeError("CUDA required for candidate measurement")
        if measure:
            torch.cuda.reset_peak_memory_stats()
        self.tokenizer=AutoTokenizer.from_pretrained(snapshot,local_files_only=True,trust_remote_code=False)
        loader=Qwen3_5ForConditionalGeneration if self.entry["model_type"]=="qwen3_5" else AutoModelForCausalLM
        options={}
        if quantized and not self.entry.get("prequantized"):
            options["quantization_config"]=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16)
        start=time.monotonic()
        self.model=loader.from_pretrained(snapshot,dtype=torch.bfloat16,device_map={"":"cuda:0"},
                local_files_only=True,use_safetensors=True,trust_remote_code=False,attn_implementation="sdpa",**options)
        self.adapter_sha256=None
        if adapter is not None:
            import hashlib
            from pathlib import Path
            from peft import PeftModel
            adapter=Path(adapter).resolve()
            adapter.relative_to((ROOT/"models/experiments").resolve())
            receipt=json.loads((adapter/"training-report.json").read_text())
            self.adapter_sha256=hashlib.sha256((adapter/"adapter_model.safetensors").read_bytes()).hexdigest()
            if (receipt["model"]!=name or receipt["revision"]!=self.entry["revision"]
                    or receipt["adapter_sha256"]!=self.adapter_sha256):
                raise ValueError("Candidate adapter provenance mismatch")
            self.model=PeftModel.from_pretrained(self.model,str(adapter),is_trainable=False,
                local_files_only=True,use_safetensors=True)
        self.model.eval()
        self.load_seconds=time.monotonic()-start
        self.quantized=quantized or self.entry.get("prequantized",False)
