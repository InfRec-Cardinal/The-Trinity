from __future__ import annotations

import argparse
import json
import sys
import os
import subprocess
from pathlib import Path

from . import analyst, digests, induction, records as rec, trees, verifier
from .bridge import export_training
from .storage import write_json, write_text

PROMPTS = Path(__file__).resolve().parent / "prompts"


def prompt(name: str) -> str:
    return (PROMPTS / f"{name}.txt").read_text().strip()


def load_json(p: Path):
    return json.loads(Path(p).read_text())


def tasks_of(handoff: dict, cohort: str) -> dict[str, dict]:
    want = "train" if cohort == "train" else "unseen"
    return {rec.safe_id(t["taskId"]): t for t in handoff["tasks"] if t.get("set") == want}


def failure_rule(task: dict) -> str:
    return task.get("failureRule", "outcome")


def completed_training(a, ledger=None):
    directory = getattr(a, "training_run", None)
    if not directory:
        raise ValueError("Unseen processing requires --training-run from completed Harness training")
    checker = Path(__file__).resolve().parents[2] / "harness" / "src" / "protocol-state.mjs"
    command = [os.environ.get("TRINITY_NODE", "node"), str(checker), "verify-unseen" if ledger else "verify", str(Path(directory).resolve()), str(Path(a.out).resolve())]
    if ledger:
        command.append(str(ledger))
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode:
        raise ValueError(result.stderr.strip() or "Training completion verification failed")
    return json.loads(result.stdout)


def require_unseen(a):
    complete = completed_training(a)
    proof = load_json(Path(a.out) / "unseen-import.json")
    if proof["completionHash"] != complete["hash"]:
        raise ValueError("Unseen records belong to a different completed training run")
    for ledger in proof["ledgers"]:
        completed_training(a, ledger)


def cmd_import(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    handoff = load_json(a.handoff)
    sources = load_json(a.runs)
    unseen_ids = set(tasks_of(handoff, "unseen"))
    if getattr(a, "training_only", False):
        sources = {key: value for key, value in sources.items() if key not in unseen_ids}
    imports_unseen = bool(set(sources) & unseen_ids)
    if imports_unseen:
        complete = completed_training(a)
        if rec.content_digest(handoff) != complete["artifact"]["stage2"]["handoffDigest"]:
            raise ValueError("Unseen handoff differs from the frozen training split")
    existing = out / "handoff.json"
    if existing.exists() and load_json(existing) != handoff:
        raise ValueError("Cannot replace the existing task split")
    write_text(existing, json.dumps(handoff, ensure_ascii=False))
    for source in sources.values():
        source["path"] = str((Path(a.runs).resolve().parent / source["path"]).resolve())
        if "ledgerPath" in source:
            source["ledgerPath"] = str((Path(a.runs).resolve().parent / source["ledgerPath"]).resolve())
    if imports_unseen:
        ledgers = sorted({sources[key].get("ledgerPath", "") for key in sources if key in unseen_ids})
        for ledger in ledgers:
            completed_training(a, ledger)
        write_text(out / "unseen-import.json", json.dumps({"completionHash": complete["hash"], "ledgers": ledgers}))
    eps = rec.import_runs(sources)
    rec.write_records(eps, out)
    print(json.dumps({t: len(e) for t, e in eps.items()}, indent=1))


def cmd_digests(a):
    out = Path(a.out)
    limits = load_json(a.limits) if a.limits else None
    digests.write_digests(rec.read_records(out), out, {k: tuple(v) for k, v in (limits or {}).items()})
    print("digests written to", out / "digests")


def catalogue_or_none(out: Path):
    p = out / "capabilities" / "capabilities.json"
    return load_json(p) if p.exists() else None


def cmd_analyse(a):
    if a.cohort == "unseen":
        require_unseen(a)
    out = Path(a.out)
    handoff = load_json(out / "handoff.json")
    tasks = tasks_of(handoff, a.cohort)
    catalogue = catalogue_or_none(out) if a.cohort == "unseen" or a.fixed else None
    mode = "fixed" if catalogue is not None else "open"
    if a.cohort == "unseen" and catalogue is None:
        sys.exit("unseen tasks need the fixed catalogue: run induce and assign on the training tasks first")
    selected = [t for t in a.task] if a.task else sorted(tasks)
    for task_id in selected:
        stats_path = out / "stats" / f"{task_id}.json"
        if not stats_path.exists():
            print(f"skip {task_id}: no H0 trajectories imported")
            continue
        record_path = out / a.cohort / "records" / f"{task_id}.json"
        if record_path.exists() and not a.force:
            continue
        analyst.analyse_task(task=tasks[task_id], stats=load_json(stats_path), digest_path=out / "digests" / f"{task_id}.txt", mode=mode, catalogue=catalogue,
                             out_dir=out / a.cohort, checkpoint_dir=out / "checkpoints", prompt=prompt("analyst-open" if mode == "open" else "analyst-fixed"),
                             failure_rule=failure_rule(tasks[task_id]), cohort=a.cohort)
        print("analysed", task_id)


MAX_REVISIONS = 2


def review_cohort(out: Path, cohort: str, tasks: dict, catalogue, revise: bool, max_revisions: int = MAX_REVISIONS, log=print) -> dict:
    verdicts = {}
    for p in sorted((out / cohort / "records").glob("*.json")):
        record = load_json(p)
        task_id = record["taskId"]
        while True:
            verdict = record.get("review") if record.get("reviewOutcome") else None
            if verdict is None:
                analysis = (out / cohort / "analyses" / f"{task_id}.txt").read_text()
                verdict = verifier.review_task(record=record, analysis=analysis, stats=load_json(out / "stats" / f"{task_id}.json"), digest_path=out / "digests" / f"{task_id}.txt",
                                               catalogue=catalogue if record.get("mode") == "fixed" else None, checkpoint_dir=out / "checkpoints", prompt=prompt("reviewer"), log=log)
                record["review"] = verdict
            record["reviewOutcome"] = "accepted" if verdict["verdict"] == "accept" else "pending" if revise and record.get("revision", 0) < max_revisions else "unresolved"
            write_json(p, record)
            if record["reviewOutcome"] != "pending":
                break
            revision = record.get("revision", 0) + 1
            log(f"{task_id}: the review asked for a revision ({len(verdict['objections'])} objection(s)); running analyst revision {revision}")
            previous = [*record.get("previousReviews", []), {"revision": record.get("revision", 0), **verdict}]
            record = analyst.analyse_task(task=tasks[task_id], stats=load_json(out / "stats" / f"{task_id}.json"), digest_path=out / "digests" / f"{task_id}.txt", mode=record["mode"],
                                          catalogue=catalogue if record["mode"] == "fixed" else None, out_dir=out / cohort, checkpoint_dir=out / "checkpoints",
                                          prompt=prompt("analyst-open" if record["mode"] == "open" else "analyst-fixed"), failure_rule=record.get("failureRule", "outcome"), cohort=cohort,
                                          revision=revision, objections=verdict["objections"], previous_reviews=previous, log=log)
        verdicts[task_id] = {**record["review"], "outcome": record["reviewOutcome"], "revision": record.get("revision", 0)}
    write_json(out / cohort / "reviews.json", verdicts)
    return verdicts


def cmd_review(a):
    if a.cohort == "unseen":
        require_unseen(a)
    out = Path(a.out)
    verdicts = review_cohort(out, a.cohort, tasks_of(load_json(out / "handoff.json"), a.cohort), catalogue_or_none(out), a.revise)
    print(json.dumps({t: {"verdict": v["verdict"], "outcome": v["outcome"], "revision": v["revision"]} for t, v in verdicts.items()}, indent=1))


def cmd_induce(a):
    out = Path(a.out)
    handoff = load_json(out / "handoff.json")
    tasks = tasks_of(handoff, "train")
    recs = {p.stem: load_json(p) for p in sorted((out / "train" / "records").glob("*.json"))}
    unreviewed = [t for t, r in recs.items() if r.get("review", {}).get("verdict") != "accept"]
    if unreviewed and not a.allow_unreviewed:
        sys.exit(f"induction needs accepted reviews for every training analysis; pending or unresolved: {unreviewed}")
    prompts = {k: prompt(k) for k in ("proposer", "judge", "catalogue_reviewer", "reviser")}
    catalogue = induction.induce(records=recs, tasks=tasks, out_dir=out, checkpoint_dir=out / "checkpoints", prompts=prompts, proposers=a.proposers, reviewers=a.reviewers, rounds=a.rounds, work_dir=out)
    assigned = induction.apply_assignments(recs, catalogue)
    for task_id, r in assigned.items():
        write_json(out / "train" / "records" / f"{task_id}.json", r)
    induction.write_catalogue(catalogue, out, assigned, tasks)
    print("catalogue:", len(catalogue["capabilities"]), "capabilities,", len(catalogue["defectTypes"]), "defect types; order", catalogue["order"])


def place_cohort(out: Path, cohort: str) -> bool:
    catalogue = load_json(out / "capabilities" / "capabilities.json")
    order = catalogue["order"]
    results, placed = {}, []
    for p in sorted((out / cohort / "records").glob("*.json")):
        record = verifier.derive_placement(load_json(p), catalogue, order)
        write_json(p, record)
        analysis = (out / cohort / "analyses" / f"{record['taskId']}.txt").read_text()
        results[record["taskId"]] = verifier.gate(record, load_json(out / "stats" / f"{record['taskId']}.json"), analysis, catalogue, order, work_dir=out)
        placed.append(record)
    ok = verifier.write_gate_report(results, out / cohort / "gate-report.txt")
    write_json(out / cohort / "task-capability-gaps.json", placed)
    print((out / cohort / "gate-report.txt").read_text())
    return ok


def cmd_assign(a):
    if not place_cohort(Path(a.out), "train"):
        sys.exit("gate failed for the training records")


def cmd_unseen(a):
    a.cohort, a.fixed, a.force, a.task = "unseen", True, False, []
    cmd_analyse(a)
    a.revise = True
    cmd_review(a)
    if not place_cohort(Path(a.out), "unseen"):
        sys.exit("gate failed for the unseen records")


def cmd_trees(a):
    out = Path(a.out)
    catalogue = load_json(out / "capabilities" / "capabilities.json")
    recs = load_json(out / "train" / "task-capability-gaps.json")
    unseen = out / "unseen" / "task-capability-gaps.json"
    if unseen.exists():
        require_unseen(a)
    unseen_recs = load_json(unseen) if unseen.exists() else []
    handoff = load_json(out / "handoff.json")
    induction.write_defect_table(catalogue, out / "capabilities" / "defect-types.csv", {r["taskId"]: r for r in recs}, tasks_of(handoff, "train") | tasks_of(handoff, "unseen"), {r["taskId"]: r for r in unseen_recs})
    trees.write_trees(recs + unseen_recs, catalogue, out / "trees")
    print("trees written to", out / "trees")


def cmd_all(a):
    a.training_only = True
    cmd_import(a)
    cmd_digests(a)
    a.cohort, a.fixed, a.force, a.task = "train", False, False, []
    cmd_analyse(a)
    a.revise = True
    cmd_review(a)
    cmd_induce(a)
    cmd_assign(a)
    cmd_trees(a)


def main(argv=None):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--out", required=True)
    common.add_argument("--training-run")
    s = sub.add_parser("import-runs", parents=[common]); s.add_argument("--handoff", required=True); s.add_argument("--runs", required=True); s.set_defaults(fn=cmd_import)
    s = sub.add_parser("digests", parents=[common]); s.add_argument("--limits"); s.set_defaults(fn=cmd_digests)
    s = sub.add_parser("analyse", parents=[common]); s.add_argument("--cohort", default="train", choices=["train", "unseen"]); s.add_argument("--task", nargs="*"); s.add_argument("--fixed", action="store_true"); s.add_argument("--force", action="store_true"); s.set_defaults(fn=cmd_analyse)
    s = sub.add_parser("review", parents=[common]); s.add_argument("--cohort", default="train", choices=["train", "unseen"]); s.add_argument("--revise", action="store_true"); s.set_defaults(fn=cmd_review)
    s = sub.add_parser("induce", parents=[common]); s.add_argument("--proposers", type=int, default=3); s.add_argument("--reviewers", type=int, default=4); s.add_argument("--rounds", type=int, default=3); s.add_argument("--allow-unreviewed", action="store_true"); s.set_defaults(fn=cmd_induce)
    s = sub.add_parser("assign", parents=[common]); s.set_defaults(fn=cmd_assign)
    s = sub.add_parser("unseen", parents=[common]); s.set_defaults(fn=cmd_unseen)
    s = sub.add_parser("trees", parents=[common]); s.set_defaults(fn=cmd_trees)
    s = sub.add_parser("export-training", parents=[common]); s.set_defaults(fn=lambda a: print(json.dumps(export_training(a.out))))
    s = sub.add_parser("all", parents=[common]); s.add_argument("--handoff", required=True); s.add_argument("--runs", required=True); s.add_argument("--limits"); s.add_argument("--proposers", type=int, default=3); s.add_argument("--reviewers", type=int, default=4); s.add_argument("--rounds", type=int, default=3); s.add_argument("--allow-unreviewed", action="store_true"); s.set_defaults(fn=cmd_all)
    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
