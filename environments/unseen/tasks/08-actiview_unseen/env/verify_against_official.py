                                                                                         
                                                                                      
                                                                                      
                                                                                  
                                                        
import copy
import os
import random
import sys

import actiview_core as C
from official_stubs import import_official_evaluator

ev_mod = import_official_evaluator()
A = C.ASSET
E = ev_mod.EvaluatorChat(data_path=A, image_path=os.path.join(A, "images"),
                         image_split_path=os.path.join(A, "images_split"), model="gpt")
data = C.load_data()
insts = C.load_instances()
n = len(data)
fails = []


def check(cond, what):
    if not cond:
        fails.append(what)


                                                                      
ZOOM_SEL = ["1,3", "2", "1, 3", "upperleft,4", "none", "1,2,3,4", "upper", "left", "3.4", "4,1", "right,2", "lowerright"]
ANSWERS = ["A", "B. x", "Answer: C", "(A)", "b", "GOLDTEXT", "D.", "Z", "A) foo", " B"]


def answer_for(i, d):
    a = ANSWERS[i % len(ANSWERS)]
    return d["options"][d["answer"]] if a == "GOLDTEXT" else a


def drive(gen, replies):
    reqs, out = [], None
    req = next(gen)
    k = 0
    while True:
        reqs.append(req)
        try:
            req = gen.send(replies(k, req))
        except StopIteration as s:
            out = s.value
            break
        k += 1
    return reqs, out


                                                                       
off_sel = list(E.format_data4zooming())
check(len(off_sel) == n, "zoom count")
sel_replies = [ZOOM_SEL[i % len(ZOOM_SEL)] for i in range(n)]
off_qa = list(E.format_data4zooming_qa(sel_replies))
zoom_preds_off = []
zoom_correct_bridge = []
zi = [e for e in insts if e["setting"] == "zoom"]
for i, inst in enumerate(zi):
    d = data[i]
    ans = answer_for(i, d)
    _, gen = C.make_episode(inst)
    reqs, out = drive(gen, lambda k, r: sel_replies[i] if k == 0 else ans)
    o_imgs, o_msgs = off_sel[i]
    check(reqs[0]["message"] == o_msgs[0]["content"][-1]["text"], f"zoom sel text {i}")
    check(reqs[0]["images"] == [o_imgs], f"zoom sel imgs {i}")
    q_imgs, q_msgs = off_qa[i]
    check(reqs[1]["message"] == q_msgs[0]["content"][-1]["text"], f"zoom qa text {i}")
    check(reqs[1]["images"] == q_imgs, f"zoom qa imgs {i}")
    check(len(q_msgs[0]["content"]) - 1 == len(q_imgs), f"zoom qa image slots {i}")
    zoom_preds_off.append(ans)
    zoom_correct_bridge.append(C.finish(inst, d, out, len(reqs))["correct"])
acc_off = E.cal_acc(zoom_preds_off)
acc_br = sum(zoom_correct_bridge) / n
check(abs(acc_off - acc_br) < 1e-12, f"zoom acc {acc_off} vs {acc_br}")
print(f"zoom: {n} instances compared; official cal_acc={acc_off:.4f} bridge={acc_br:.4f}", file=sys.stderr)

                                                                        
import json              
with open(os.path.join(A, "shifting_level.json")) as fr:
    levels = json.loads(fr.read())


def stop_after(i, setting):
                                                                                      
                                                                            
    return (i + C.SETTINGS.index(setting)) % 4 + 1


YES_FORMS = ["Yes", "yes", "No.", "Yes, I need more."]
NO_FORMS = ["No", "no", "NO"]

for setting in C.SETTINGS[1:]:
    rec = []

    def fake_get_response(self, model, processor, prompt, images, generation_kwargs):
        rec.append((copy.deepcopy(prompt), list(images)))
        cur = rec_items[-1]
        text = prompt[0]["content"][-1]["text"]
        if text.startswith("Carefully analysis"):
            cur["final"] = True
            return [answer_for(cur["i"], data[cur["i"]])]
        cur["dec"] += 1
        if cur["dec"] == stop_after(cur["i"], setting):
            return [NO_FORMS[cur["i"] % 3]]
        return [YES_FORMS[(cur["i"] + cur["dec"]) % 4]]

    rec_items = []
    orig_enum = enumerate

    class Track:
        def __iter__(self_inner):
            for i, d in orig_enum(E.data):
                rec_items.append({"i": i, "dec": 0, "start": len(rec)})
                yield i, d

    ev_mod.enumerate = lambda x, *a: Track() if x is E.data else orig_enum(x, *a)                                                    
    ev_mod.EvaluatorChat.get_response = fake_get_response
    if setting == "shift-R":
        ev_mod.random.seed(1234)                                                                       
        pre = []
    else:
        pre = levels[C.LEVEL_KEY[setting]]
    preds, used, orders = E.format_data4shifting(model=object(), pre_define_initial=pre, processor=None,
                                                 generation_kwargs=None)
    del ev_mod.enumerate
    si = [e for e in insts if e["setting"] == setting]
    check(orders == [e["startView"] for e in si], f"{setting} start views")
    correct = []
    for i, inst in enumerate(si):
        d = data[i]
        lo = rec_items[i]["start"]
        hi = rec_items[i + 1]["start"] if i + 1 < n else len(rec)
        off_calls = rec[lo:hi]
        st = {"dec": 0}

        def replies(k, req, i=i):
            if req["message"].startswith("Carefully analysis"):
                return answer_for(i, d)
            st["dec"] += 1
            if st["dec"] == stop_after(i, setting):
                return NO_FORMS[i % 3]
            return YES_FORMS[(i + st["dec"]) % 4]

        _, gen = C.make_episode(inst)
        reqs, out = drive(gen, replies)
        check(len(reqs) == len(off_calls), f"{setting} step count {i}: {len(reqs)} vs {len(off_calls)}")
        for (pm, pimgs), r in zip(off_calls, reqs):
            check(r["message"] == pm[0]["content"][-1]["text"], f"{setting} text {i}")
            check(r["images"] == pimgs, f"{setting} imgs {i}")
            check(len(pm[0]["content"]) - 1 == len(pimgs), f"{setting} image slots {i}")
        check([C.IMAGE_VIEWS[v] for v in used[i]] == out["viewsUsed"], f"{setting} used views {i}")
        check(preds[i] == out["prediction"], f"{setting} pred {i}")
        correct.append(C.finish(inst, d, out, len(reqs))["correct"])
    acc_off = E.cal_acc(preds)
    acc_br = sum(correct) / n
    check(abs(acc_off - acc_br) < 1e-12, f"{setting} acc {acc_off} vs {acc_br}")
    print(f"{setting}: {n} instances compared ({len(rec)} official model calls); "
          f"official cal_acc={acc_off:.4f} bridge={acc_br:.4f}", file=sys.stderr)

print(f"\nFAILURES: {len(fails)}", file=sys.stderr)
for f in fails[:30]:
    print("  ", f, file=sys.stderr)
sys.exit(1 if fails else 0)
