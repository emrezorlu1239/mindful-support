"""Resumable range download from official pinned Hugging Face URLs, with full LFS SHA verification."""
import hashlib
import json
import math
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import requests
from ai.config import ROOT,BASE_MODEL,LOCK

def file_sha256(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source,"sha256").hexdigest()

def expose_snapshot(target,link):
    link.parent.mkdir(parents=True,exist_ok=True)
    if not link.exists():
        try: os.link(target,link)
        except OSError: shutil.copyfile(target,link)

def get_metadata():
    r=requests.get("https://huggingface.co/api/models/"+BASE_MODEL,
                   params={"blobs":"true","revision":LOCK[BASE_MODEL]["revision"]},timeout=30)
    r.raise_for_status()
    data=r.json()
    if data["sha"]!=LOCK[BASE_MODEL]["revision"]: raise ValueError("Model revision changed")
    return data

def download():
    revision=LOCK[BASE_MODEL]["revision"]
    hub=ROOT/"models"/"hf"/"hub"/("models--"+BASE_MODEL.replace("/","--"))
    snapshot=hub/"snapshots"/revision
    metadata=get_metadata()
    for item in metadata["siblings"]:
        name=item["rfilename"]
        if not name.endswith(".safetensors"): continue
        digest=item["lfs"]["sha256"];size=item["lfs"]["size"]
        target=hub/"blobs"/digest
        if target.exists() and file_sha256(target)==digest:
            expose_snapshot(target,snapshot/name)
            print("Already verified",name,flush=True)
            continue
        parts=ROOT/"work"/"model-parts"/digest
        parts.mkdir(parents=True,exist_ok=True)
        chunk_size=2*1024*1024
        count=math.ceil(size/chunk_size)
        def fetch(index):
            start=index*chunk_size;end=min(size-1,start+chunk_size-1)
            path=parts/str(index)
            if path.exists() and path.stat().st_size==end-start+1:return index
            url="https://huggingface.co/"+BASE_MODEL+"/resolve/"+revision+"/"+name
            for attempt in range(4):
                try:
                    response=requests.get(url,params={"download":"true","part":str(index)},
                        headers={"Range":f"bytes={start}-{end}"},timeout=(15,45))
                    if response.status_code!=206 or response.headers.get("Content-Range")!=f"bytes {start}-{end}/{size}":
                        raise RuntimeError("Range response mismatch")
                    data=response.content
                    if len(data)!=end-start+1: raise RuntimeError("Short model range")
                    path.write_bytes(data)
                    return index
                except Exception:
                    if attempt==3: raise
                    time.sleep(attempt+1)
        completed=0
        with ThreadPoolExecutor(max_workers=12) as pool:
            for future in as_completed([pool.submit(fetch,i) for i in range(count)]):
                future.result();completed+=1
                if completed%20==0 or completed==count:
                    print(name,completed,"/",count,"chunks",flush=True)
        temporary=target.with_suffix(".assembled")
        target.parent.mkdir(parents=True,exist_ok=True)
        sha=hashlib.sha256()
        with temporary.open("wb") as out:
            for index in range(count):
                data=(parts/str(index)).read_bytes();sha.update(data);out.write(data)
        if sha.hexdigest()!=digest: raise ValueError("Downloaded model hash mismatch")
        os.replace(temporary,target)
        expose_snapshot(target,snapshot/name)
        print("SHA256 verified:",name,flush=True)
    print("Pinned base weights ready",flush=True)
if __name__=="__main__":download()
