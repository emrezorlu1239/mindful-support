import hashlib
import json
import re
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from ai.config import ROOT
from ai.retrieval import Embedder, build_index

def prepare():
    definitions = [
        ("care","Caring for Your Mental Health","https://www.nimh.nih.gov/health/topics/caring-for-your-mental-health",
         ["Get regular exercise.","Eat healthy, regular meals","Make sleep a priority","Try a relaxing activity.",
          "Set goals and priorities.","Practice gratitude.","Focus on positivity","Stay connected."]),
        ("stress","I'm So Stressed Out!","https://www.nimh.nih.gov/health/publications/so-stressed-out-fact-sheet",
         ["Learning what causes or triggers your stress","Keep a journal.","Identify and challenge your negative",
          "Reach out to your friends or family","If you are struggling to cope, or the symptoms"])
    ]
    records=[]
    retrieved=datetime.now(timezone.utc).isoformat()
    for key,title,url,prefixes in definitions:
        raw=(ROOT/"work"/(key+".html")).read_bytes()
        soup=BeautifulSoup(raw,"html.parser")
        texts=list(dict.fromkeys(re.sub(r"\s+"," ",node.get_text(" ",strip=True)).strip()
                                 for node in soup.find_all(["li","p"])))
        for index,prefix in enumerate(prefixes):
            candidates=[text for text in texts if text.startswith(prefix)]
            if not candidates:
                raise ValueError("Reviewed text not found: "+prefix)
            text=min(candidates,key=len)
            if key=="stress" and prefix=="Keep a journal.":
                # Preserve the source paragraph that gives this very short bullet its context.
                intro=next(t for t in texts if t.startswith("Learning what causes or triggers your stress"))
                text=intro+" "+text
            if len(text)>1600: raise ValueError("Unexpected source expansion")
            records.append(dict(id=key+"-"+str(index+1),text=text,title=title,url=url,language="en",
                publisher="National Institute of Mental Health",retrieved_at=retrieved,
                html_sha256=hashlib.sha256(raw).hexdigest(),sha256=hashlib.sha256(text.encode()).hexdigest(),
                reuse="NIMH public-domain text; general information only",
                policy_url="https://www.nimh.nih.gov/site-info/policies",
                review="Reuse and scope reviewed by coding agent; not clinically reviewed",
                purpose=["retrieval"],images_included=False))
    folder=ROOT/"knowledge"
    folder.mkdir(exist_ok=True)
    (folder/"passages.json").write_text(json.dumps(records,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return records

if __name__=="__main__":
    print("Preparing reviewed source excerpts",flush=True)
    prepare()
    print("Building multilingual semantic vectors on CPU",flush=True)
    count=build_index(Embedder())
    print("Indexed",count,"approved passages",flush=True)
