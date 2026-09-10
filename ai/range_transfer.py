"""Bounded, resumable byte-range transfer for verified public artifacts."""
import hashlib
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import requests
from ai.config import ROOT

def download_file(url,size,digest,target,workers=12):
    target=Path(target)
    target.resolve().relative_to(ROOT.resolve())
    if target.is_file() and target.stat().st_size==size:
        with target.open("rb") as src:
            if hashlib.file_digest(src,"sha256").hexdigest()==digest: return target
    parts=ROOT/"work"/"range-parts"/digest
    parts.mkdir(parents=True,exist_ok=True)
    chunk_size=1024*1024
    count=math.ceil(size/chunk_size)
    def fetch(index):
        start=index*chunk_size;end=min(size-1,start+chunk_size-1)
        path=parts/str(index)
        if path.is_file() and path.stat().st_size==end-start+1:return
        for attempt in range(4):
            try:
                with requests.get(url,params={"download":"true","part":str(index)},
                        headers={"Range":f"bytes={start}-{end}"},stream=True,timeout=(10,25)) as response:
                    if response.status_code!=206 or response.headers.get("Content-Range")!=f"bytes {start}-{end}/{size}":
                        raise ValueError("Range response mismatch")
                    data=response.content
                    if len(data)!=end-start+1: raise ValueError("Short range")
                    path.write_bytes(data)
                    return
            except Exception:
                if attempt==3:raise
                time.sleep(attempt+1)
    completed=0
    started=time.monotonic()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for task in as_completed([pool.submit(fetch,index) for index in range(count)]):
            task.result();completed+=1
            if completed%100==0 or completed==count:
                print(target.name,completed,"/",count,"MiB chunks","elapsed",round(time.monotonic()-started),flush=True)
    temporary=target.with_suffix(".assembled")
    target.parent.mkdir(parents=True,exist_ok=True)
    sha=hashlib.sha256()
    with temporary.open("wb") as out:
        for index in range(count):
            content=(parts/str(index)).read_bytes();sha.update(content);out.write(content)
    if sha.hexdigest()!=digest:raise ValueError("Full artifact digest mismatch")
    os.replace(temporary,target)
    print("Verified",target.name,flush=True)
    return target

def main():
    import argparse,json
    from huggingface_hub import snapshot_download
    from ai.download_resumable import expose_snapshot
    from ai.candidate_download import validate_snapshot
    parser=argparse.ArgumentParser();parser.add_argument("model")
    parser.add_argument("--workers",type=int,default=12,choices=range(1,33))
    args=parser.parse_args()
    entry=json.loads((ROOT/"ai/candidates.json").read_text())[args.model]
    snapshot=Path(snapshot_download(args.model,revision=entry["revision"],
        allow_patterns=["*.json","*.jinja","vocab.*","merges.txt","LICENSE","README.md"],
        max_workers=2))
    for item in entry["weights"]:
        if Path(item["name"]).name!=item["name"]:raise ValueError("Nested weight paths are not allowed")
        target=snapshot.parent.parent/"blobs"/item["sha256"]
        url="https://huggingface.co/"+args.model+"/resolve/"+entry["revision"]+"/"+item["name"]
        download_file(url,item["size"],item["sha256"],target,workers=args.workers)
        expose_snapshot(target,snapshot/item["name"])
    validate_snapshot(snapshot,entry)
    print("Candidate ready:",args.model,flush=True)

if __name__=="__main__":main()
