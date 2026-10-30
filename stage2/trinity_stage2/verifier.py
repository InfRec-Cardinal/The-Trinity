from __future__ import annotations

import json
import re
from pathlib import Path

from .analyst import BANNED, failing_episodes, binary_episodes, digest_tools
from .media import step_evidence
from .model import Tool, ask_once
from .evidence import coverage_errors, verify_checks
from .storage import write_text

PLACEMENTS = ["missing_capability_route", "capability_clue_route", "zero_failure_gap_route", "no_gap_observed"]

VERDICT_SCHEMA = {"type": "object", "properties": {
    "verdict": {"type": "string", "enum": ["accept", "revise"]},
    "objections": {"type": "array", "items": {"type": "object", "properties": {
        "behaviourIndex": {"type": "integer"}, "kind": {"type": "string", "enum": ["citation_mismatch", "unsupported_mechanism", "non_capability_cause", "missing_success_contrast", "confidence_too_high", "coverage_gap", "definition_mismatch", "other"]},
        "detail": {"type": "string", "minLength": 20}}, "required": ["behaviourIndex", "kind", "detail"], "additionalProperties": False}},
    "checkedCitations": {"type": "integer", "minimum": 0},
    "summary": {"type": "string", "minLength": 20}}, "required": ["verdict", "objections", "checkedCitations", "summary"], "additionalProperties": False}


def review_task(*, record: dict, analysis: str, stats: list[dict], digest_path: Path, catalogue: dict | None, checkpoint_dir: Path, prompt: str, log=print) -> dict:
    evidence_errors = verify_checks(record, digest_path.parent.parent) + coverage_errors(record)
    if evidence_errors:
        raise ValueError("; ".join(evidence_errors))
    digest = digest_path.read_text()
    lines = digest.splitlines()
    steps_text = {}
    header = None
    for l in lines:
        if l.startswith("## "):
            header = l[3:].split(" | ")[0].strip()
        elif header and re.match(r"^s\d+ ", l):
            steps_text[(header, int(l[1:l.index(" ")]))] = l

    cited = []
    for i, b in enumerate(record["behaviours"]):
        for c in b.get("citations", []):
            cited.append({"behaviourIndex": i, "episode": c["episode"], "step": c["step"], "text": steps_text.get((c["episode"], c["step"]), "(step not in digest)")[:1500]})
    kickoff = {"record": record, "analysis": analysis, "stats": stats, "citedSteps": cited,
               "catalogue": None if catalogue is None else {"capabilities": catalogue["capabilities"], "defectTypes": catalogue["defectTypes"]}}

    work_dir = digest_path.parent.parent
    visual_citations = set()
    for item in cited:
        evidence = step_evidence(work_dir, record["taskId"], item["episode"], item["step"])
        if evidence["attach"]:
            visual_citations.add((item["episode"], item["step"]))
    inspected = set()
    reader = next(t for t in digest_tools(work_dir, [record["taskId"]]) if t.name == "read_step")
    original_reader = reader.handler
    def read_visual(args):
        value = original_reader(args)
        inspected.add((args["episode"], args["step"]))
        return value
    reader.handler = read_visual
    kickoff["visualCitations"] = [{"episode": episode, "step": step} for episode, step in sorted(visual_citations)]
    kickoff["inspection"] = "Use read_step to inspect the actual images of every visual citation before submitting the verdict."

    def check(args):
        if visual_citations - inspected:
            raise ValueError("Inspect every visual citation with read_step before submitting the verdict")
        if cited and args["checkedCitations"] < 1:
            raise ValueError("Check at least one cited step before submitting the verdict")
        for o in args["objections"]:
            if not 0 <= o["behaviourIndex"] < max(1, len(record["behaviours"])):
                raise ValueError(f"objection names behaviourIndex {o['behaviourIndex']}; the record has {len(record['behaviours'])} behaviours")
        if args["verdict"] == "revise" and not args["objections"]:
            raise ValueError("a revise verdict needs at least one objection")
        return None

    tool = Tool("submit_verdict", "Submit the independent review verdict.", VERDICT_SCHEMA, check)
    verdict = ask_once(key=f"review-{record['cohort']}-{record['taskId']}-r{record.get('revision', 0)}", system=prompt, text=json.dumps(kickoff, ensure_ascii=False), tool=tool, extra_tools=[reader], attempts=max(8, len(visual_citations) + 4), checkpoint_dir=checkpoint_dir, log=log)
    return verdict


def derive_placement(record: dict, catalogue: dict, order: list[str]) -> dict:
    dts = catalogue["defectTypes"]
    missing = {}
    observed = {}
    proposed = {}
    for b in record["behaviours"]:
        dt = b.get("defectType")
        if not dt:
            continue
        if dt.startswith("NEW") and dt not in dts:
            cap = b.get("capability")
            if cap not in catalogue["capabilities"]:
                raise ValueError(f"{record['taskId']}: behaviour {dt!r} names capability {cap!r}, which is not in the fixed catalogue")
            o = proposed.setdefault(dt, {"proposedType": dt, "capability": cap, "definition": b.get("newDefinition"), "failureBehaviours": 0, "successBehaviours": 0, "failureEpisodes": set(), "successEpisodes": set(), "confidence": "lower"})
            if o["capability"] != cap:
                raise ValueError(f"{record['taskId']}: proposed type {dt!r} is used under capabilities {o['capability']} and {cap}; one proposed type evidences one capability")
        elif dt in dts:
            cap = dts[dt]["capability"]
            o = observed.setdefault(dt, {"defectType": dt, "name": dts[dt]["name"], "capability": cap, "failureBehaviours": 0, "successBehaviours": 0, "failureEpisodes": set(), "successEpisodes": set(), "confidence": "lower"})
        else:
            raise ValueError(f"{record['taskId']}: unknown defect type {dt!r}")
        if b["kind"] == "failure":
            o["failureBehaviours"] += 1
            o["failureEpisodes"].update(c["episode"] for c in b.get("citations", []))
            if b["confidence"] == "higher":
                o["confidence"] = "higher"
            level = b["confidence"]
            if missing.get(cap) != "higher":
                missing[cap] = level
        else:
            o["successBehaviours"] += 1
            o["successEpisodes"].update(c["episode"] for c in b.get("citations", []))
    non_cap = {c["episode"] for c in record.get("nonCapabilityCauses", [])}
    failures = record["failure"]
    rank = lambda c: order.index(c) if c in order else len(order)
    evidenced = [*observed.values(), *proposed.values()]
    for o in evidenced:
        o["failureEpisodes"], o["successEpisodes"] = len(o["failureEpisodes"]), len(o["successEpisodes"])
    satisfied = sorted({o["capability"] for o in evidenced if o["successBehaviours"] and o["capability"] not in missing}, key=rank)
    if failures == 0:
        placement = "zero_failure_gap_route" if evidenced else "no_gap_observed"
        missing = {}
    elif any(v == "higher" for v in missing.values()) and len(non_cap) < failures:
        placement = "missing_capability_route"
    else:
        placement = "capability_clue_route"
        missing = {c: "lower" for c in missing}
    path = sorted(set(missing) | set(satisfied), key=rank)
    return {**record, "placement": placement, "capabilityPath": path, "capabilityPathLabel": " -> ".join(path) if path else "H0",
            "missingCapabilities": dict(missing), "satisfiedCapabilities": satisfied,
            "defectTypesObserved": sorted(observed.values(), key=lambda o: (rank(o["capability"]), o["defectType"])),
            "proposedDefectTypes": sorted(proposed.values(), key=lambda o: (rank(o["capability"]), o["proposedType"]))}


def gate(record: dict, stats: list[dict], analysis: str, catalogue: dict, order: list[str], work_dir: Path | None = None) -> list[str]:
    errs = coverage_errors(record)
    if record.get("review", {}).get("verdict") != "accept":
        errs.append(f"the independent review has not accepted this analysis (outcome: {record.get('reviewOutcome', 'not reviewed')})")
    if work_dir is not None:
        errs.extend(verify_checks(record, work_dir))
    elif not record.get("evidenceChecks") and record["behaviours"]:
        errs.append("Host-bound rule-check evidence is missing")
    rule = record.get("failureRule", "outcome")
    eps, fails = binary_episodes(stats, rule), failing_episodes(stats, rule)
    if record["trajectories"] != len(eps) or record["failure"] != len(fails) or record["success"] != len(eps) - len(fails):
        errs.append(f"counts {record['trajectories']}/{record['success']}/{record['failure']} differ from the stats table {len(eps)}/{len(eps) - len(fails)}/{len(fails)}")
    if record["placement"] not in PLACEMENTS:
        errs.append(f"placement {record['placement']!r}")
    path = record["capabilityPath"]
    if path != sorted(path, key=lambda c: order.index(c) if c in order else 99):
        errs.append(f"path {path} is not in the fixed order {order}")
    expected = sorted(set(record["missingCapabilities"]) | set(record.get("satisfiedCapabilities", [])), key=lambda c: order.index(c) if c in order else 99)
    if path != expected:
        errs.append(f"path {path} differs from the requirement set {expected} (missing plus satisfied capabilities)")
    if record["placement"] == "missing_capability_route" and not any(v == "higher" for v in record["missingCapabilities"].values()):
        errs.append("missing-capability placement without a higher-confidence missing capability")
    if record["placement"] == "capability_clue_route" and any(v == "higher" for v in record["missingCapabilities"].values()):
        errs.append("clue placement with a higher-confidence missing capability")
    if fails and not record["missingCapabilities"]:
        unattributed = sorted(f for f in fails if f not in {c["episode"] for c in record.get("nonCapabilityCauses", [])})
        if unattributed:
            errs.append(f"the task has {len(fails)} failing episode(s) but no missing capability, and {len(unattributed)} of them are not attributed to a non-capability cause: {unattributed[:4]}")
        if record["placement"] != "capability_clue_route":
            errs.append("the task has failures but no missing capability")
    for p in record.get("proposedDefectTypes", []):
        if p["capability"] not in catalogue["capabilities"]:
            errs.append(f"proposed type {p['proposedType']} names unknown capability {p['capability']}")
        if p["capability"] not in record["capabilityPath"]:
            errs.append(f"proposed type {p['proposedType']} evidences capability {p['capability']}, which is missing from the path")
    for d in record["defectTypesObserved"]:
        if d["defectType"] not in catalogue["defectTypes"]:
            errs.append(f"unknown defect type {d['defectType']}")
        elif catalogue["defectTypes"][d["defectType"]]["capability"] != d["capability"]:
            errs.append(f"{d['defectType']} listed under {d['capability']}, catalogue says {catalogue['defectTypes'][d['defectType']]['capability']}")
    steps = {s["episode"]: s.get("steps") for s in stats}
    cited, bad = set(), 0
    for index, b in enumerate(record["behaviours"]):
        if not b.get("citations"):
            errs.append(f"behaviours[{index}] cites no trajectory step")
        for c in b.get("citations", []):
            if c["episode"] not in steps:
                bad += 1
                continue
            cited.add(c["episode"])
            n = steps[c["episode"]]
            if n is not None and not 0 <= c["step"] <= n:
                bad += 1
    if bad:
        errs.append(f"{bad} citation(s) name unknown episodes or out-of-range steps")
    attributed = {c["episode"] for c in record.get("nonCapabilityCauses", [])}
    uncovered = [f for f in fails if f not in cited and f not in attributed and f not in analysis]
    if uncovered:
        errs.append(f"{len(uncovered)} failing episode(s) neither cited, attributed nor named: {uncovered[:4]}")
    text = analysis + json.dumps(record, ensure_ascii=False)
    hits = sorted({m.group(0) for m in BANNED.finditer(text)})
    if hits:
        errs.append(f"banned wording: {hits}")
    return errs


def write_gate_report(results: dict[str, list[str]], path: Path) -> bool:
    lines = [("PASS " if not errs else "FAIL ") + task + "".join("\n     - " + e for e in errs) for task, errs in sorted(results.items())]
    write_text(path, "\n".join(lines) + "\n")
    return not any(results.values())
