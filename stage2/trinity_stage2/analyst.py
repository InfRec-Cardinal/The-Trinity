from __future__ import annotations

import json
import re
from pathlib import Path

from .model import Tool, run_agent
from .media import step_evidence
from .evidence import append_check, check_log, input_digest, bind_checks, coverage_errors, YARDSTICK_FIELDS
from .storage import write_json, write_text

CONFIDENCE = ["higher", "lower"]
BANNED = re.compile(r"\b(opus|claude|haiku|sonnet|thinking budget|effort low|adaptive thinking|transport route|cohort v\d|RSI|curriculum|fine-tun\w*|harness design)\b", re.I)

CITATION = {"type": "object", "properties": {"episode": {"type": "string"}, "step": {"type": "integer"}, "field": {"type": "string", "enum": ["action", "observation", "terminal"]},
                                             "outcome": {"type": "string"}}, "required": ["episode", "step", "field", "outcome"], "additionalProperties": False}


YARDSTICK = {"type": "object", "properties": {k: {"type": "string", "minLength": 8} for k in ("goal", "observation", "feedback", "actions", "irreversible", "budget", "success", "failure", "competentDecision")},
             "required": ["goal", "observation", "feedback", "actions", "irreversible", "budget", "success", "failure", "competentDecision"], "additionalProperties": False,
             "description": "The rule yardstick derived from the task specification: what the Player sees, what each action does and costs, what is irreversible, the budget, the completion criteria, and what a competent decision must satisfy given the information at the time."}


def behaviour_schema(mode: str) -> dict:
    props = {"kind": {"type": "string", "enum": ["failure", "success"]},
             "criterion": {"type": "string", "minLength": 10, "description": "The rule or completion criterion of the yardstick that the cited steps violate (failure) or satisfy (success)."},
             "check": {"type": "string", "minLength": 10, "description": "Use run_check:<exact successful check name> or read_steps:<step-by-step rule reasoning>. Every referenced check/step must actually be executed/read through the host tools for these inputs."},
             "behaviour": {"type": "string", "minLength": 20, "description": "The decisive behaviour, stated generally enough to recur."},
             "instance": {"type": "string", "minLength": 10, "description": "What exactly happened in these episodes, with numbers."},
             "confidence": {"type": "string", "enum": CONFIDENCE},
             "citations": {"type": "array", "minItems": 1, "items": CITATION}}
    if mode == "open":
        props["defectLabel"] = {"type": "string", "minLength": 4, "description": "A short name for the observable failure pattern, in words a reader can test."}
        props["defectDefinition"] = {"type": "string", "minLength": 30, "description": "Pass/fail definition of the pattern, independent of this task's objects."}
        required = ["kind", "criterion", "check", "behaviour", "instance", "confidence", "citations", "defectLabel", "defectDefinition"]
    else:
        props["defectType"] = {"type": "string", "description": "A defect type id of the catalogue, or NEW:<proposed name>."}
        props["capability"] = {"type": "string", "description": "The catalogue capability id of that defect type."}
        props["newDefinition"] = {"type": "string", "description": "Only for NEW: the proposed pass/fail definition."}
        required = ["kind", "criterion", "check", "behaviour", "instance", "confidence", "citations", "defectType", "capability"]
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


def submit_schema(mode: str) -> dict:
    return {"type": "object", "properties": {
        "ruleYardstick": YARDSTICK,
        "requirementCoverage": {"type": "array", "minItems": 9, "maxItems": 9, "items": {"type": "object", "properties": {
            "field": {"type": "string", "enum": YARDSTICK_FIELDS}, "requirement": {"type": "string", "minLength": 10},
            "behaviourIndices": {"type": "array", "items": {"type": "integer", "minimum": 0}},
            "notApplicableReason": {"type": ["string", "null"]}},
            "required": ["field", "requirement", "behaviourIndices", "notApplicableReason"], "additionalProperties": False}},
        "analysis": {"type": "string", "minLength": 400, "description": "The Markdown analysis (sections: Task and observation; Summary of findings; Decisive behaviours and where they appear; Attribution; What successful episodes did; Evidence limits; Episode table; Failure coverage)."},
        "behaviours": {"type": "array", "items": behaviour_schema(mode)},
        "nonCapabilityCauses": {"type": "array", "items": {"type": "object", "properties": {"episode": {"type": "string"}, "cause": {"type": "string", "minLength": 10}}, "required": ["episode", "cause"], "additionalProperties": False},
                                "description": "Failing episodes whose failure is mainly a non-capability cause (evidence not delivered, protocol rejection, interface or budget limit, service error, scorer confound)."},
        "unresolved": {"type": "array", "items": {"type": "string"}}},
        "required": ["ruleYardstick", "requirementCoverage", "analysis", "behaviours", "nonCapabilityCauses", "unresolved"], "additionalProperties": False}


def failing_episodes(stats: list[dict], failure_rule: str = "outcome") -> set[str]:
    if failure_rule == "score_below_one":
        return {s["episode"] for s in stats if isinstance(s.get("score"), (int, float)) and s["score"] < 1}
    return {s["episode"] for s in stats if s.get("outcome") == "failure"}


def binary_episodes(stats: list[dict], failure_rule: str = "outcome") -> set[str]:
    if failure_rule == "score_below_one":
        return {s["episode"] for s in stats if isinstance(s.get("score"), (int, float))}
    return {s["episode"] for s in stats if s.get("outcome") in ("success", "failure")}


def check_submission(args: dict, stats: list[dict], digest: str, catalogue: dict | None, failure_rule: str, check_records=None, expected_input=None) -> list[str]:
    problems = coverage_errors(args)
    problems.extend(bind_checks(args["behaviours"], check_records or [], expected_input)[1])
    steps = {s["episode"]: s.get("steps") for s in stats}
    fails = failing_episodes(stats, failure_rule)
    text = args["analysis"] + json.dumps(args["behaviours"], ensure_ascii=False)
    for hit in sorted({m.group(0) for m in BANNED.finditer(text)}):
        problems.append(f"remove condition labels and downstream guidance wording: '{hit}' (treat every trajectory as H0; describe behaviour only)")
    cited = set()
    proposed_caps: dict[str, set] = {}
    for i, b in enumerate(args["behaviours"]):
        if not b.get("citations"):
            problems.append(f"behaviours[{i}] cites no trajectory step; cite at least one decisive step")
        for c in b.get("citations", []):
            if c["episode"] not in steps:
                problems.append(f"behaviours[{i}] cites unknown episode {c['episode']} (use the digest headers exactly)")
                continue
            n = steps[c["episode"]]
            if n is not None and not 0 <= c["step"] <= n:
                problems.append(f"behaviours[{i}] cites step {c['step']} of {c['episode']}, which has {n} steps")
            cited.add(c["episode"])
            if b["kind"] == "failure" and c["episode"] not in fails:
                problems.append(f"behaviours[{i}] is a failure behaviour but cites {c['episode']}, which is not a failing episode (cite it as a success behaviour or drop it)")
        if catalogue is not None:
            dt = b.get("defectType", "")
            if dt.startswith("NEW") and dt not in catalogue["defectTypes"]:
                if not b.get("newDefinition"):
                    problems.append(f"behaviours[{i}] proposes {dt} without newDefinition")
                if b.get("capability") not in catalogue["capabilities"]:
                    problems.append(f"behaviours[{i}] proposes {dt} under capability {b.get('capability')!r}, which is not in the fixed catalogue")
                proposed_caps.setdefault(dt, set()).add(b.get("capability"))
                if len(proposed_caps[dt]) > 1:
                    problems.append(f"behaviours[{i}]: {dt} is proposed under more than one capability ({', '.join(sorted(map(str, proposed_caps[dt])))}); a defect type belongs to exactly one capability, so use distinct names")
            elif dt not in catalogue["defectTypes"]:
                problems.append(f"behaviours[{i}] names unknown defect type {dt}")
            elif catalogue["defectTypes"][dt]["capability"] != b.get("capability"):
                problems.append(f"behaviours[{i}]: {dt} belongs to capability {catalogue['defectTypes'][dt]['capability']}, not {b.get('capability')}")
    attributed = {c["episode"] for c in args["nonCapabilityCauses"]}
    uncovered = sorted(f for f in fails if f not in cited and f not in attributed and f not in args["analysis"])
    if uncovered:
        problems.append(f"{len(uncovered)} failing episode(s) are neither cited by a behaviour, attributed to a non-capability cause, nor named in the analysis: {uncovered[:6]}")
    for episode in attributed - set(steps):
        problems.append(f"nonCapabilityCauses names unknown episode {episode}")
    return problems


def digest_tools(work_dir: Path, task_ids: list[str] | None = None) -> list[Tool]:
    cache: dict[str, tuple[list[str], list[str]]] = {}

    def texts(task_id):
        if task_ids and task_id not in task_ids:
            raise ValueError(f"unknown task {task_id}; available: {', '.join(task_ids)}")
        if task_id not in cache:
            p = work_dir / "digests" / f"{task_id}.txt"
            if not p.exists():
                raise ValueError(f"unknown task {task_id}")
            full = p.with_suffix(".full.txt")
            cache[task_id] = (p.read_text().splitlines(), (full.read_text() if full.exists() else p.read_text()).splitlines())
        return cache[task_id]

    def read_digest(args):
        lines, _ = texts(args["task"])
        offset, limit = int(args.get("offset", 0)), min(int(args.get("limit", 200)), 400)
        if offset < 0 or offset > len(lines):
            raise ValueError(f"offset must be within 0..{len(lines)}")
        return {"task": args["task"], "offset": offset, "lines": lines[offset:offset + limit], "totalLines": len(lines), "nextOffset": offset + limit if offset + limit < len(lines) else None}

    def grep_digest(args):
        lines, _ = texts(args["task"])
        pattern = re.compile(args["pattern"], re.I)
        hits = [(i, l) for i, l in enumerate(lines) if pattern.search(l)]
        return {"task": args["task"], "matches": [{"line": i, "text": l[:600]} for i, l in hits[:80]], "total": len(hits)}

    def read_step(args):
        _, src = texts(args["task"])
        episode, step = args["episode"], int(args["step"])
        header = re.compile(rf"^## {re.escape(episode)} ")
        start = next((i for i, l in enumerate(src) if header.match(l)), None)
        if start is None:
            raise ValueError(f"unknown episode {episode}")
        for l in src[start:]:
            if l.startswith(f"s{step} "):
                return step_evidence(work_dir, args["task"], episode, step)
            if l.startswith("## ") and not header.match(l):
                break
        raise ValueError(f"episode {episode} has no step {step}")

    task_prop = {"task": {"type": "string", "description": "task id"}}
    return [Tool("read_digest", "Read a task's digest, `limit` lines from `offset` (one line per step; headers give episode ids).", {"type": "object", "properties": {**task_prop, "offset": {"type": "integer"}, "limit": {"type": "integer"}}, "required": ["task", "offset"], "additionalProperties": False}, read_digest),
            Tool("grep_digest", "Search a task's digest with a regular expression; returns matching line numbers and text.", {"type": "object", "properties": {**task_prop, "pattern": {"type": "string"}}, "required": ["task", "pattern"], "additionalProperties": False}, grep_digest),
            Tool("read_step", "Read the full action, host receipt and actual images before and after one step. Image references alone are not visual evidence.", {"type": "object", "properties": {**task_prop, "episode": {"type": "string"}, "step": {"type": "integer"}}, "required": ["task", "episode", "step"], "additionalProperties": False}, read_step)]


def check_tool(work_dir: Path, log_path: Path, timeout: int = 120, task_id: str | None = None) -> Tool:
    import subprocess
    import sys

    def run_check(args):
        code = args["code"]
        before = input_digest(work_dir, task_id) if task_id else None
        proc = subprocess.run([sys.executable, "-I", "-c", code], cwd=str(work_dir), capture_output=True, text=True, timeout=timeout, env={"PATH": "", "WORK_DIR": str(work_dir)})
        out = {"name": args["name"], "stdout": proc.stdout[-20000:], "stderr": proc.stderr[-4000:], "returncode": proc.returncode}
        if task_id and input_digest(work_dir, task_id) != before:
            raise ValueError("A rule check modified its frozen evidence inputs")
        return append_check(log_path, {"kind": "execution", "code": code, "inputDigest": before, **out})

    return Tool("run_check", "Run a deterministic rule-based check: Python code (standard library only) that reads the files under the work directory (digests/<task>.txt, stats/<task>.json, records-canonical/<task>.json; the directory is the current directory and WORK_DIR) and prints its result. Use it for candidate-set replays, per-step references, distance-to-goal and budget arithmetic. Name each check; cite its name in the behaviour's `check` field.",
                {"type": "object", "properties": {"name": {"type": "string", "minLength": 3}, "code": {"type": "string", "minLength": 10}}, "required": ["name", "code"], "additionalProperties": False}, run_check)


def analyse_task(*, task: dict, stats: list[dict], digest_path: Path, mode: str, catalogue: dict | None, out_dir: Path, checkpoint_dir: Path,
                 prompt: str, failure_rule: str = "outcome", cohort: str = "train", max_turns: int = 60, work_dir: Path | None = None,
                 revision: int = 0, objections: list[dict] | None = None, previous_reviews: list[dict] | None = None, log=print) -> dict:
    task_id = task["taskId"]
    digest = digest_path.read_text()
    lines = digest.splitlines()
    work_dir = work_dir or digest_path.parent.parent

    check_path = out_dir / "checks" / f"{task_id}.jsonl"
    inspected = set()
    readers = digest_tools(work_dir, [task_id])
    reader = next(t for t in readers if t.name == "read_step")
    original_reader = reader.handler
    def read_visual(args):
        value = original_reader(args)
        inspected.add((args["episode"], args["step"]))
        append_check(check_path, {"kind": "reading", "episode": args["episode"], "step": args["step"], "inputDigest": input_digest(work_dir, task_id)})
        return value
    reader.handler = read_visual

    def submit(args):
        for behaviour in args["behaviours"]:
            for citation in behaviour["citations"]:
                evidence = step_evidence(work_dir, task_id, citation["episode"], citation["step"])
                if evidence["attach"] and (citation["episode"], citation["step"]) not in inspected:
                    raise ValueError("Inspect every visual citation with read_step before submitting the analysis")
        problems = check_submission(args, stats, digest, catalogue, failure_rule, check_log(check_path), input_digest(work_dir, task_id))
        if problems:
            raise ValueError("; ".join(problems[:12]))
        args["evidenceChecks"] = bind_checks(args["behaviours"], check_log(check_path), input_digest(work_dir, task_id))[0]
        return {"finish": args}

    tools = [*readers, check_tool(work_dir, check_path, task_id=task_id),
             Tool("submit_analysis", "Submit the analysis and the structured record. The host checks counts, citations, coverage and vocabulary; fix what it reports and resubmit.", submit_schema(mode), submit)]
    fails = failing_episodes(stats, failure_rule)
    kickoff = {"task": {k: task.get(k) for k in ("taskId", "name", "taskTreeOrigin", "summary", "assignment", "inputScope")},
               "episodes": {"total": len(stats), "failures": len(fails), "successes": len(binary_episodes(stats, failure_rule)) - len(fails), "failureRule": failure_rule, "table": stats},
               "digest": {"lines": len(lines), "note": "read it with read_digest / grep_digest; read_step returns full observations and actual images; inspect images for visual claims"},
               "mode": mode, "cohort": cohort}
    if catalogue is not None:
        kickoff["catalogue"] = {"capabilities": catalogue["capabilities"], "defectTypes": catalogue["defectTypes"]}
    if revision:
        kickoff["revision"] = revision
        kickoff["objectionsToAnswer"] = objections or []
        kickoff["instruction"] = ("An independent reviewer rejected the previous analysis with the objections above. Re-read the cited steps, answer every "
                                  "objection in the analysis by keeping, correcting or withdrawing each behaviour with its evidence, and submit again.")
    result = run_agent(key=f"analysis-{cohort}-{mode}-{task_id}" + (f"-r{revision}" if revision else ""), system=prompt, kickoff=json.dumps(kickoff, ensure_ascii=False), tools=tools,
                       checkpoint_dir=checkpoint_dir, max_turns=max_turns, log=log).result
    (out_dir / "analyses").mkdir(parents=True, exist_ok=True)
    (out_dir / "records").mkdir(parents=True, exist_ok=True)
    write_text(out_dir / "analyses" / f"{task_id}.txt", result["analysis"].rstrip() + "\n")
    record = {"taskId": task_id, "taskName": task.get("name"), "taskTreeOrigin": task.get("taskTreeOrigin"), "cohort": cohort, "mode": mode, "ruleYardstick": result["ruleYardstick"], "requirementCoverage": result["requirementCoverage"], "evidenceChecks": result["evidenceChecks"],
              "trajectories": len(binary_episodes(stats, failure_rule)), "success": len(binary_episodes(stats, failure_rule)) - len(fails), "failure": len(fails),
              "failureRule": failure_rule, "behaviours": result["behaviours"], "nonCapabilityCauses": result["nonCapabilityCauses"], "unresolved": result["unresolved"],
              "revision": revision, "previousReviews": previous_reviews or []}
    write_json(out_dir / "records" / f"{task_id}.json", record)
    return record
