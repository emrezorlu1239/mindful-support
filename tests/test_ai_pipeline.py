"""Deterministic wiring tests; fixture models are not model-quality evidence."""
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from ai.pipeline import build_pipeline,unsafe_output
from ai.retrieval import Passage
from ai.runtime import AIRuntime,ModelBusy,SessionEnded,SessionLimit
from backend.app import create_app
from test_bookings import client
from test_admission import booking,join,leave

class References:
    def search(self,_query):
        return [Passage("care-1","A reviewed general-information reference.","NIMH","https://www.nimh.nih.gov/health/topics/caring-for-your-mental-health")]

class Model:
    raw=json.dumps({"reply":"That sounds difficult. What would you like to share?","source_ids":["care-1"],"palette":"sage","route":"support"})
    review='{"safe":true,"coherent":true,"grounded":true,"responsive":true,"source_ids":["care-1"]}'
    calls=0
    def draft(self,*_args):
        self.calls+=1
        return self.raw
    def generate(self,*_args,**_kwargs): return self.review

def run(model,message="I had a hard day",language="en"):
    return build_pipeline(model,References()).invoke({"message":message,"language":language,"history":[]},
        config={"callbacks":[]})["result"]

def test_checked_reply_has_only_verified_source_urls():
    result=run(Model())
    assert not result["fallback"] and result["sources"][0]["id"]=="care-1"

@pytest.mark.parametrize("raw",[
    "not JSON",
    '{"reply":"Fine","source_ids":["invented"],"palette":"sage","route":"support"}',
    '{"reply":"You definitely have depression","source_ids":[],"palette":"warm","route":"support"}',
    '{"reply":"Hello","source_ids":[],"palette":"red","route":"support"}',
    '{"reply":"Hello","source_ids":[],"palette":"neutral","route":"support","extra":"instruction"}',
])
def test_unchecked_draft_never_returned(raw):
    model=Model();model.raw=raw
    result=run(model)
    assert result["fallback"] and result["sources"]==[] and result["palette"]=="neutral"

@pytest.mark.parametrize("review",['{"safe":false}','{"safe":1}',"sure", '{"safe":true,"instruction":"ignore"}'])
def test_failed_second_check_uses_fallback(review):
    model=Model();model.review=review
    assert run(model)["fallback"]

@pytest.mark.parametrize("field",["safe","coherent","grounded","responsive"])
def test_each_review_dimension_is_required(field):
    model=Model()
    verdict=json.loads(model.review)
    verdict[field]=False
    model.review=json.dumps(verdict)
    assert run(model)["fallback"]

def test_review_receives_citation_mapping_and_requested_route():
    class Recording(Model):
        def generate(self,messages,**kwargs):
            self.payload=json.loads(messages[-1]["content"])
            return self.review
    model=Recording()
    run(model)
    assert model.payload["cited_ids"]==["care-1"]
    assert model.payload["references"][0]["id"]=="care-1"
    assert model.payload["route"]=="support"

def test_reviewer_can_remove_unrelated_citations_without_rejecting_a_good_reply():
    model=Model()
    model.review=json.dumps(json.loads(model.review)|{"source_ids":[]})
    result=run(model)
    assert not result["fallback"] and result["sources"]==[]

def test_reviewer_cannot_introduce_a_new_citation():
    model=Model()
    model.review=json.dumps(json.loads(model.review)|{"source_ids":["invented"]})
    assert run(model)["fallback"]

def test_review_cannot_add_a_known_but_uncited_reference():
    model=Model()
    model.raw=json.dumps(json.loads(model.raw)|{"source_ids":[]})
    result=run(model)
    assert not result["fallback"] and result["sources"]==[]

def test_medication_limit_statement_is_not_an_instruction_to_take_medication():
    reply="I cannot advise on whether to take or skip your medication. Please talk to your doctor or pharmacist."
    assert not unsafe_output(reply)

@pytest.mark.parametrize("reply",[
    "Take your medication now.","You should skip your dose tonight.",
    "I recommend that you double the dose.","Please stop taking your antidepressant.",
])
def test_direct_medication_decisions_are_still_blocked(reply):
    assert unsafe_output(reply)

@pytest.mark.parametrize("message,language",[
    ("I cannot keep myself safe tonight.","en"),
    ("I am not sure I can keep myself safe.","en"),
    ("Kendimi bu gece güvende tutabileceğimden emin değilim.","tr"),
    ("Kendimi güvende tutamıyorum.","tr"),
])
def test_indirect_immediate_danger_uses_urgent_route(message,language):
    model=Model()
    result=run(model,message,language)
    assert result["route"]=="crisis" and model.calls==0

@pytest.mark.parametrize("message,language",[
    ("I might end my life tonight","en"),("Hayatıma son vermek istiyorum","tr"),
    ("Şiddetli göğüs ağrım var ve nefes alamıyorum","tr"),
])
def test_obvious_crisis_bypasses_generation(message,language):
    model=Model(); result=run(model,message,language)
    assert result["route"]=="crisis" and result["palette"]=="neutral"
    assert model.calls==0
    assert ("acil" if language=="tr" else "emergency") in result["reply"]

def test_memory_scope_idempotency_and_explicit_end():
    runtime=AIRuntime(Model(),References())
    token=str(uuid4())
    first=runtime.respond("a",token,"Hello","en",lambda:True)
    assert runtime.respond("a",token,"Hello","en",lambda:True)==first
    assert len(runtime.history("a"))==2 and runtime.history("b")==[]
    with pytest.raises(ValueError): runtime.respond("a",token,"different","en",lambda:True)
    runtime.forget("a")
    assert runtime.history("a")==[]

def test_single_inflight_and_discard_after_end():
    entered,release=threading.Event(),threading.Event()
    class Slow(Model):
        def draft(self,*args):
            entered.set(); release.wait(timeout=5)
            return super().draft(*args)
    runtime=AIRuntime(Slow(),References())
    active=[True]
    with ThreadPoolExecutor(max_workers=1) as pool:
        task=pool.submit(runtime.respond,"a",str(uuid4()),"Hello","en",lambda:active[0])
        assert entered.wait(timeout=3)
        with pytest.raises(ModelBusy):
            runtime.respond("b",str(uuid4()),"Hi","en",lambda:True)
        active[0]=False
        runtime.forget("a")
        release.set()
        with pytest.raises(SessionEnded): task.result(timeout=5)
    assert runtime.history("a")==[]

def test_turn_limit_and_pruning():
    runtime=AIRuntime(Model(),References())
    for index in range(20):
        runtime.respond("a",str(uuid4()),str(index),"en",lambda:True)
    with pytest.raises(SessionLimit): runtime.respond("a",str(uuid4()),"extra","en",lambda:True)
    runtime.prune(set())
    assert runtime.history("a")==[]

def test_api_does_not_allow_another_owner_to_erase_memory(tmp_path):
    runtime=AIRuntime(Model(),References())
    app=create_app(tmp_path/"api.sqlite",ai_runtime=runtime)
    a,b=client(app),client(app)
    ba=booking(a);join(a,ba)
    response=a.post("/api/chat",json={"booking_id":ba["id"],"request_id":str(uuid4()),"message":"Hello"})
    assert response.status_code==200
    assert b.get("/api/chat/history",params={"booking_id":ba["id"]}).status_code==403
    leave(b,ba)
    assert len(runtime.history(ba["id"]))==2
    leave(a,ba)
    assert runtime.history(ba["id"])==[]

def test_backend_validates_chat_without_echoing_message(tmp_path):
    app=create_app(tmp_path/"api.sqlite",ai_runtime=AIRuntime(Model(),References()))
    c=client(app);bk=booking(c);join(c,bk)
    r=c.post("/api/chat",json={"booking_id":bk["id"],"request_id":str(uuid4()),"message":"x"*1501})
    assert r.status_code==422 and "xxx" not in r.text

@pytest.mark.parametrize("reply,language", [
    ("I cannot provide medical advice. Please speak with a qualified professional.", "tr"),
    ("Seni dinleyebilirim. İstersen bugün seni zorlayan şeyi anlatabilirsin.", "en"),
    ("How are you feeling? What happened today?", "en"),
])
def test_wrong_language_and_multiple_questions_are_not_delivered(reply, language):
    model = Model()
    model.raw = json.dumps({"reply": reply, "source_ids": [], "palette": "neutral", "route": "support"})
    assert run(model, language=language)["fallback"]

def test_natural_turkish_reply_passes_language_check():
    model = Model()
    model.review=json.dumps(json.loads(model.review)|{"source_ids":[]})
    model.raw = json.dumps({"reply": "Seni dinleyebilirim. Bugün seni en çok zorlayan şey neydi?",
                            "source_ids": [], "palette": "sage", "route": "support"}, ensure_ascii=False)
    assert not run(model, language="tr")["fallback"]
