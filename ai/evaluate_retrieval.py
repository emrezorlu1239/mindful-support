import json
from ai.config import ROOT
from ai.retrieval import Embedder,Retriever
tests=[("Uyumadan önce telefonuma bakıyorum, uyku düzenimi nasıl destekleyebilirim?","care-3"),
       ("I cannot stop scrolling before bed. How can I support my sleep routine?","care-3"),
       ("Kendimi yalnız hissediyorum ve yakınlarımla konuşmak istiyorum.","care-8"),
       ("I feel lonely and want to connect with friends who support me.","care-8"),
       ("Günlük tutmak stresimi anlamama yardımcı olabilir mi?","stress-2"),
       ("Can keeping a journal help me understand stress?","stress-2"),
       ("Çok fazla işim var, öncelik belirlemeyi nasıl deneyebilirim?","care-5"),
       ("How can I set priorities when I have too many tasks?","care-5")]
retriever=Retriever(Embedder())
rows=[]
for query,expected in tests:
    found=retriever.search(query)
    row={"query":query,"expected":expected,"ids":[p.id for p in found],"scores":[p.score for p in found],
         "hit":expected in [p.id for p in found]}
    rows.append(row)
report={"passages":len(retriever.passages),"evaluations":rows,"hit_at_3":sum(r["hit"] for r in rows)/len(rows),
        "clinical_validation":False,"scope":"Eight hand-authored development queries; not a broad retrieval benchmark"}
(ROOT/"docs"/"RETRIEVAL_EVALUATION.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,ensure_ascii=True),flush=True)
