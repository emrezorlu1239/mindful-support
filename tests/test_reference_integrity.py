import json
import sqlite3
import numpy as np
import pytest
from ai import retrieval
from ai.runtime import load_approved_runtime
from ai.checkpoint_guard import validate_shard_map

@pytest.mark.parametrize("name",["../private.txt","C:/Windows/test","\\\\.\\pipe\\test","model-00003-of-00003.safetensors"])
def test_checkpoint_shard_paths_are_allowlisted(name):
    with pytest.raises(ValueError):
        validate_shard_map({"weight_map":{"layer":name}})

class FixtureEmbeddings:
    def encode(self,texts,query=False):
        vectors=[]
        for text in texts:
            vector=np.zeros(384,dtype="<f4")
            vector[0 if "sleep" in text.lower() else 1]=1
            vectors.append(vector)
        return np.stack(vectors)

def test_reference_index_contains_no_query_rows_and_rejects_tampering(tmp_path):
    path=tmp_path/"vectors.sqlite"
    embedder=FixtureEmbeddings()
    retrieval.build_index(embedder,path)
    index=retrieval.Retriever(embedder,path)
    result=index.search("private sample query")
    assert result
    with sqlite3.connect(path) as db:
        before=db.execute("SELECT COUNT(*) FROM passages").fetchone()[0]
        assert db.execute("SELECT COUNT(*) FROM passages WHERE text LIKE '%private sample%'").fetchone()[0]==0
        db.execute("UPDATE passages SET url='https://evil.example' WHERE id=?",(result[0].id,))
    with pytest.raises(ValueError,match="differs from the reviewed corpus"):
        retrieval.Retriever(embedder,path)
    assert before==13

def test_adapter_activation_fails_without_receipt(tmp_path,monkeypatch):
    import ai.serving
    monkeypatch.setattr(ai.serving,"selection",lambda: ({},tmp_path,tmp_path/"evaluation.json",{}))
    with pytest.raises(RuntimeError,match="evaluation is missing"):
        load_approved_runtime()

def test_adapter_activation_fails_closed_for_failed_or_changed_weights(tmp_path,monkeypatch):
    import ai.serving
    spec={"model":"test","supported_languages":["en","tr"],"concurrent_generations":1}
    monkeypatch.setattr(ai.serving,"selection",lambda: (spec,tmp_path,tmp_path/"evaluation.json",{"revision":"pinned"}))
    monkeypatch.setattr(ai.serving,"serving_fingerprint",lambda: {})
    receipt=tmp_path/"evaluation.json"
    receipt.write_text(json.dumps({"approved_for_local_demo":False}))
    with pytest.raises(RuntimeError,match="not approved"):
        load_approved_runtime()
    receipt.write_text(json.dumps({"approved_for_local_demo":True,"adapter_sha256":"incorrect"}))
    (tmp_path/"adapter_model.safetensors").write_bytes(b"test fixture, not a model")
    with pytest.raises(RuntimeError,match="does not match"):
        load_approved_runtime()

@pytest.mark.parametrize("changed", ["code", "packages"])
def test_adapter_activation_rejects_stale_evaluation(tmp_path, monkeypatch, changed):
    import hashlib
    import ai.serving
    spec={"model":"test","supported_languages":["en","tr"],"concurrent_generations":1}
    monkeypatch.setattr(ai.serving,"selection",lambda: (spec,tmp_path,tmp_path/"evaluation.json",{"revision":"pinned"}))
    content = b"fixture weights"
    (tmp_path/"adapter_model.safetensors").write_bytes(content)
    fingerprint = {"code": "reviewed", "packages": "reviewed"}
    (tmp_path/"evaluation.json").write_text(json.dumps({
        "approved_for_local_demo": True,
        "adapter_sha256": hashlib.sha256(content).hexdigest(),
        "model":"test","revision":"pinned",
        "fingerprint": fingerprint,
    }))
    current = {**fingerprint, changed: "changed"}
    monkeypatch.setattr(ai.serving, "serving_fingerprint", lambda: current)
    with pytest.raises(RuntimeError, match="configuration changed"):
        load_approved_runtime()
