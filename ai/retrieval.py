"""Small SQLite vector collection containing approved public references only."""
import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from ai.config import ROOT, EMBED_MODEL, LOCK, INDEX

@dataclass(frozen=True)
class Passage:
    id: str
    text: str
    title: str
    url: str
    score: float = 0.0

class Embedder:
    def __init__(self):
        import torch
        from transformers import AutoModel, AutoTokenizer
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(EMBED_MODEL, revision=LOCK[EMBED_MODEL]["revision"],local_files_only=True)
        self.model = AutoModel.from_pretrained(EMBED_MODEL, revision=LOCK[EMBED_MODEL]["revision"],
                                              use_safetensors=True, trust_remote_code=False,local_files_only=True).eval().to("cpu")

    def encode(self, texts, query=False):
        torch = self.torch
        prefix = "query: " if query else "passage: "
        batches = []
        with torch.inference_mode():
            for start in range(0, len(texts), 8):
                tokens = self.tokenizer([prefix + x for x in texts[start:start+8]],
                                        return_tensors="pt", padding=True, truncation=True, max_length=512)
                hidden = self.model(**tokens).last_hidden_state
                mask = tokens["attention_mask"].unsqueeze(-1)
                pooled = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1)
                batches.append(torch.nn.functional.normalize(pooled, p=2, dim=1).numpy())
        return np.concatenate(batches).astype("<f4")

def build_index(embedder, path=INDEX):
    source_file = ROOT / "knowledge" / "passages.json"
    corpus = json.loads(source_file.read_text(encoding="utf-8"))
    if not corpus or len(corpus) > 1000:
        raise ValueError("Expected a bounded, reviewed reference collection")
    for item in corpus:
        if item["sha256"] != hashlib.sha256(item["text"].encode()).hexdigest():
            raise ValueError("Reference text changed without provenance update")
        if item["reuse"] != "NIMH public-domain text; general information only":
            raise ValueError("Reference reuse review missing")
    vectors = embedder.encode([item["text"] for item in corpus])
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS passages(id TEXT PRIMARY KEY,text TEXT,title TEXT,url TEXT,vector BLOB)")
        db.execute("DELETE FROM passages")
        for item, vector in zip(corpus,vectors):
            db.execute("INSERT INTO passages VALUES (?,?,?,?,?)",
                       (item["id"],item["text"],item["title"],item["url"],vector.tobytes()))
        db.executemany("INSERT OR REPLACE INTO metadata VALUES (?,?)", [
            ("model",EMBED_MODEL),("revision",LOCK[EMBED_MODEL]["revision"]),
            ("corpus_sha256",hashlib.sha256(source_file.read_bytes()).hexdigest()),
            ("dimensions",str(vectors.shape[1]))])
    return len(corpus)

class Retriever:
    def __init__(self, embedder, path=INDEX):
        self.embedder = embedder
        with sqlite3.connect(path) as db:
            meta = dict(db.execute("SELECT key,value FROM metadata"))
            rows = db.execute("SELECT id,text,title,url,vector FROM passages ORDER BY id").fetchall()
        expected = hashlib.sha256((ROOT/"knowledge"/"passages.json").read_bytes()).hexdigest()
        if meta.get("revision") != LOCK[EMBED_MODEL]["revision"] or meta.get("corpus_sha256") != expected:
            raise ValueError("Rebuild reference vectors for the pinned corpus/model")
        if not rows:
            raise ValueError("Empty reference index")
        canonical = {item["id"]: item for item in json.loads((ROOT/"knowledge"/"passages.json").read_text(encoding="utf-8"))}
        if len(rows) != len(canonical):
            raise ValueError("Reference collection size changed")
        for row in rows:
            item = canonical.get(row[0])
            if item is None or tuple(row[:4]) != (item["id"],item["text"],item["title"],item["url"]):
                raise ValueError("Indexed source content differs from the reviewed corpus")
        self.passages = [Passage(*row[:4]) for row in rows]
        self.vectors = np.stack([np.frombuffer(row[4],dtype="<f4") for row in rows])
        if self.vectors.shape[1] != int(meta["dimensions"]) or not np.isfinite(self.vectors).all():
            raise ValueError("Invalid reference vectors")

    def search(self, query, limit=3):
        if not query.strip():
            return []
        vector = self.embedder.encode([query],query=True)[0]
        scores = self.vectors @ vector
        indices = np.argsort(-scores)[:min(limit,3)]
        return [Passage(**(self.passages[i].__dict__ | {"score":float(scores[i])}))
                for i in indices if scores[i] >= 0.7]
