#!/usr/bin/env python3
                                                                              
                                                                        
                                                                              
           
                                                                              
                                                                            
                                                                    
                                                                             
                                                                                 
                                                               
 
        
                                                                         
                                                                                      
                                                                              
                                                                              
import argparse
import csv
import json
import re
import sys
from pathlib import Path


                                                                              
def extract_agent(ipynb_path, out_dir):
    nb = json.load(open(ipynb_path))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    agent_src = None
    for cell in nb["cells"]:
        src = "".join(cell.get("source", []))
        if "%%writefile" in src and "my_agent.py" in src:
                                              
            lines = src.split("\n")
            body = "\n".join(l for l in lines if not l.strip().startswith("%%writefile"))
            agent_src = body
            break
    if agent_src is None:
        print("ERROR: no %%writefile my_agent.py cell found", file=sys.stderr)
        return 1
    dest = out / "submitted_my_agent.py"
    dest.write_text(agent_src)
                                                         
    max_actions = re.findall(r"MAX_ACTIONS\s*=\s*([^\n]+)", agent_src)
    has_fb = "class FallbackExplorer" in agent_src
    print(f"extracted -> {dest}")
    print(f"chars: {len(agent_src)}")
    print(f"MAX_ACTIONS occurrences: {max_actions}")
    print(f"contains FallbackExplorer: {has_fb}")
    print(">> Copy submitted_my_agent.py next to fallbackonly_agent.py so the")
    print(">> diagnostic imports the EXACT scored artifact.")
    return 0


                                                                               
def parse_recording(rec_path, game, out_csv):
    rows = []
    last_level = None
    level_start_action = 0
    action_idx = 0
    final_state = None
    for line in Path(rec_path).open():
        try:
            data = json.loads(line).get("data", {})
        except Exception:
            continue
        lvl = data.get("levels_completed")
        st = data.get("state")
        if st is not None:
            final_state = st
        if lvl is not None and lvl != last_level:
            if last_level is not None:
                rows.append({
                    "game": game, "level": last_level,
                    "actions_in_level": action_idx - level_start_action,
                    "state_at_end": final_state,
                })
            last_level = lvl
            level_start_action = action_idx
        action_idx += 1
                 
    if last_level is not None:
        rows.append({
            "game": game, "level": last_level,
            "actions_in_level": action_idx - level_start_action,
            "state_at_end": final_state,
        })
    _write_csv(rows, out_csv, ["game", "level", "actions_in_level", "state_at_end"])
    levels_cleared = max((r["level"] for r in rows), default=0)
    print(f"{game}: levels_cleared={levels_cleared} total_actions={action_idx} "
          f"final_state={final_state} rows={len(rows)} -> {out_csv}")
    return 0


                                                                               
_DIAG_STEP = re.compile(
    r"\[FALLBACK_DIAG\] step=(\d+) lvl=(\d+) state=(\S+) action=(\S+) xy=(\S+) "
    r"sig=(\S+) repeat=(\d+) untried=(\S+) diff=(\S+) noop=(\S+)"
)
_DIAG_TERM = re.compile(
    r"\[FALLBACK_DIAG\] TERMINAL reason=(\S+) level=(\d+) max_level=(\d+) "
    r"total_actions=(\d+) noops=(\d+) game_overs=(\d+) distinct_sigs=(\d+)"
)


def parse_log(log_path, game, out_csv):
    steps = []
    term = None
    for line in Path(log_path).open(errors="ignore"):
        m = _DIAG_STEP.search(line)
        if m:
            steps.append({
                "game": game, "step": int(m.group(1)), "level": int(m.group(2)),
                "state": m.group(3), "action": m.group(4), "xy": m.group(5),
                "sig": m.group(6), "repeat": int(m.group(7)),
                "untried": m.group(8), "diff": m.group(9), "noop": m.group(10),
            })
            continue
        mt = _DIAG_TERM.search(line)
        if mt:
            term = {
                "reason": mt.group(1), "level": int(mt.group(2)),
                "max_level": int(mt.group(3)), "total_actions": int(mt.group(4)),
                "noops": int(mt.group(5)), "game_overs": int(mt.group(6)),
                "distinct_sigs": int(mt.group(7)),
            }
    _write_csv(steps, out_csv,
               ["game", "step", "level", "state", "action", "xy", "sig",
                "repeat", "untried", "diff", "noop"])
                               
    if steps:
        n = len(steps)
        noop_rate = sum(1 for s in steps if s["noop"] == "True") / n
        repeats = sum(1 for s in steps if s["repeat"] and int(s["repeat"]) > 3)
        distinct = len({s["sig"] for s in steps})
        print(f"{game}: steps={n} distinct_sigs={distinct} "
              f"noop_rate={noop_rate:.2f} high_repeat_steps={repeats}")
        if term:
            print(f"  TERMINAL: {term}")
                                 
        if distinct < max(3, n * 0.1):
            print("  HINT: low signature diversity -> possible STATE ALIASING "
                  "(mode d) or stuck exploring (graph not progressing).")
        if noop_rate > 0.3:
            print("  HINT: high no-op rate -> actions not changing state "
                  "(candidate generation / wrong action set).")
        if term and term["game_overs"] > 0 and term["max_level"] == 0:
            print("  HINT: GAME_OVER with no level cleared -> dangerous-action "
                  "loops (mode c) or never finds advancing action (mode a).")
    else:
        print(f"{game}: no [FALLBACK_DIAG] step lines found in {log_path}")
    return 0


def _write_csv(rows, out_csv, fields):
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract-agent"); e.add_argument("ipynb"); e.add_argument("out_dir")
    pr = sub.add_parser("parse-recording")
    pr.add_argument("recording"); pr.add_argument("--game", required=True)
    pr.add_argument("--out", required=True)
    pl = sub.add_parser("parse-log")
    pl.add_argument("log"); pl.add_argument("--game", required=True)
    pl.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "extract-agent":
        return extract_agent(a.ipynb, a.out_dir)
    if a.cmd == "parse-recording":
        return parse_recording(a.recording, a.game, a.out)
    if a.cmd == "parse-log":
        return parse_log(a.log, a.game, a.out)


if __name__ == "__main__":
    sys.exit(main())
