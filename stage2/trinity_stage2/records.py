from __future__ import annotations

import hashlib
import json
import os
import math
import re
from decimal import Decimal
from dataclasses import dataclass, field, asdict
from pathlib import Path
from .media import normalize_media
from .storage import write_text

SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,159}")
LONE_SURROGATE = re.compile("[\ud800-\udfff]")


def safe_id(value) -> str:
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
        raise ValueError(f"Invalid task identifier: {value!r}")
    return value


def canonical(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, list):
        return "[" + ",".join(canonical(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + canonical(value[k]) for k in sorted(value, key=lambda k: k.encode("utf-16-be"))) + "}"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Non-finite evidence number")
        if value == 0:
            return "0"
        shortest = repr(value).lower()
        if 1e-6 <= abs(value) < 1e21:
            result = format(Decimal(shortest), "f")
            return result.rstrip("0").rstrip(".") if "." in result else result
        mantissa, exponent = shortest.split("e")
        exponent = int(exponent)
        return mantissa.removesuffix(".0") + "e" + ("+" if exponent >= 0 else "-") + str(abs(exponent))
    if isinstance(value, str):
        return LONE_SURROGATE.sub(lambda match: "\\u%04x" % ord(match.group()), json.dumps(value, ensure_ascii=False))
    return json.dumps(value, ensure_ascii=False)


def verify_chain(step_dir: Path) -> dict:
    verified = mismatched = 0
    breaks: list[str] = []
    previous = None
    for name in sorted(os.listdir(step_dir)):
        if not name.endswith(".json"):
            continue
        e = json.loads((step_dir / name).read_text())
        if "hash" not in e:
            return {"verified": 0, "mismatched": 0, "breaks": [], "status": "unhashed"}
        digest = hashlib.sha256(canonical({"index": e.get("index"), "previousHash": e.get("previousHash"), "data": e.get("data")}).encode()).hexdigest()
        if digest == e["hash"]:
            verified += 1
        else:
            mismatched += 1
        if e.get("previousHash") != previous:
            breaks.append(name)
        previous = e["hash"]
    return {"verified": verified, "mismatched": mismatched, "breaks": breaks, "status": "intact" if not mismatched and not breaks else "broken"}


@dataclass
class Step:
    index: int
    action: object
    observation: object
    terminal: dict | None = None
    reward: object = None


@dataclass
class Episode:
    taskId: str
    episodeId: str
    configuration: str | None
    outcome: str | None
    score: object
    reason: str | None
    initialObservation: object
    steps: list[Step] = field(default_factory=list)
    source: dict = field(default_factory=dict)

    @property
    def step_count(self) -> int:
        return len(self.steps)

    def to_dict(self) -> dict:
        return asdict(self)


def _text(observation) -> str:
    return normalize_media(observation) if observation is not None else ""


def load_lab_run(run_dir: Path, task_id: str | None = None) -> list[Episode]:
    checkpoint = json.loads((run_dir / "checkpoint.json").read_text())
    task_id = task_id or checkpoint.get("taskId")
    configurations = checkpoint.get("configurations") or []
    episodes = []
    for e in checkpoint.get("episodes") or []:
        if e.get("status") not in (None, "completed"):
            continue
        conf = configurations[e["configurationIndex"]] if isinstance(e.get("configurationIndex"), int) and e["configurationIndex"] < len(configurations) else {}
        steps = []
        step_dir = run_dir / "episodes" / e["id"] / "h0-trace" / "steps"
        integrity = verify_chain(step_dir) if step_dir.is_dir() else {"status": "missing"}
        if integrity.get("status") == "broken":
            raise ValueError(f"{task_id} {e['id']}: the step records failed the hash-chain check ({integrity})")
        if step_dir.is_dir():
            for name in sorted(os.listdir(step_dir)):
                if not name.endswith(".json"):
                    continue
                d = json.loads((step_dir / name).read_text())
                d = d.get("data", d)
                o = d.get("observation") or {}
                steps.append(Step(index=d.get("index", len(steps) + 1), action=d.get("action"), observation=_text(o), terminal=o.get("terminal") if isinstance(o, dict) else None, reward=d.get("reward")))
        episodes.append(Episode(taskId=task_id, episodeId=e["id"], configuration=conf.get("id") or conf.get("label"), outcome=e.get("outcome"),
                                score=e.get("score"), reason=e.get("terminalReason"), initialObservation=_text(e.get("initialObservation")), steps=steps,
                                source={"format": "lab", "run": str(run_dir), "runId": checkpoint.get("id") or run_dir.name, "integrity": integrity}))
    return episodes


def load_jsonl_episode(record: Path, task_id: str | None = None, episode_id: str | None = None) -> Episode:
    lines = [json.loads(l) for l in record.read_text().splitlines() if l.strip()]
    initial = next((l for l in lines if l.get("kind") == "initial"), {})
    steps, terminal = [], None
    for l in lines:
        if l.get("kind") != "step":
            continue
        o = l.get("observation") or {}
        terminal = (o.get("terminal") if isinstance(o, dict) else None) or terminal
        steps.append(Step(index=l.get("index", len(steps) + 1), action=l.get("action"), observation=_text(o), terminal=o.get("terminal") if isinstance(o, dict) else None, reward=l.get("reward")))
    t = terminal or {}
    return Episode(taskId=task_id or initial.get("taskId") or "unknown", episodeId=episode_id or record.parent.name, configuration=initial.get("configuration"),
                   outcome=t.get("outcome"), score=t.get("score"), reason=t.get("reason"), initialObservation=_text(initial.get("observation")), steps=steps,
                   source={"format": "jsonl", "path": str(record)})


def load_package_trajectory(path: Path) -> Episode:
    d = json.loads(path.read_text())
    texts = d.get("observations") or {}
    def resolve(ref):
        if not isinstance(ref, dict):
            return normalize_media(ref) if ref is not None else ""
        if any(key in ref for key in ("imageRef", "imageRefs")):
            raise ValueError("Unresolved image references in package trajectory; export canonical observations with embedded image blocks")
        observation = {key: value for key, value in ref.items() if key != "textRef"}
        if "textRef" in ref:
            if ref["textRef"] not in texts:
                raise ValueError("Missing package observation reference")
            text = texts[ref["textRef"]]
            if not observation:
                return normalize_media(text)
            observation["text"] = text
        return normalize_media(observation)
    steps_in = d.get("steps") or []
    initial = resolve(steps_in[0]["before"]) if steps_in else ""
    steps = []
    for s in steps_in:
        md = s.get("recordedEnvironmentMetadata") or {}
        steps.append(Step(index=int(s.get("index", len(steps) + 1)), action=s.get("action"), observation=resolve(s.get("after")), terminal=md.get("terminal"), reward=md.get("reward")))
    return Episode(taskId=d["taskId"], episodeId=d["episodeId"], configuration=d.get("configurationId"), outcome=d.get("outcome"), score=d.get("score"),
                   reason=d.get("terminalReason"), initialObservation=initial, steps=steps, source={"format": "package", "path": str(path), "runId": d.get("runId")})


def content_digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def verify_exploration_source(src, task_id, rows):
    ledger = Path(src.get("ledgerPath", ""))
    if not ledger.is_file() or not src.get("ledgerHead"):
        raise ValueError("Canonical H0 import requires a pinned source ledger")
    events, previous = [], None
    for index, line in enumerate(ledger.read_text().splitlines(), 1):
        event = json.loads(line)
        raw = {k: v for k, v in event.items() if k != "hash"}
        if event.get("sequence") != index or event.get("previous") != previous or content_digest(raw) != event.get("hash"):
            raise ValueError("Exploration ledger integrity failure")
        events.append(event)
        previous = event["hash"]
    if previous != src["ledgerHead"]:
        raise ValueError("Exploration ledger head mismatch")
    exports = [e["payload"] for e in events if e["type"] == "exploration_task_exported" and e["payload"]["taskId"] == task_id]
    if len(exports) != 1 or exports[0]["recordsDigest"] != content_digest(rows):
        raise ValueError("Canonical records differ from the host export")
    export = exports[0]
    if export["episodeIds"] != [r["episodeId"] for r in rows]:
        raise ValueError("Exported episode order mismatch")
    starts = {e["hash"]: e["payload"] for e in events if e["type"] == "episode_started"}
    finishes = {e["payload"]["episodeId"]: e for e in events if e["type"] == "episode_finished"}
    reports = {}
    for row in rows:
        start = starts.get(row["episodeId"])
        event = finishes.get(row["episodeId"])
        report = event["payload"] if event else {}
        sealed = report.get("terminalReceipt", {})
        receipt = sealed.get("receipt", {})
        if not start or report.get("technicalFailure") or row["configuration"] != content_digest([]):
            raise ValueError("Verified H0 execution required")
        for key, expected in {"taskId": task_id, "harnessId": content_digest([]), "split": export["cohort"], "phase": "initial_training_exploration"}.items():
            if start.get(key) != expected or report.get(key) != expected:
                raise ValueError("H0 source identity mismatch: " + key)
        for key in ("harnessId", "worldDigest", "budget"):
            if receipt.get(key) != start.get(key):
                raise ValueError("Terminal receipt binding mismatch: " + key)
        if receipt.get("episodeId") != row["episodeId"] or receipt.get("decisionId") is not None or content_digest(receipt) != sealed.get("hash"):
            raise ValueError("Invalid terminal receipt")
        plan_event = next((e for e in events if e["hash"] == report.get("instancePlan") and e["type"] == "initial_instances_frozen"), None)
        start_event = next(e for e in events if e["hash"] == row["episodeId"])
        if not plan_event or plan_event["sequence"] >= start_event["sequence"]:
            raise ValueError("H0 instances must be fixed before execution")
        plan = json.loads((ledger.parent / "objects" / (plan_event["payload"]["artifact"] + ".json")).read_text())
        if content_digest(plan) != plan_event["payload"]["artifact"] or content_digest(plan) != plan_event["payload"]["planDigest"] or plan["taskId"] != task_id:
            raise ValueError("Invalid initial instance manifest")
        if not any(instance == report.get("instance") and plan["initialStateHashes"][i] == report.get("initialStateHash") for i, instance in enumerate(plan["instances"])):
            raise ValueError("H0 initial state differs from its fixed manifest")
        if report.get("initialStateHash") != report.get("expectedInitialStateHash") or not report.get("initialStateHash"):
            raise ValueError("Unverified initial state")
        for key in ("initialStateHash", "expectedInitialStateHash", "instancePlan"):
            if receipt.get(key) != report.get(key) or (key != "initialStateHash" and start.get(key) != report.get(key)):
                raise ValueError("Initial state receipt binding mismatch")
        if receipt.get("instanceDigest") != content_digest(report.get("instance")) or start.get("instance") != report.get("instance"):
            raise ValueError("Initial selector receipt binding mismatch")
        if receipt.get("evidenceDigest") != content_digest(report.get("events")) or receipt.get("publicTaskDigest") != content_digest(report.get("publicTask")):
            raise ValueError("Terminal evidence mismatch")
        actions = [e["publicData"] for e in report["events"] if e.get("publicData", {}).get("action")]
        if not actions or len(actions) != receipt.get("actions") or len(actions) != report.get("actions") or len(actions) > start["budget"]:
            raise ValueError("Incomplete terminal trajectory")
        if any(a["step"] != i or a["receipt"].get("done") for i, a in enumerate(actions[:-1], 1)):
            raise ValueError("Invalid action sequence")
        last = actions[-1]["receipt"]
        if receipt["termination"] == "environment":
            if not last["done"] or last["success"] != report["success"]:
                raise ValueError("Environment termination mismatch")
        elif receipt["termination"] != "host_budget_exhausted" or last["done"] or report["success"] or len(actions) != start["budget"]:
            raise ValueError("Invalid budget settlement")
        for key in ("success", "score", "cost"):
            if receipt[key] != report[key]:
                raise ValueError("Terminal outcome mismatch")
        if last.get("score") != report["score"] or sum(a["receipt"]["cost"] for a in actions) != report["cost"]:
            raise ValueError("Terminal score/cost mismatch")
        expected_outcome = "success" if report["success"] else "failure"
        if row["outcome"] != expected_outcome or row["score"] != report["score"] or len(row["steps"]) != len(actions):
            raise ValueError("Canonical outcome mismatch")
        if row["initialObservation"] != normalize_media(actions[0]["observation"]):
            raise ValueError("Canonical initial observation mismatch")
        for step, action in zip(row["steps"], actions):
            if step["action"] != action["action"] or step["observation"] != normalize_media(action["receipt"]["observation"]):
                raise ValueError("Canonical action evidence mismatch")
        reports[row["episodeId"]] = {"ledgerPath": str(ledger.resolve()), "ledgerHead": previous,
            "episodeEventHash": event["hash"], "status": "verified", "executionReport": report}
    return reports


def import_runs(spec: dict) -> dict[str, list[Episode]]:
    out: dict[str, list[Episode]] = {}
    for task_id, src in spec.items():
        safe_id(task_id)
        fmt, path = src["format"], Path(src["path"]).expanduser()
        if fmt == "canonical":
            rows = json.loads(path.read_text())
            proofs = verify_exploration_source(src, task_id, rows)
            eps = []
            seen = set()
            for row in rows:
                if row.get("taskId") != task_id or row.get("episodeId") in seen:
                    raise ValueError("Canonical trajectory identity mismatch")
                seen.add(row["episodeId"])
                row = dict(row)
                row["source"] = {**row.get("source", {}), "integrity": proofs[row["episodeId"]]}
                steps = [Step(**step) for step in row.pop("steps")]
                if [step.index for step in steps] != list(range(1, len(steps) + 1)):
                    raise ValueError("Canonical trajectory steps are not sequential")
                eps.append(Episode(steps=steps, **row))
        elif fmt == "lab":
            eps = load_lab_run(path, task_id)
        elif fmt == "jsonl":
            eps = [load_jsonl_episode(p, task_id) for p in sorted(path.rglob("record.jsonl"))]
        elif fmt == "package":
            eps = [load_package_trajectory(p) for p in sorted(path.rglob("*.json")) if p.name.startswith("case-") or p.name.startswith("episode-")]
            eps = [e for e in eps if e.taskId == task_id] or eps
        else:
            raise ValueError(f"{task_id}: unknown record format {fmt}")
        out[task_id] = eps
    return out


def write_records(episodes: dict[str, list[Episode]], out_dir: Path) -> None:
    d = out_dir / "records-canonical"
    d.mkdir(parents=True, exist_ok=True)
    for task_id, eps in episodes.items():
        write_text(d / f"{safe_id(task_id)}.json", json.dumps([e.to_dict() for e in eps], ensure_ascii=False))


def read_records(out_dir: Path) -> dict[str, list[Episode]]:
    d = out_dir / "records-canonical"
    out = {}
    for p in sorted(d.glob("*.json")):
        eps = []
        for e in json.loads(p.read_text()):
            steps = [Step(**s) for s in e.pop("steps")]
            eps.append(Episode(steps=steps, **e))
        out[p.stem] = eps
    return out
