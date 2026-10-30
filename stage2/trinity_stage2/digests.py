from __future__ import annotations

import json
from pathlib import Path

from .records import Episode
from .media import observation_text
from .storage import write_text

DEFAULT_OBS_CHARS, DEFAULT_ACT_CHARS = 400, 200


def cut(text: str, n: int) -> str:
    text = str(text).replace("\n", " ⏎ ")
    if n <= 0 or len(text) <= n:
        return text
    return text[: n * 2 // 3] + f" ...(+{len(text) - n} chars)... " + text[-n // 3:]


def new_part(prev: str, cur: str) -> str:
    if prev and len(prev) > 200:
        i, m = 0, min(len(prev), len(cur))
        while i < m and prev[i] == cur[i]:
            i += 1
        if i > 0.6 * len(prev):
            return "[+] " + cur[i:]
    return cur


def end_marker(t: dict | None) -> str:
    if not t or not t.get("ended"):
        return ""
    return f" => END outcome={t.get('outcome')} score={t.get('score')} reason={t.get('reason')}"


def digest_lines(task_id: str, episodes: list[Episode], obs_chars: int, act_chars: int) -> list[str]:
    lines = [f"# Digest: {task_id}", "",
             "One line per step: `s<step>` action -> end marker | observation (`[+]` = only the text appended to the previous "
             "observation; long texts cut in the middle). Image references are shown; read_step returns the actual images before and after the action.", ""]
    for e in episodes:
        lines += ["", f"## {e.episodeId} | {e.configuration} | **{e.outcome}** score={e.score} reason={e.reason} steps={e.step_count}", ""]
        lines.append("s0 INIT " + cut(observation_text(e.initialObservation), max(obs_chars, 2500) if obs_chars else 0))
        prev = observation_text(e.initialObservation)
        for s in e.steps:
            action = json.dumps(s.action, ensure_ascii=False) if not isinstance(s.action, str) else s.action
            lines.append(f"s{s.index} {cut(action, act_chars)}{end_marker(s.terminal)} | {cut(new_part(prev, observation_text(s.observation)), obs_chars)}")
            prev = observation_text(s.observation)
    return lines


def stats_rows(episodes: list[Episode]) -> list[dict]:
    return [{"episode": e.episodeId, "configuration": e.configuration, "outcome": e.outcome, "score": e.score, "reason": e.reason, "steps": e.step_count} for e in episodes]


def write_digests(records: dict[str, list[Episode]], out_dir: Path, limits: dict[str, tuple[int, int]] | None = None) -> None:
    (out_dir / "digests").mkdir(parents=True, exist_ok=True)
    (out_dir / "stats").mkdir(parents=True, exist_ok=True)
    for task_id, episodes in records.items():
        obs, act = (limits or {}).get(task_id, (DEFAULT_OBS_CHARS, DEFAULT_ACT_CHARS))
        write_text(out_dir / "digests" / f"{task_id}.txt", "\n".join(digest_lines(task_id, episodes, obs, act)) + "\n")
        write_text(out_dir / "digests" / f"{task_id}.full.txt", "\n".join(digest_lines(task_id, episodes, 0, 0)) + "\n")
        write_text(out_dir / "stats" / f"{task_id}.json", json.dumps(stats_rows(episodes), indent=0))
