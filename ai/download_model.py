from ai.config import BASE_MODEL, LOCK
from huggingface_hub import snapshot_download
if __name__=="__main__":
    path=snapshot_download(BASE_MODEL,revision=LOCK[BASE_MODEL]["revision"],
        allow_patterns=["*.safetensors","*.json","*.jinja","vocab.*","merges.txt","LICENSE","README.md"],
        max_workers=3)
    print("Pinned base model downloaded:",path,flush=True)
