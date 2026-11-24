                                                              

                                                             
                                                                               
                                                                   
                                                                                 
                                                                          
                                                                                     
import contextlib
import io
import json
import os
import sys

import actiview_core as C
from official_stubs import import_official_evaluator

with contextlib.redirect_stdout(io.StringIO()):
    ev = import_official_evaluator()
    E = ev.Evaluator(data_path=C.ASSET)
qidx = {d["id"]: i for i, d in enumerate(C.load_data())}
recs = {}
for path in sys.argv[1:]:
    with open(path) as fr:
        for line in fr:
            line = line.strip()
            if line:
                r = json.loads(line)
                if r.get("kind") == "terminal":
                    recs[(r["setting"], r["questionId"])] = r
all_answers, all_options = list(E.answers), list(E.options)
summary = {}
for s in C.SETTINGS:
    rs = sorted((r for (st, _), r in recs.items() if st == s), key=lambda r: qidx[r["questionId"]])
    if not rs:
        continue
    idx = [qidx[r["questionId"]] for r in rs]
    E.answers = [all_answers[i] for i in idx]
    E.options = [all_options[i] for i in idx]
    acc = E.cal_acc([r["prediction"] for r in rs])
    bridge = sum(r["correct"] for r in rs) / len(rs)
    assert abs(acc - bridge) < 1e-12, (s, acc, bridge)
    views = sum(len(r["viewsUsed"]) for r in rs) / len(rs)
    summary[s] = {"n": len(rs), "complete": len(rs) == len(all_answers), "acc": round(100 * acc, 2),
                  "avgViewsUsed": round(views, 3), "avgSteps": round(sum(r["steps"] for r in rs) / len(rs), 3)}
if all(s in summary and summary[s]["complete"] for s in C.SETTINGS):
    summary["modelAVG"] = round(sum(summary[s]["acc"] for s in C.SETTINGS) / 5, 2)
print(json.dumps(summary, indent=1))
