from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from .analyst import digest_tools
from .model import Tool, run_agent
from .storage import write_csv, write_json, write_text

LETTERS = "abcdefghijklmnopqrstuvwxyz"
CAPABILITY_KEY = r"^cap-[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
DEFECT_KEY = r"^dt-[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
INDUCTION_VERSION = "evidence-v2"

CATALOGUE_SCHEMA = {"type": "object", "properties": {
    "capabilities": {"type": "array", "items": {"type": "object", "properties": {
        "key": {"type": "string", "pattern": CAPABILITY_KEY, "description": "Descriptive semantic key, not a final display identifier"}, "name": {"type": "string", "minLength": 4}, "definition": {"type": "string", "minLength": 40},
        "groups": {"type": "array", "items": {"type": "object", "properties": {"name": {"type": "string"}, "definition": {"type": "string"}}, "required": ["name", "definition"], "additionalProperties": False}},
        "excludes": {"type": "array", "items": {"type": "string"}}, "typicalSymptoms": {"type": "array", "items": {"type": "string"}}},
        "required": ["key", "name", "definition", "groups", "excludes", "typicalSymptoms"], "additionalProperties": False}},
    "defectTypes": {"type": "array", "items": {"type": "object", "properties": {
        "key": {"type": "string", "pattern": DEFECT_KEY, "description": "Descriptive semantic key, not a final display identifier"}, "name": {"type": "string", "minLength": 4}, "capability": {"type": "string"}, "group": {"type": "string"},
        "definition": {"type": "string", "minLength": 40, "description": "Pass / fail definition: what the Player must do at the decisive step, in task-independent words."}},
        "required": ["key", "name", "capability", "group", "definition"], "additionalProperties": False}},
    "assignments": {"type": "array", "items": {"type": "object", "properties": {"behaviour": {"type": "string", "description": "<taskId>#<behaviourIndex>"}, "defectType": {"type": "string"}},
                                                "required": ["behaviour", "defectType"], "additionalProperties": False}},
    "notes": {"type": "string"}}, "required": ["capabilities", "defectTypes", "assignments", "notes"], "additionalProperties": False}

REVIEW_SCHEMA = {"type": "object", "properties": {
    "verdict": {"type": "string", "enum": ["accept", "revise"]},
    "findings": {"type": "array", "items": {"type": "object", "properties": {
        "check": {"type": "string", "enum": ["definitions", "evidence", "assignments", "coverage"]},
        "target": {"type": "string", "description": "capability key, defect type key or behaviour id"},
        "detail": {"type": "string", "minLength": 20}}, "required": ["check", "target", "detail"], "additionalProperties": False}},
    "summary": {"type": "string", "minLength": 20}}, "required": ["verdict", "findings", "summary"], "additionalProperties": False}


def behaviour_inventory(records: dict[str, dict], tasks: dict[str, dict]) -> list[dict]:
    rows = []
    for task_id, r in sorted(records.items()):
        t = tasks.get(task_id, {})
        for i, b in enumerate(r["behaviours"]):
            rows.append({"id": f"{task_id}#{i}", "task": t.get("name", task_id), "domain": (t.get("taskTreeOrigin") or {}).get("domainName"), "kind": b["kind"], "confidence": b["confidence"],
                         "label": b.get("defectLabel"), "definition": b.get("defectDefinition") or b.get("newDefinition"), "behaviour": b["behaviour"], "instance": b["instance"][:600]})
    return rows


def check_catalogue(args: dict, inventory: list[dict]) -> list[str]:
    problems, caps, dts = [], {}, {}
    if set(args) - set(CATALOGUE_SCHEMA["properties"]):
        problems.append("unsupported catalogue fields; submit semantic categories and assignments only")
    for c in args["capabilities"]:
        if not re.fullmatch(CAPABILITY_KEY, c["key"]):
            problems.append("capability keys must be descriptive cap-... keys, not final display identifiers")
        if set(c) - set(CATALOGUE_SCHEMA["properties"]["capabilities"]["items"]["properties"]):
            problems.append(f"unsupported capability fields for {c['key']}")
        if c["key"] in caps:
            problems.append(f"duplicate capability key {c['key']}")
        caps[c["key"]] = c
    for d in args["defectTypes"]:
        if not re.fullmatch(DEFECT_KEY, d["key"]):
            problems.append("defect keys must be descriptive dt-... keys, not final display identifiers")
        if set(d) - set(CATALOGUE_SCHEMA["properties"]["defectTypes"]["items"]["properties"]):
            problems.append(f"unsupported defect type fields for {d['key']}")
        if d["key"] in dts:
            problems.append(f"duplicate defect type key {d['key']}")
        if d["capability"] not in caps:
            problems.append(f"defect type {d['key']} names unknown capability {d['capability']}")
        elif d["group"] and d["group"] not in {g["name"] for g in caps[d["capability"]]["groups"]}:
            problems.append(f"defect type {d['key']} names group {d['group']!r}, which capability {d['capability']} does not define")
        dts[d["key"]] = d
    ids = {row["id"] for row in inventory}
    seen = defaultdict(int)
    for a in args["assignments"]:
        if a["behaviour"] not in ids:
            problems.append(f"assignment names unknown behaviour {a['behaviour']}")
        if a["defectType"] not in dts:
            problems.append(f"assignment of {a['behaviour']} names unknown defect type {a['defectType']}")
        seen[a["behaviour"]] += 1
    for row in inventory:
        if seen[row["id"]] != 1:
            problems.append(f"behaviour {row['id']} must be assigned exactly once (found {seen[row['id']]})")
    for key in dts:
        if not any(a["defectType"] == key for a in args["assignments"]):
            problems.append(f"defect type {key} has no behaviour")
    for key in caps:
        if not any(d["capability"] == key for d in dts.values()):
            problems.append(f"capability {key} has no defect type")
    return problems[:20]


def _catalogue_tool(inventory, name="submit_catalogue"):
    def handler(args):
        problems = check_catalogue(args, inventory)
        if problems:
            raise ValueError("; ".join(problems))
        return {"finish": args}
    return Tool(name, "Submit the catalogue: capabilities, defect types and the assignment of every behaviour to exactly one defect type.", CATALOGUE_SCHEMA, handler)


def task_specs(tasks: dict) -> list[dict]:
    return [{"taskId": t["taskId"], "name": t.get("name"), "domain": (t.get("taskTreeOrigin") or {}).get("domainName"), "subClass": (t.get("taskTreeOrigin") or {}).get("subCategoryName"),
             "assignment": t.get("assignment"), "inputScope": {k: v for k, v in (t.get("inputScope") or {}).items() if k != "evidence"}} for t in tasks.values()]


def propose(*, inventory, tasks, proposers: int, prompt: str, checkpoint_dir: Path, work_dir: Path, log=print) -> list[dict]:
    specs = task_specs(tasks)
    reads = digest_tools(work_dir, sorted(tasks))
    out = []
    for k in range(proposers):
        kickoff = {"proposer": k + 1, "of": proposers, "tasks": specs, "behaviours": inventory,
                   "instruction": "Work independently. Read the cited steps of any behaviour you need to judge (read_step). Infer the capabilities and defect types supported by the behaviours, including satisfied requirements. Choose their number and boundaries from evidence; input channels are specification context only. Use descriptive semantic keys, with no final display identifiers or predefined taxonomy."}
        out.append(run_agent(key=f"induction-{INDUCTION_VERSION}-proposer-{k + 1}", system=prompt, kickoff=json.dumps(kickoff, ensure_ascii=False), tools=[*reads, _catalogue_tool(inventory)], checkpoint_dir=checkpoint_dir, max_turns=40, max_tokens=32000, log=log).result)
    return out


def consolidate(*, proposals, inventory, tasks, prompt: str, checkpoint_dir: Path, work_dir: Path, round_no: int = 0, objections=None, previous=None, log=print) -> dict:
    kickoff = {"proposals": proposals, "behaviours": inventory, "tasks": task_specs(tasks)}
    if previous is not None:
        kickoff = {"currentCatalogue": previous, "reviewerFindings": objections, "behaviours": inventory, "proposals": proposals, "tasks": task_specs(tasks),
                   "instruction": "Repair the current catalogue so that every reviewer finding is resolved; keep what the reviewers accepted."}
    return run_agent(key=f"induction-{INDUCTION_VERSION}-judge-r{round_no}", system=prompt, kickoff=json.dumps(kickoff, ensure_ascii=False), tools=[*digest_tools(work_dir, sorted(tasks)), _catalogue_tool(inventory)],
                     checkpoint_dir=checkpoint_dir, max_turns=40, max_tokens=32000, log=log).result


def review_catalogue(*, catalogue, inventory, tasks, reviewers: int, prompt: str, checkpoint_dir: Path, work_dir: Path, round_no: int, log=print) -> list[dict]:
    out = []
    for k in range(reviewers):
        check = ["definitions", "evidence", "assignments", "coverage"][k % 4]
        kickoff = {"reviewer": k + 1, "focus": check, "catalogue": catalogue, "behaviours": inventory, "tasks": task_specs(tasks),
                   "instruction": f"Check all four criteria, with particular care for {check}. Read cited steps (read_step) wherever a judgement depends on them. Accept only when every criterion holds."}
        tool = Tool("submit_review", "Submit the independent catalogue review.", REVIEW_SCHEMA, lambda args: {"finish": args})
        out.append(run_agent(key=f"induction-{INDUCTION_VERSION}-review-r{round_no}-{k + 1}", system=prompt, kickoff=json.dumps(kickoff, ensure_ascii=False), tools=[*digest_tools(work_dir, sorted(tasks)), tool],
                             checkpoint_dir=checkpoint_dir, max_turns=30, max_tokens=16000, log=log).result)
    return out


def capability_label(index: int) -> str:
    if index < 0:
        raise ValueError("Capability index must be nonnegative")
    label, value = "", index + 1
    while value:
        value, remainder = divmod(value - 1, len(LETTERS))
        label = LETTERS[remainder] + label
    return label


def check_training_records(records: dict, tasks: dict) -> None:
    for task_id, task in tasks.items():
        if task.get("set", task.get("cohort", "train")) != "train":
            raise ValueError("Capability induction accepts training task specifications only: " + task_id)
    for task_id, record in records.items():
        if task_id not in tasks or record.get("cohort", "train") != "train":
            raise ValueError("Capability induction accepts training task records only: " + task_id)
        if any(b.get("kind") not in ("failure", "success") for b in record["behaviours"]):
            raise ValueError("Unknown behaviour evidence kind: " + task_id)


def label_and_order(catalogue: dict, records: dict[str, dict], tasks: dict[str, dict]) -> dict:
    check_training_records(records, tasks)
    problems = check_catalogue(catalogue, behaviour_inventory(records, tasks))
    if problems:
        raise ValueError("; ".join(problems))
    by_key = {c["key"]: c for c in catalogue["capabilities"]}
    dt_cap = {d["key"]: d["capability"] for d in catalogue["defectTypes"]}
    assign = {a["behaviour"]: a["defectType"] for a in catalogue["assignments"]}
    domains, required, failed, succeeded = (defaultdict(set) for _ in range(4))
    requirements = {}
    for task_id, record in records.items():
        origin = tasks[task_id].get("taskTreeOrigin") or {}
        domain = ("id", origin["domainId"]) if origin.get("domainId") else ("name", origin.get("domainName") or "unknown")
        task_requirements = set()
        for i, behaviour in enumerate(record["behaviours"]):
            capability = dt_cap[assign[f"{task_id}#{i}"]]
            task_requirements.add(capability)
            (failed if behaviour["kind"] == "failure" else succeeded)[capability].add(task_id)
        requirements[task_id] = task_requirements
        for capability in task_requirements:
            domains[capability].add(domain)
            required[capability].add(task_id)
    ordered = sorted(by_key, key=lambda key: (-len(domains[key]), -len(required[key]), key))
    labels = {key: capability_label(i) for i, key in enumerate(ordered)}
    caps = {}
    for key in ordered:
        c = by_key[key]
        caps[labels[key]] = {"id": labels[key], "name": c["name"], "definition": c["definition"],
                            "groups": {g["name"]: g["definition"] for g in c["groups"]},
                            "excludes": c["excludes"], "typicalSymptoms": c["typicalSymptoms"],
                            "domainBreadth": len(domains[key]), "tasksRequiringCapability": sorted(required[key]),
                            "tasksWithFailureEvidence": sorted(failed[key]), "tasksWithSuccessEvidence": sorted(succeeded[key]), "judgeKey": key}
    dts, counter = {}, defaultdict(int)
    rank = {key: i for i, key in enumerate(ordered)}
    for d in sorted(catalogue["defectTypes"], key=lambda d: (rank[d["capability"]], d["key"])):
        cap = labels[d["capability"]]
        counter[cap] += 1
        did = f"{cap.upper()}{counter[cap]:02d}"
        dts[did] = {"id": did, "name": d["name"], "capability": cap, "group": d["group"], "definition": d["definition"], "judgeKey": d["key"]}
    key_to_id = {v["judgeKey"]: key for key, v in dts.items()}
    return {"schema": "trinity-capability-catalogue-v1", "inductionPolicy": INDUCTION_VERSION, "order": [labels[key] for key in ordered],
            "orderRule": "descending domain breadth across training requirement sets (failure and satisfied evidence), then descending training task count, then semantic key; display identifiers assigned only after catalogue review",
            "trainingRequirements": {task_id: [labels[key] for key in ordered if key in needed] for task_id, needed in sorted(requirements.items())},
            "capabilities": caps, "defectTypes": dts, "assignments": {behaviour: key_to_id[defect] for behaviour, defect in assign.items()}}


def apply_assignments(records: dict[str, dict], catalogue: dict) -> dict[str, dict]:
    out = {}
    for task_id, r in records.items():
        r = json.loads(json.dumps(r))
        for i, b in enumerate(r["behaviours"]):
            dt = catalogue["assignments"].get(f"{task_id}#{i}")
            if dt:
                b["defectType"], b["capability"] = dt, catalogue["defectTypes"][dt]["capability"]
        out[task_id] = r
    return out


def write_defect_table(catalogue: dict, path: Path, records: dict[str, dict], tasks: dict[str, dict], unseen: dict[str, dict] | None = None) -> None:
    def exposed(recs):
        fail, succ = set(), set()
        for task_id, r in recs.items():
            name = r.get("taskName") or tasks.get(task_id, {}).get("name", task_id)
            for b in r["behaviours"]:
                if b.get("defectType") == did:
                    (fail if b["kind"] == "failure" else succ).add(name)
        return fail, succ
    rows = [["defectType", "name", "capability", "capabilityName", "group", "trainingTasksWithFailureEvidence", "trainingTasksWithSuccessContrast",
             "unseenTasksWithFailureEvidence", "unseenTasksWithSuccessContrast", "trainingCount", "unseenCount", "definition"]]
    for did, dt in catalogue["defectTypes"].items():
        tf, ts = exposed(records)
        uf, us = exposed(unseen or {})
        rows.append([did, dt["name"], dt["capability"], catalogue["capabilities"][dt["capability"]]["name"], dt["group"], "; ".join(sorted(tf)), "; ".join(sorted(ts)),
                     "; ".join(sorted(uf)), "; ".join(sorted(us)), len(tf), len(uf), dt["definition"]])
    write_csv(path, rows)


def write_catalogue(catalogue: dict, out_dir: Path, records: dict[str, dict] | None = None, tasks: dict[str, dict] | None = None, unseen: dict[str, dict] | None = None) -> None:
    d = out_dir / "capabilities"
    d.mkdir(parents=True, exist_ok=True)
    write_json(d / "capabilities.json", catalogue)
    write_defect_table(catalogue, d / "defect-types.csv", records or {}, tasks or {}, unseen)
    lines = ["# Capabilities", "", f"{len(catalogue['capabilities'])} capabilities and {len(catalogue['defectTypes'])} defect types, induced from the training analyses. "
             f"Order of the tree: {', '.join(catalogue['order'])} ({catalogue['orderRule']}).", ""]
    for cid in catalogue["order"]:
        c = catalogue["capabilities"][cid]
        lines += [f"## {cid} - {c['name']}", "", f"**Definition.** {c['definition']}", ""]
        for g, gd in c["groups"].items():
            lines.append(f"- *{g}*: {gd}")
        lines += ["", "**Excludes.** " + " ".join(c["excludes"]), "", "| Defect type | Group | Definition |", "|---|---|---|"]
        for did, dt in catalogue["defectTypes"].items():
            if dt["capability"] == cid:
                lines.append(f"| {did} {dt['name']} | {dt['group']} | {dt['definition']} |")
        lines.append("")
    write_text(d / "CAPABILITIES.txt", "\n".join(lines))


def induce(*, records, tasks, out_dir: Path, checkpoint_dir: Path, prompts: dict, proposers: int = 3, reviewers: int = 4, rounds: int = 3, work_dir: Path | None = None, log=print) -> dict:
    work_dir = work_dir or out_dir
    if any(type(value) is not int or value < 1 for value in (proposers, reviewers, rounds)):
        raise ValueError("Induction requires at least one proposer, reviewer and review round")
    check_training_records(records, tasks)
    inventory = behaviour_inventory(records, tasks)
    proposals = propose(inventory=inventory, tasks=tasks, proposers=proposers, prompt=prompts["proposer"], checkpoint_dir=checkpoint_dir, work_dir=work_dir, log=log)
    catalogue, objections = None, None
    for round_no in range(rounds):
        catalogue = consolidate(proposals=proposals, inventory=inventory, tasks=tasks, prompt=prompts["judge"] if round_no == 0 else prompts["reviser"], checkpoint_dir=checkpoint_dir, work_dir=work_dir, round_no=round_no, objections=objections, previous=catalogue, log=log)
        reviews = review_catalogue(catalogue=catalogue, inventory=inventory, tasks=tasks, reviewers=reviewers, prompt=prompts["catalogue_reviewer"], checkpoint_dir=checkpoint_dir, work_dir=work_dir, round_no=round_no, log=log)
        (out_dir / "induction").mkdir(parents=True, exist_ok=True)
        write_json(out_dir / "induction" / f"round-{round_no}.json", {"catalogue": catalogue, "reviews": reviews})
        objections = [f for r in reviews for f in r["findings"]]
        if all(r["verdict"] == "accept" for r in reviews):
            log(f"catalogue accepted by all {reviewers} reviewers in round {round_no + 1}")
            break
        log(f"round {round_no + 1}: {len(objections)} finding(s) to resolve")
    else:
        raise RuntimeError(f"the catalogue was not accepted within {rounds} rounds; see {out_dir / 'induction'}")
    labelled = label_and_order(catalogue, records, tasks)
    write_json(out_dir / "induction" / "proposals.json", proposals)
    return labelled
