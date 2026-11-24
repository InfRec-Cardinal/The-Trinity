                                                           

                                                      

                                                                                                 
                                                               
                                                                                                                    
                                                                   
                                                           
   
import json
import sys

_OUT = sys.stdout
sys.stdout = sys.stderr                              

import actiview_core as C              


def emit(obj):
    _OUT.write(json.dumps(obj) + "\n")
    _OUT.flush()


def fail(msg):
    emit({"kind": "error", "message": msg})
    sys.exit(2)


def main():
    if len(sys.argv) != 2:
        fail("usage: actiview_bridge.py <instance_id>")
    inst = {e["id"]: e for e in C.load_instances()}.get(sys.argv[1])
    if inst is None:
        fail(f"unknown instance id: {sys.argv[1]}")
    d, gen = C.make_episode(inst)
    print(f"[actiview] {inst['id']} setting={inst['setting']} question={d['question']!r}", flush=True)
    req = next(gen)
    steps = 0
    while True:
        steps += 1
        emit({"kind": "player_request", "message": req["message"],
              "images": [C.png_b64(p) for p in req["images"]], "legal": req["legal"]})
        line = sys.stdin.readline()
        if not line:
            fail(f"stdin closed before reply to step {steps}")
        try:
            action = json.loads(line)["action"]
        except Exception as e:                
            fail(f"bad reply line at step {steps}: {type(e).__name__}")
        if not isinstance(action, str):
            fail(f"'action' must be a string at step {steps}")
        print(f"[actiview] step {steps} reply: {action.strip()[:200]!r}", flush=True)
        try:
            req = gen.send(action.strip())
        except StopIteration as stop:
            rec = C.finish(inst, d, stop.value, steps)
            break
    print(f"[actiview] Answer: {rec['prediction']!r} gold={rec['gold']} correct={rec['correct']}", flush=True)
    emit(rec)
    return 0


if __name__ == "__main__":
    sys.exit(main())
