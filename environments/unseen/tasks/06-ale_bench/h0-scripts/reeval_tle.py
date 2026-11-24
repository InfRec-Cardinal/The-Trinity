                                                                                                             

                                                                                                          
                                                                                                              
                                                                                                              
                                                                                                             

                                                                                                                                   
                                                                                                     
                                                                                                                     
                                                                              
   
import datetime as dt
import json
import os
import sys
from pathlib import Path

import ale_bench

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bridge import CODE_LANGUAGE, JUDGE_VERSION, Bridge, judge_slot              

run_dir = Path(sys.argv[1])
run = json.loads((run_dir / "run.json").read_text())
out_path = run_dir / "reeval_tle.json"
report = json.loads(out_path.read_text()) if out_path.exists() else {"rule": 'Re-evaluate TLE solutions with the official judge', "problems": {}}
only = [c for c in os.environ.get("ALE_CHECKPOINTS", "").split(",") if c]
if only:
    report["checkpoints"] = only

for ep in run["episodes"]:
    official = (ep.get("evaluation") or {}).get("official")
    if ep.get("status") != "completed" or not official:
        continue
    pid = official["problemId"]
    tle = {k: v for k, v in official["checkpoints"].items()
           if v["overall_judge_result"] == "TIME_LIMIT_EXCEEDED" and (not only or k in only)}
    if not tle or pid in report["problems"]:
        continue
    steps = [r for r in map(json.loads, (run_dir / "episodes" / ep["id"] / "record.jsonl").read_text().splitlines())
             if r.get("kind") == "step"]
    if any(r["observation"]["info"].get("judgeResult") == "TIME_LIMIT_EXCEEDED" for r in steps):
        print(pid, "has a public TLE: rule (1) does not apply", flush=True)
        continue
    subs = run_dir / "episodes" / ep["id"] / "submissions"
    bridge = Bridge()
    bridge.session = ale_bench.start(problem_id=pid, lite_version=False, num_workers=6,
                                     run_visualization_server=False, session_duration=dt.timedelta(hours=240))
    by_round: dict[int, dict] = {}
    results = {}
    for name, before in tle.items():
        rnd = before["submission_round"]
        if rnd not in by_round:
            code = (subs / f"round-{rnd:02d}.cpp").read_text()
            (private_result, rank, perf), retries = bridge._private(code)
            by_round[rnd] = {"overall_absolute_score": private_result.overall_absolute_score,
                             "overall_judge_result": private_result.overall_judge_result.value,
                             "rank": rank, "performance": perf, "judge_retries": retries,
                             "tle_cases": sum(c.judge_result.value == "TIME_LIMIT_EXCEEDED" for c in private_result.case_results),
                             "cases": len(private_result.case_results)}
        results[name] = {"submission_round": rnd, "in_run": before, "reeval": by_round[rnd]}
        print(pid, name, "round", rnd, "in-run perf", before["performance"], "-> re-eval perf", by_round[rnd]["performance"],
              by_round[rnd]["overall_judge_result"], f"TLE {by_round[rnd]['tle_cases']}/{by_round[rnd]['cases']}", flush=True)
    bridge.close()
    report["problems"][pid] = {"episode": ep["id"], "checkpoints": results, "at": dt.datetime.now(dt.timezone.utc).isoformat()}
    out_path.write_text(json.dumps(report, indent=1))
print("re-evaluated problems:", len(report["problems"]))
