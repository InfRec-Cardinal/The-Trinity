                                                                                   
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
HARNESS = ROOT / "ARC-AGI-3-Agents"
PYTHON = HARNESS / ".venv" / "bin" / "python"
RUN_ROOT = ROOT / "fallback_matrix_runs"


def masked(board: np.ndarray) -> np.ndarray:
    result = board.copy()
    result[:2] = 0
    result[-2:] = 0
    result[:, :2] = 0
    result[:, -2:] = 0
    return result


def parse_recording(path: Path) -> dict:
    frames = []
    for line in path.open():
        data = json.loads(line).get("data", {})
        if "frame" in data and "levels_completed" in data:
            frames.append(data)
    if not frames:
        raise ValueError(f"No frames in {path}")
    noops = 0
    first_clear = None
    for index in range(1, len(frames)):
        before = np.asarray(frames[index - 1]["frame"])[-1]
        after = np.asarray(frames[index]["frame"])[-1]
        if before.shape == after.shape and np.count_nonzero(masked(before) != masked(after)) == 0:
            noops += 1
        if first_clear is None and int(frames[index].get("levels_completed") or 0) > 0:
            first_clear = index
    final = frames[-1]
    levels = int(final.get("levels_completed") or 0)
    state = str(final.get("state", "UNKNOWN"))
    actions = len(frames)
    return {
        "levels_cleared": levels,
        "no_op_rate": noops / max(actions - 1, 1),
        "game_over_zero": int(state == "GAME_OVER" and levels == 0),
        "actions_to_first_clear": first_clear if first_clear is not None else "",
        "total_actions": actions,
        "final_state": state,
        "recording": str(path),
    }


def newest_recordings(agent: str, started: float) -> list[Path]:
    recordings = HARNESS / "recordings"
    return sorted(
        path
        for path in recordings.glob(f"*.{agent}.*.recording.jsonl")
        if path.stat().st_mtime >= started - 1
    )


def run_batch(agent: str, games: list[str], budget: int, run: int, variant: str) -> list[dict]:
    output_dir = RUN_ROOT / variant / agent / f"budget_{budget}" / f"run_{run}"
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "run.log"
    env = os.environ.copy()
    env.update(
        {
            "FALLBACK_MAX_ACTIONS": str(budget),
            "MPLCONFIGDIR": "/tmp/matplotlib",
            "RECORDINGS_DIR": str(HARNESS / "recordings"),
        }
    )
    for key in ("FB2_NOOP_MEMORY", "FB2_DEADLY_MEMORY", "FB2_CANDIDATE_ORDERING", "FB2_CYCLE_GUARD"):
        env.pop(key, None)
    if variant != "full":
        disabled = variant.removeprefix("no_").upper()
        env[f"FB2_{disabled}"] = "0"
    command = [
        str(PYTHON),
        "main.py",
        f"--agent={agent}",
        f"--game={','.join(games)}",
        f"--tags=matrix,{variant},budget-{budget},run-{run}",
    ]
    started = time.time()
    with log_path.open("w") as log:
        result = subprocess.run(command, cwd=HARNESS, env=env, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"Batch failed: {log_path}")
    newest_by_game: dict[str, Path] = {}
    for recording in newest_recordings(agent, started):
        game = recording.name.split("-", 1)[0]
        if game not in games:
            continue
        previous = newest_by_game.get(game)
        if previous is None or recording.stat().st_mtime > previous.stat().st_mtime:
            newest_by_game[game] = recording
    rows = []
    for game, recording in sorted(newest_by_game.items()):
        metrics = parse_recording(recording)
        rows.append(
            {
                "agent": agent,
                "variant": variant,
                "budget": budget,
                "run": run,
                "game": game,
                **metrics,
            }
        )
    found = {row["game"] for row in rows}
    missing = set(games) - found
    if missing:
        raise RuntimeError(f"Missing recordings for {sorted(missing)}; see {log_path}")
    return rows


def write_rows(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", required=True)
    parser.add_argument("--games", required=True)
    parser.add_argument("--budgets", default="600,2000")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--variant", default="full")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    games = args.games.split(",")
    rows = []
    for budget in map(int, args.budgets.split(",")):
        for run in range(1, args.runs + 1):
            rows.extend(run_batch(args.agent, games, budget, run, args.variant))
            write_rows(rows, args.out)
            print(f"completed {args.agent} {args.variant} budget={budget} run={run}", flush=True)


if __name__ == "__main__":
    main()
