                                                                                                                         
                                                                                                                    
                                                                                                               
                                              

                                                                             
   
import json
import sys
from pathlib import Path

run_dir = Path(sys.argv[1])
run = json.loads((run_dir / "run.json").read_text())
report = json.loads((run_dir / "reeval_tle.json").read_text())

for ep in run["episodes"]:
    official = (ep.get("evaluation") or {}).get("official") or {}
    pid = official.get("problemId")
    if pid not in report["problems"]:
        continue
    steps = [r for r in map(json.loads, (run_dir / "episodes" / ep["id"] / "record.jsonl").read_text().splitlines())
             if r.get("kind") == "step"]
    if any(r["observation"]["info"].get("judgeResult") == "TIME_LIMIT_EXCEEDED" for r in steps):
        print(pid, "has a public TLE: rule (1) does not apply, checkpoints kept")
        continue
    for name, r in report["problems"][pid]["checkpoints"].items():
        new = {k: r["reeval"][k] for k in ("overall_absolute_score", "overall_judge_result", "rank", "performance",
                                            "judge_retries", "tle_cases", "cases")}
        official["checkpoints"][name] = {"submission_round": r["submission_round"], **new,
                                         "reevaluated": "rule (1)", "inRun": r["in_run"]}
        print(pid, name, "perf", r["in_run"]["performance"], "->", new["performance"], new["overall_judge_result"])
    official["final"] = official["checkpoints"]["self_refine_16"]
    official["x1"] = official["checkpoints"]["x1_first_submission"]
    official["ruleOneReevaluatedAt"] = report["problems"][pid]["at"]
    ep["score"] = official["final"]["performance"]
    ep["outcome"] = "success" if official["final"]["overall_judge_result"] == "ACCEPTED" else "failure"

                                   
done = [e for e in run["episodes"] if e.get("status") == "completed"]
perf = [e["score"] for e in done if isinstance(e.get("score"), (int, float))]
run["summary"] = {"episodes": len(run["episodes"]), "completed": len(done),
                  "successes": sum(e.get("outcome") == "success" for e in run["episodes"]),
                  "averagePerformanceX16": round(sum(perf) / len(perf), 1) if perf else None,
                  "costUSD": round(sum(e.get("costUSD") or 0 for e in run["episodes"]), 4)}
(run_dir / "run.json").write_text(json.dumps(run, indent=1))
print("summary", json.dumps(run["summary"]))
