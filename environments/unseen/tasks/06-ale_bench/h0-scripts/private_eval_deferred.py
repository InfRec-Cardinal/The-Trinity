                                                                                                     

                                                                                                                
                                                                                                                 
                                                                                                          
                                                                                                   
                                                                                                
                                                                                                                 

                                                                                                                            
                                                                     
                                                                                                                      
                                                                                                                          
                                                                                                                
                                                                                  
   
import datetime as dt
import fcntl
import json
import os
import sys
from pathlib import Path

import ale_bench

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bridge import Bridge              

parts = Path(sys.argv[1])
skip = set(filter(None, os.environ.get("ALE_SKIP_PROBLEMS", "").split(",")))
wait = os.environ.get("ALE_LOCK_WAIT") == "1"
only = [c for c in os.environ.get("ALE_CHECKPOINTS", "").split(",") if c]
lock_dir = Path("/tmp/ale-private-eval-locks")
lock_dir.mkdir(exist_ok=True)
for part in sorted(p for p in parts.iterdir() if (p / "run.json").is_file() and p.name not in skip):
    lock = open(lock_dir / f"{part.name}.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | (0 if wait else fcntl.LOCK_NB))
    except BlockingIOError:
        lock.close()
        continue
    run = json.loads((part / "run.json").read_text())
    for ep in run["episodes"]:
        official = (ep.get("evaluation") or {}).get("official") or {}
        if ep.get("status") != "completed" or not official.get("pending"):
            continue
        pid, selections = official["problemId"], official["selections"]
        subs = part / "episodes" / ep["id"] / "submissions"
        bridge = Bridge()
        bridge.session = ale_bench.start(problem_id=pid, lite_version=False, num_workers=6,
                                         run_visualization_server=False, session_duration=dt.timedelta(hours=240))
        evaluated: dict[str, dict] = {}
        checkpoints = {}
        for name, rnd in selections.items():
            if only and name not in only:
                continue
            code = (subs / f"round-{rnd:02d}.cpp").read_text()
            key = code.strip()
            if key not in evaluated:
                from ale_bench_eval.evaluate import get_ce_code
                (private_result, rank, perf), retries = bridge._private(code if key else get_ce_code("cpp20"))
                evaluated[key] = {"overall_absolute_score": private_result.overall_absolute_score,
                                  "overall_relative_score": private_result.overall_relative_score,
                                  "overall_judge_result": private_result.overall_judge_result.value,
                                  "rank": rank, "performance": perf, "judge_retries": retries}
            checkpoints[name] = {"submission_round": rnd, **evaluated[key]}
            print(pid, name, "round", rnd, "perf", checkpoints[name]["performance"], checkpoints[name]["overall_judge_result"], flush=True)
        bridge.close()
        final = checkpoints["self_refine_16"]
        ep["outcome"] = "success" if final["overall_judge_result"] == "ACCEPTED" else "failure"
        ep["score"] = final["performance"]
        ep["evaluation"] = {"official": {"problemId": pid, "metric": "performance (rank-based)", "final": final,
                                         "x1": checkpoints["x1_first_submission"], "checkpoints": checkpoints,
                                         "publicScores": official["publicScores"], "privateEvaluation": "deferred",
                                         "privateEvaluatedAt": dt.datetime.now(dt.timezone.utc).isoformat()}}
        if only:
            ep["evaluation"]["official"]["checkpointsEvaluated"] = only
        (part / "run.json").write_text(json.dumps(run, indent=1))
        print(pid, "x16 performance", final["performance"], flush=True)
    lock.close()
