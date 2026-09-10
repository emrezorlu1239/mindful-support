"""In-process, bounded conversation memory. Explicitly not a distributed model server."""
import hashlib
import threading
import time
from dataclasses import dataclass, field
from ai.pipeline import build_pipeline

class ModelBusy(Exception): pass
class SessionLimit(Exception): pass
class SessionEnded(Exception): pass

@dataclass
class Session:
    messages: list=field(default_factory=list)
    requests: dict=field(default_factory=dict)

class AIRuntime:
    def __init__(self,model,retriever):
        self.graph=build_pipeline(model,retriever)
        self.sessions={}
        self.memory_lock=threading.Lock()
        self.compute=threading.BoundedSemaphore(1)
        self.ready=True
    def prune(self,active_ids):
        with self.memory_lock:
            for key in list(self.sessions):
                if key not in active_ids: del self.sessions[key]
    def forget(self,booking_id):
        with self.memory_lock:
            self.sessions.pop(booking_id,None)
    def history(self,booking_id):
        with self.memory_lock:
            session=self.sessions.get(booking_id)
            return list(session.messages) if session else []
    def respond(self,booking_id,request_id,message,language,is_active):
        if not self.compute.acquire(blocking=False): raise ModelBusy()
        try:
            if not is_active(): raise SessionEnded()
            fingerprint=hashlib.sha256(message.encode()).hexdigest()
            with self.memory_lock:
                session=self.sessions.setdefault(booking_id,Session())
                if request_id in session.requests:
                    previous_hash,result=session.requests[request_id]
                    if previous_hash != fingerprint: raise ValueError("Request ID already used")
                    return result
                if len(session.messages)>=40: raise SessionLimit()
                history=[{"role":row["role"],"content":row["content"]} for row in session.messages[-6:]]
            result=self.graph.invoke({"message":message,"language":language,"history":history},
                                     config={"callbacks":[],"recursion_limit":8})["result"]
            if not is_active():
                self.forget(booking_id)
                raise SessionEnded()
            with self.memory_lock:
                # A cancelled session cannot be recreated by an in-flight generation.
                if self.sessions.get(booking_id) is not session: raise SessionEnded()
                session.messages.extend([{"role":"user","content":message},
                    {"role":"assistant","content":result["reply"],"sources":result["sources"]}])
                session.requests[request_id]=(fingerprint,result)
            return result
        finally:
            self.compute.release()

def load_approved_runtime():
    from ai.serving import load_selected_runtime
    return load_selected_runtime()
