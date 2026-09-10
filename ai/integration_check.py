"""Real loopback HTTP integration with synthetic identities and a real adapted model."""
import hashlib
import json
import threading
import time
from uuid import uuid4
import requests
import uvicorn
from ai.config import ROOT
from ai.serving import selection
from ai.candidate_model import CandidateModel
from ai.retrieval import Embedder,Retriever
from ai.runtime import AIRuntime
from backend.app import create_app

def main():
    spec,adapter,_receipt,_entry=selection()
    model=CandidateModel(spec["model"],quantized=True,adapter=adapter)
    runtime=AIRuntime(model,Retriever(Embedder()))
    database=ROOT/"work"/("integration-"+uuid4().hex+".sqlite")
    app=create_app(database,ai_runtime=runtime)
    server=uvicorn.Server(uvicorn.Config(app,host="127.0.0.1",port=8012,access_log=False,log_level="critical"))
    thread=threading.Thread(target=server.run,daemon=True);thread.start()
    base="http://127.0.0.1:8012/api"
    clients=[requests.Session(),requests.Session()]
    for client in clients:
        client.headers.update({"Origin":"http://localhost:3000","Content-Type":"application/json"})
    def call(client,method,path,body=None):
        response=client.request(method,base+path,json=body,timeout=120)
        return response
    try:
        deadline=time.monotonic()+10
        while not server.started and thread.is_alive() and time.monotonic()<deadline:time.sleep(.05)
        if not server.started:raise RuntimeError("Loopback integration server did not start")
        a,b=clients
        bookings=[]
        for client,language in zip(clients,["en","tr"]):
            assert call(client,"POST","/bootstrap").status_code==200
            response=call(client,"POST","/bookings",{"first_name":"Synthetic","last_name":"Check",
                "gender":"unspecified","language":language,"adult_consent":True})
            assert response.status_code==201
            bookings.append(response.json())
        first,second=bookings
        assert call(a,"POST","/admission/join",{"booking_id":first["id"]}).json()["state"]=="active"
        waiting=call(b,"POST","/admission/join",{"booking_id":second["id"]}).json()
        assert waiting["state"]=="waiting" and waiting["people_ahead"]>=1
        health=call(a,"GET","/health").json()
        assert health["fine_tuned"] and health["chat_enabled"]
        prompt="I moved to a new city. Coming home to silence is hard, and I am not ready for advice."
        payload={"booking_id":first["id"],"request_id":str(uuid4()),"message":prompt}
        start=time.monotonic();response=call(a,"POST","/chat",payload);elapsed=time.monotonic()-start
        assert response.status_code==200
        reply=response.json();assert not reply["fallback"]
        retry=call(a,"POST","/chat",payload)
        assert retry.status_code==200 and retry.json()==reply
        assert len(call(a,"GET","/chat/history?booking_id="+first["id"]).json()["messages"])==2
        assert call(b,"GET","/chat/history?booking_id="+first["id"]).status_code==403
        assert call(b,"POST","/chat",{"booking_id":second["id"],"request_id":str(uuid4()),"message":"Hello"}).status_code==403
        assert call(a,"POST","/admission/leave",{"booking_id":first["id"]}).status_code==200
        assert not runtime.history(first["id"])
        assert call(b,"POST","/admission/status").json()["state"]=="active"
        second_reply=call(b,"POST","/chat",{"booking_id":second["id"],"request_id":str(uuid4()),
            "message":"Artık konuşmak istemiyorum. Görüşmeyi burada bitirelim."})
        assert second_reply.status_code==200
        assert call(b,"POST","/admission/leave",{"booking_id":second["id"]}).status_code==200
        assert not runtime.sessions
        assert prompt.encode() not in database.read_bytes()
        report={"scope":"Actual loopback HTTP with real NF4+QLoRA model and synthetic input; no public deployment",
            "model":spec["model"],"revision":model.entry["revision"],"adapter_sha256":model.adapter_sha256,
            "passed":True,"english_response_seconds":elapsed,"english_reply":reply,"turkish_reply":second_reply.json(),
            "checks":["real model readiness","FIFO waiting count","active-session authorization","owner history isolation",
                      "idempotent retry without a duplicate turn","queue promotion after leave","session memory removal",
                      "synthetic conversation absent from the appointment database"],
            "approved_for_publication":False}
        (ROOT/"docs/AI_HTTP_INTEGRATION.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("Real model HTTP integration passed.",flush=True)
    finally:
        for client in clients:client.close()
        server.should_exit=True;thread.join(timeout=10)
        if thread.is_alive():raise RuntimeError("Integration server did not stop")

if __name__=="__main__":main()
