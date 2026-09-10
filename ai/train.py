"""Reproducible small LoRA experiment. Only explicitly synthetic records are trained."""
import hashlib
import json
import random
import time
from ai.config import ROOT, BASE_MODEL, LOCK, ADAPTER, SYSTEM, LANGUAGES
from ai.checkpoint_guard import base_snapshot
import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer

def main():
    random.seed(42)
    torch.manual_seed(42)
    if not torch.cuda.is_available(): raise RuntimeError("CUDA required; no silent CPU fallback")
    base_snapshot()
    dataset_file=ROOT/"training"/"examples.json"
    dataset=json.loads(dataset_file.read_text(encoding="utf-8"))
    train=dataset["records"]
    held={row["user"].strip().casefold() for row in dataset["evaluation"]}
    if any(row["split"]!="train" or row["user"].strip().casefold() in held for row in train):
        raise ValueError("Dataset separation violated")
    tokenizer=AutoTokenizer.from_pretrained(BASE_MODEL,revision=LOCK[BASE_MODEL]["revision"],local_files_only=True)
    base=AutoModelForCausalLM.from_pretrained(BASE_MODEL,revision=LOCK[BASE_MODEL]["revision"],
        dtype=torch.bfloat16,device_map={"":"cuda:0"},use_safetensors=True,
        trust_remote_code=False,local_files_only=True,attn_implementation="sdpa")
    model=get_peft_model(base,LoraConfig(r=8,lora_alpha=16,target_modules=["q_proj","v_proj"],
                                        lora_dropout=0.05,bias="none",task_type="CAUSAL_LM"))
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant":False})
    model.enable_input_require_grads()
    model.config.use_cache=False
    trainable=[p for p in model.parameters() if p.requires_grad]
    optimizer=torch.optim.AdamW(trainable,lr=1e-4,weight_decay=0.01)
    examples=[]
    for row in train:
        prefix=[{"role":"system","content":SYSTEM+"\nReply language: "+LANGUAGES[row["language"]]},
                {"role":"user","content":row["user"]}]
        prompt=tokenizer.apply_chat_template(prefix,tokenize=False,add_generation_prompt=True,enable_thinking=False)
        completion=json.dumps(row["response"],ensure_ascii=False)+tokenizer.eos_token
        prompt_ids=tokenizer(prompt,add_special_tokens=False)["input_ids"]
        target_ids=tokenizer(completion,add_special_tokens=False)["input_ids"]
        # Never silently truncate away the supervised answer.
        if len(prompt_ids)+len(target_ids)>768: raise ValueError("Example exceeds training budget")
        examples.append((prompt_ids+target_ids,[-100]*len(prompt_ids)+target_ids))
    before={name:p.detach().float().cpu().clone() for name,p in model.named_parameters() if p.requires_grad}
    losses=[]
    started=time.monotonic()
    optimizer.zero_grad()
    model.train()
    steps=0
    epochs=6
    for epoch in range(epochs):
        order=list(range(len(examples)));random.shuffle(order)
        for position,index in enumerate(order):
            ids,labels=examples[index]
            outputs=model(input_ids=torch.tensor([ids],device="cuda"),labels=torch.tensor([labels],device="cuda"),
                          attention_mask=torch.ones((1,len(ids)),device="cuda",dtype=torch.long))
            loss=outputs.loss
            if not torch.isfinite(loss): raise RuntimeError("Non-finite training loss")
            (loss/4).backward()
            losses.append(float(loss.detach()))
            if (position+1)%4==0 or position+1==len(order):
                torch.nn.utils.clip_grad_norm_(trainable,1.0)
                optimizer.step();optimizer.zero_grad(set_to_none=True);steps+=1
                print(json.dumps({"epoch":epoch+1,"step":steps,"loss":round(sum(losses[-4:])/min(len(losses),4),4),
                                  "peak_vram_mb":round(torch.cuda.max_memory_allocated()/2**20)}),flush=True)
    changed=sum(not torch.equal(before[name],p.detach().float().cpu()) for name,p in model.named_parameters() if p.requires_grad)
    if not changed: raise RuntimeError("No adapter weights changed")
    ADAPTER.mkdir(parents=True,exist_ok=True)
    model.save_pretrained(ADAPTER,safe_serialization=True)
    tokenizer.save_pretrained(ADAPTER)
    weights=ADAPTER/"adapter_model.safetensors"
    report={"status":"trained_not_approved","base_model":BASE_MODEL,"base_revision":LOCK[BASE_MODEL]["revision"],
        "dataset_sha256":hashlib.sha256(dataset_file.read_bytes()).hexdigest(),"train_examples":len(train),
        "held_out_examples":len(dataset["evaluation"]),"epochs":epochs,"optimizer_steps":steps,
        "system_prompt_sha256":hashlib.sha256(SYSTEM.encode()).hexdigest(),
        "trainable_parameters":sum(p.numel() for p in trainable),"changed_parameter_tensors":changed,
        "adapter_sha256":hashlib.sha256(weights.read_bytes()).hexdigest(),"elapsed_seconds":time.monotonic()-started,
        "peak_vram_mb":torch.cuda.max_memory_allocated()/2**20,"losses":losses,
        "clinical_validation":False,"seed":42}
    (ADAPTER/"training-report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    (ROOT/"docs"/"TRAINING_REPORT.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("Actual adapter training finished. Evaluation is still required.",flush=True)
if __name__=="__main__": main()
