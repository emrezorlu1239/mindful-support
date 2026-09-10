"""Execute the authorized local experiment after verified downloads finish."""
import json
import subprocess
import sys
import time
from ai.config import ROOT,BASE_MODEL,LOCK
from ai.checkpoint_guard import base_snapshot,validate_shard_map

def main():
    snapshot=ROOT/"models"/"hf"/"hub"/("models--"+BASE_MODEL.replace("/","--"))/"snapshots"/LOCK[BASE_MODEL]["revision"]
    shards=validate_shard_map(json.loads((snapshot/"model.safetensors.index.json").read_text()))
    deadline=time.monotonic()+7200
    print("Waiting for fully verified base-model shards; no training has started.",flush=True)
    while not all((snapshot/name).exists() for name in shards):
        if time.monotonic()>deadline: raise TimeoutError("Base-model download is still incomplete")
        time.sleep(20)
    for module in ["ai.model","ai.train","ai.evaluate"]:
        print("Starting",module,flush=True)
        subprocess.run([sys.executable,"-m",module],cwd=ROOT,check=True)
    print("Local experiment finished. Inspect the evaluation report before enabling AI.",flush=True)
if __name__=="__main__":main()
