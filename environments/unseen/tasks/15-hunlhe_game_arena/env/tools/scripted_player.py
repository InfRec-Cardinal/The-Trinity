#!/usr/bin/env python3
                                                             

                                                                             
                                                                       
                                                              
                                                        
                                                       
   
import json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ep, out = sys.argv[1], pathlib.Path(sys.argv[2])
policy = sys.argv[3] if len(sys.argv) > 3 else "call"
proc = subprocess.Popen([str(ROOT / "env/bin/python"), str(ROOT / "poker_bridge.py"), ep],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, cwd=ROOT)
n_req = 0
with open(out, "w") as f:
  for line in proc.stdout:
    rec = json.loads(line)
    f.write(line)
    if rec["kind"] == "player_request":
      n_req += 1
      can_check = not any(l.endswith("move=Fold") for l in rec["legal"])
      legal_txt = "Final Answer: check" if can_check else "Final Answer: call"
      if policy == "garbage" or (policy == "garbage-once" and not rec["retry"]):
        txt = "I am not sure what to do here."
      else:
        txt = "Reasoning...\n" + legal_txt
      proc.stdin.write(json.dumps({"action": txt}) + "\n"); proc.stdin.flush()
    elif rec["kind"] == "hand_result":
      print(f"hand {rec['hand']}: player {rec['playerChips']:+} chips, button={rec['playerIsButton']}, "
            f"illegal={rec['illegal']}", file=sys.stderr)
    elif rec["kind"] in ("terminal", "error"):
      short = {k: v for k, v in rec.items() if k != "perHand"}
      print(json.dumps(short), file=sys.stderr)
proc.stdin.close()
rc = proc.wait()
print(f"bridge exit={rc} player_requests={n_req}", file=sys.stderr)
sys.exit(rc)
