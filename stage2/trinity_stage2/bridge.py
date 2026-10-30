import json
import re
from pathlib import Path

from . import verifier
from .records import read_records, verify_exploration_source


def capability_definitions(catalogue):
    definitions = {}
    for cid in catalogue["order"]:
        entry = catalogue["capabilities"][cid]
        if entry.get("id") != cid or any(not isinstance(entry.get(key), str) or not entry[key].strip() for key in ("name", "definition")):
            raise ValueError("Missing or mismatched capability semantics: " + cid)
        groups, excludes, symptoms = entry.get("groups", {}), entry.get("excludes", []), entry.get("typicalSymptoms", [])
        if not isinstance(groups, dict) or any(not isinstance(k, str) or not k.strip() or not isinstance(v, str) or not v.strip() for k, v in groups.items()):
            raise ValueError("Invalid capability groups: " + cid)
        if any(not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values) for values in (excludes, symptoms)):
            raise ValueError("Invalid capability boundaries or symptoms: " + cid)
        definitions[cid] = {"id": cid, "name": entry["name"], "definition": entry["definition"],
                            "groups": groups, "excludes": excludes, "typicalSymptoms": symptoms}
    return definitions


def export_training(work):
    work = Path(work)
    load = lambda p: json.loads(p.read_text())
    handoff = load(work / "handoff.json")
    if handoff.get("schema") != "trinity-stage2-handoff-v1":
        raise ValueError("Unsupported task handoff")
    tasks = handoff["tasks"]
    ids = [t["taskId"] for t in tasks]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,159}", i) for i in ids):
        raise ValueError("Invalid or duplicate task identifiers")
    if any(t.get("set") not in ("train", "unseen") for t in tasks):
        raise ValueError("Invalid task split")
    split = handoff.get("taskTree", {}).get("split", {})
    if split.get("gaps") or split.get("errors"):
        raise ValueError("The task split is incomplete")
    catalogue = load(work / "capabilities" / "capabilities.json")
    order = catalogue["order"]
    if not order or len(order) != len(set(order)) or set(order) != set(catalogue["capabilities"]):
        raise ValueError("Invalid fixed capability order")
    if any(not re.fullmatch(r"[a-z]+", c) for c in order):
        raise ValueError("Capability identifiers must use lowercase letters")
    definitions = capability_definitions(catalogue)
    assigned = load(work / "train" / "task-capability-gaps.json")
    by_id = {r["taskId"]: r for r in assigned}
    expected = {t["taskId"] for t in tasks if t["set"] == "train"}
    if not expected or len(by_id) != len(assigned) or set(by_id) != expected:
        raise ValueError("Training capability assignments must cover every training task exactly once")
    assignments = []
    initial_feedback = {}
    memory_ledgers = set()
    episodes = read_records(work)
    for task_id in sorted(expected):
        record = by_id[task_id]
        current = load(work / "train" / "records" / f"{task_id}.json")
        if current != record:
            raise ValueError(f"{task_id}: placed records are stale; run assign again")
        if record.get("cohort") != "train" or record.get("review", {}).get("verdict") != "accept":
            raise ValueError(f"{task_id}: an accepted independent training review is required")
        stats = load(work / "stats" / f"{task_id}.json")
        analysis = (work / "train" / "analyses" / f"{task_id}.txt").read_text()
        errors = verifier.gate(record, stats, analysis, catalogue, order, work_dir=work)
        derived = verifier.derive_placement(record, catalogue, order)
        for field in ("placement", "capabilityPath", "missingCapabilities", "satisfiedCapabilities", "defectTypesObserved"):
            if record.get(field) != derived.get(field):
                errors.append(f"{field} differs from the current evidence")
        for behaviour in record["behaviours"]:
            if behaviour.get("defectType") not in catalogue["defectTypes"]:
                errors.append("Training behaviour has no fixed defect assignment")
        if errors:
            raise ValueError(f"{task_id}: " + "; ".join(errors))
        task_episodes = episodes.get(task_id, [])
        if not task_episodes:
            raise ValueError(f"{task_id}: initial H0 feedback is missing")
        raw_rows, sources = [], []
        for episode in task_episodes:
            raw = episode.to_dict()
            proof = raw["source"].pop("integrity", {})
            if proof.get("status") != "verified":
                raise ValueError("Training export requires verified initial H0 feedback")
            sources.append(proof)
            raw_rows.append(raw)
        if any((p["ledgerPath"], p["ledgerHead"]) != (sources[0]["ledgerPath"], sources[0]["ledgerHead"]) for p in sources):
            raise ValueError("Mixed initial H0 source ledgers")
        memory_ledgers.add(str(Path(sources[0]["ledgerPath"]).resolve().parent))
        verified = verify_exploration_source(sources[0], task_id, raw_rows)
        initial_feedback[task_id] = [verified[e.episodeId]["executionReport"] for e in task_episodes]
        assignments.append({"taskId": task_id, "requirements": record["capabilityPath"]})
    if len(memory_ledgers) != 1:
        raise ValueError("Training memory requires one ordered exploration ledger")
    return {"trainingMemoryDirectory": next(iter(memory_ledgers)), "schema": "trinity-training-input-v1", "taxonomy": order, "capabilityDefinitions": definitions, "assignments": assignments, "initialFeedback": initial_feedback,
            "trainingTasks": [t for t in tasks if t["set"] == "train"],
            "unseenTasks": [t for t in tasks if t["set"] == "unseen"]}
