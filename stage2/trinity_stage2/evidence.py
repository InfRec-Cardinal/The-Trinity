import json
from pathlib import Path
from .records import content_digest
from .storage import append_line, complete_lines


def input_digest(work, task_id):
    work = Path(work)
    values = {}
    for folder, suffix in (("records-canonical", ".json"), ("stats", ".json"), ("digests", ".txt")):
        path = work / folder / (task_id + suffix)
        if not path.is_file():
            raise ValueError("Missing check input: " + str(path))
        values[folder] = path.read_text()
    handoff = work / "handoff.json"
    if handoff.exists():
        values["specification"] = next((t for t in json.loads(handoff.read_text())["tasks"] if t["taskId"] == task_id), None)
    return content_digest(values)


def append_check(path, entry):
    entry = {**entry, "id": content_digest(entry)}
    append_line(path, json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def check_log(path):
    return [json.loads(line) for line in complete_lines(path)]


def bind_checks(behaviours, entries, expected_input):
    bindings, errors = [], []
    valid = [e for e in entries if e.get("inputDigest") == expected_input and e.get("id") == content_digest({k: v for k, v in e.items() if k != "id"})]
    for index, behaviour in enumerate(behaviours):
        check = behaviour.get("check", "")
        if not behaviour.get("citations"):
            errors.append(f"behaviours[{index}] cites no trajectory step; cite at least one decisive step")
            continue
        if check.startswith("run_check:"):
            name = check.split(":", 1)[1].strip()
            found = [e for e in valid if e.get("kind") == "execution" and e.get("name") == name and e.get("returncode") == 0]
            if not found:
                errors.append(f"behaviours[{index}] has no successful bound run_check: {name}")
                continue
            bindings.append({"behaviourIndex": index, "kind": "execution", "receiptIds": [found[-1]["id"]]})
        elif check.startswith("read_steps:"):
            ids = []
            for citation in behaviour.get("citations", []):
                found = [e for e in valid if e.get("kind") == "reading" and e.get("episode") == citation["episode"] and e.get("step") == citation["step"]]
                if not found:
                    errors.append(f"behaviours[{index}] cites a step not inspected by read_step")
                else:
                    ids.append(found[-1]["id"])
            bindings.append({"behaviourIndex": index, "kind": "reading", "receiptIds": ids})
        else:
            errors.append(f"behaviours[{index}].check must be run_check:<exact name> or read_steps:<reasoning>")
    return bindings, errors


def verify_checks(record, work):
    work = Path(work)
    task_id = record["taskId"]
    bindings, errors = bind_checks(record["behaviours"], check_log(work / record["cohort"] / "checks" / f"{task_id}.jsonl"), input_digest(work, task_id))
    if bindings != record.get("evidenceChecks"):
        errors.append("Rule-check bindings differ from host execution/inspection receipts")
    return errors


YARDSTICK_FIELDS = ["goal", "observation", "feedback", "actions", "irreversible", "budget", "success", "failure", "competentDecision"]


def coverage_errors(record):
    coverage = record.get("requirementCoverage", [])
    errors = []
    if not isinstance(coverage, list) or sorted(x.get("field", "") for x in coverage) != sorted(YARDSTICK_FIELDS):
        return ["Requirement coverage must explicitly cover every rule-yardstick field exactly once"]
    for row in coverage:
        refs = row.get("behaviourIndices", [])
        reason = row.get("notApplicableReason")
        if not isinstance(refs, list) or any(type(i) is not int or i < 0 or i >= len(record["behaviours"]) for i in refs):
            errors.append("Requirement coverage references unknown behaviour")
        if refs:
            if reason is not None:
                errors.append("Mapped requirements cannot also be marked not applicable")
        elif not isinstance(reason, str) or len(reason.strip()) < 20:
            errors.append("An unmapped specification requirement needs an explicit reviewed non-capability explanation")
        if not isinstance(row.get("requirement"), str) or len(row["requirement"].strip()) < 10:
            errors.append("Every yardstick field requires a concrete requirement or explicit applicability statement")
    return errors
