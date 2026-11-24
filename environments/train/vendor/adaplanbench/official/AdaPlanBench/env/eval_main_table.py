#!/usr/bin/env python3
                                                                   

                                                                               
                                                                              
                                                             
   

from __future__ import annotations

import argparse
import json
import math
import re
from copy import deepcopy
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Optional


_VALID_RESULT_STATUSES = {"success", "failed", "stopped", "error"}
_TEMPERATURE_FILTER_EXEMPT_MODELS = {"gpt-5", "gpt-5-mini", "gpt-5-nano"}
_FLOAT_TOLERANCE = 1e-9


@dataclass(frozen=True)
class RunRecord:
    model: str
    source_path: Path
    suffix: str
    metadata: dict[str, Any]
    queries: list[dict[str, Any]]
    scope: str
    hint: bool
    direct_elicit: bool


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute AdaPlanBench main-table metrics.")
    parser.add_argument("--result-dir", default="results")
    parser.add_argument("--model-list", nargs="*", default=None)
    parser.add_argument("--scope", default="both")
    parser.add_argument("--verbal", type=int, default=None)
    parser.add_argument("--iteration", type=int, default=None)
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--memory", choices=["on", "off"], default=None)
    parser.add_argument("--refine-rubrics", choices=["on", "off"], default=None)
    parser.add_argument("--hint", choices=["on", "off"], default=None)
    parser.add_argument("--direct-elicit", choices=["on", "off"], default=None)
    parser.add_argument("--trial-num", type=int, default=None)
    parser.add_argument(
        "--eval-repeated-violation-stop-limit",
        "--eval_repeated_violation_stop_limit",
        type=int,
        default=None,
        dest="eval_repeated_violation_stop_limit",
    )
    parser.add_argument(
        "--eval-no-new-violation-round-limit",
        "--eval_no_new_violation_round_limit",
        type=int,
        default=None,
        dest="eval_no_new_violation_round_limit",
    )
    parser.add_argument("--json-out", default=None, help='Output path, "false" to suppress, or omitted to print.')
    parser.add_argument("--latex-out", default=None, help='Output path, "false" to suppress.')
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    requested_models = parse_model_list(args.model_list)
    records = discover_run_records(Path(args.result_dir))
    records = filter_run_records(
        records,
        model_list=requested_models,
        temperature=args.temperature,
        scope=args.scope,
        verbal=args.verbal,
        iteration=args.iteration,
        memory=parse_optional_bool(args.memory),
        refine_rubrics=parse_optional_bool(args.refine_rubrics),
        hint=parse_optional_bool(args.hint),
        direct_elicit=parse_optional_bool(args.direct_elicit),
        trial_num=args.trial_num,
    )
    records = apply_eval_early_stop_override(
        records,
        repeated_violation_stop_limit=args.eval_repeated_violation_stop_limit,
        no_new_violation_round_limit=args.eval_no_new_violation_round_limit,
    )
    records = select_best_record_per_key(records)
    records = sort_records(records, requested_models=requested_models)
    if not records:
        raise FileNotFoundError("No result folders matched the provided filters.")

    evaluations = [evaluate_record(record) for record in records]

    json_out = parse_optional_output_path(args.json_out)
    if json_out is None and str(args.json_out).lower() != "false":
        print(json.dumps(evaluations, ensure_ascii=False, indent=2))
    elif json_out:
        write_text(json_out, json.dumps(evaluations, ensure_ascii=False, indent=2) + "\n")

    latex_out = parse_optional_output_path(args.latex_out)
    if latex_out:
        write_text(latex_out, build_latex_table(evaluations))

    return 0


def discover_run_records(result_dir: Path) -> list[RunRecord]:
    result_dir = Path(result_dir)
    candidates: list[Path] = []
    if (result_dir / "metadata.json").exists() and (result_dir / "queries").is_dir():
        candidates.append(result_dir)
    runs_dir = result_dir / "runs"
    if runs_dir.exists():
        candidates.extend(path for path in sorted(runs_dir.iterdir()) if path.is_dir())

    records: list[RunRecord] = []
    for path in candidates:
        if not (path / "metadata.json").exists() or not (path / "queries").is_dir():
            continue
        try:
            records.append(load_run_record(path))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return records


def load_run_record(path: Path) -> RunRecord:
    metadata = json.loads((path / "metadata.json").read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise ValueError(f"metadata must be a dict in {path}")

    queries = []
    query_paths = query_paths_from_index(path) or sorted((path / "queries").glob("*.json"))
    for query_path in query_paths:
        payload = json.loads(query_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"query payload must be a dict in {query_path}")
        queries.append(payload)

    suffix = path.name
    return RunRecord(
        model=str(metadata.get("model") or infer_model_from_suffix(suffix)),
        source_path=path,
        suffix=suffix,
        metadata=metadata,
        queries=queries,
        scope=infer_scope(metadata),
        hint=infer_bool_flag("hint", suffix, default=False),
        direct_elicit=infer_direct_elicit(metadata, suffix),
    )


def query_paths_from_index(path: Path) -> list[Path]:
    index_path = path / "index.jsonl"
    if not index_path.exists():
        return []
    out: list[Path] = []
    for line in index_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            continue
        rel_path = row.get("file")
        if not rel_path:
            continue
        query_path = path / str(rel_path)
        if query_path.exists():
            out.append(query_path)
    return out


def filter_run_records(
    records: Iterable[RunRecord],
    *,
    model_list: Optional[list[str]],
    temperature: Optional[float],
    scope: Optional[str],
    verbal: Optional[int],
    iteration: Optional[int],
    memory: Optional[bool],
    refine_rubrics: Optional[bool],
    hint: Optional[bool],
    direct_elicit: Optional[bool],
    trial_num: Optional[int],
) -> list[RunRecord]:
    out: list[RunRecord] = []
    for record in records:
        meta = record.metadata
        if model_list is not None and record.model not in model_list:
            continue
        if (
            temperature is not None
            and record.model not in _TEMPERATURE_FILTER_EXEMPT_MODELS
            and not float_matches(meta.get("model_temperature"), temperature)
        ):
            continue
        if scope is not None and record.scope != scope:
            continue
        if verbal is not None and metadata_int(meta, "ban_verbal_sample_num", default=-1) != verbal:
            continue
        if iteration is not None and metadata_int(meta, "ban_iterative_sample_num", default=-1) != iteration:
            continue
        if memory is not None and bool(meta.get("memory")) != memory:
            continue
        if refine_rubrics is not None and bool(meta.get("refine_rubrics")) != refine_rubrics:
            continue
        if hint is not None and record.hint != hint:
            continue
        if direct_elicit is not None and record.direct_elicit != direct_elicit:
            continue
        if trial_num is not None and metadata_int(meta, "trial_num", default=-1) != trial_num:
            continue
        out.append(record)
    return out


def apply_eval_early_stop_override(
    records: Iterable[RunRecord],
    *,
    repeated_violation_stop_limit: Optional[int],
    no_new_violation_round_limit: Optional[int],
) -> list[RunRecord]:
    if repeated_violation_stop_limit is None and no_new_violation_round_limit is None:
        return list(records)
    if repeated_violation_stop_limit is not None and repeated_violation_stop_limit < 1:
        raise ValueError("--eval-repeated-violation-stop-limit must be >= 1")
    if no_new_violation_round_limit is not None and no_new_violation_round_limit < 1:
        raise ValueError("--eval-no-new-violation-round-limit must be >= 1")

    out: list[RunRecord] = []
    for record in records:
        queries = [
            apply_eval_early_stop_to_query(
                query,
                repeated_violation_stop_limit=repeated_violation_stop_limit,
                no_new_violation_round_limit=no_new_violation_round_limit,
            )
            for query in record.queries
        ]
        metadata = dict(record.metadata)
        metadata.update(
            build_eval_outcome_stats(
                queries,
                repeated_violation_stop_limit=repeated_violation_stop_limit,
                no_new_violation_round_limit=no_new_violation_round_limit,
            )
        )
        out.append(replace(record, metadata=metadata, queries=queries))
    return out


def apply_eval_early_stop_to_query(
    query: dict[str, Any],
    *,
    repeated_violation_stop_limit: Optional[int],
    no_new_violation_round_limit: Optional[int],
) -> dict[str, Any]:
    if get_query_status(query) not in {"success", "failed", "stopped"}:
        return query
    if is_judge_error(query):
        return query

    stop = find_eval_early_stop_turn(
        query,
        repeated_violation_stop_limit=repeated_violation_stop_limit,
        no_new_violation_round_limit=no_new_violation_round_limit,
    )
    if stop is None:
        return query

    stop_turn, stop_reason, streak = stop
    current_turns = get_turn_count(query)
    current_stop_reason = get_stop_reason(query)
    if get_query_status(query) == "stopped" and current_stop_reason.startswith("early_stop") and current_turns <= stop_turn:
        return query

    updated = deepcopy(query)
    trajectory = get_trajectory(updated)
    updated["trajectory"] = trajectory[:stop_turn]
    updated["no_new_violation_streak"] = int(streak)
    if updated["trajectory"]:
        snapshot = updated["trajectory"][-1].get("counter_snapshot")
        if isinstance(snapshot, dict):
            updated["tracker"] = deepcopy(snapshot)
    updated["result"] = {
        "status": "stopped",
        "stop_reason": stop_reason,
        "turns": int(stop_turn),
    }
    return updated


def find_eval_early_stop_turn(
    query: dict[str, Any],
    *,
    repeated_violation_stop_limit: Optional[int],
    no_new_violation_round_limit: Optional[int],
) -> Optional[tuple[int, str, int]]:
    no_new_streak = 0
    for index, turn in enumerate(get_trajectory(query), start=1):
        if not isinstance(turn, dict):
            continue
        newly_seen = turn_newly_seen_items(turn)
        no_new_streak = 0 if newly_seen else no_new_streak + 1

        if repeated_violation_stop_limit is not None:
            tools_total, prefs_total = turn_disclosed_violation_totals(turn)
            if tools_total >= repeated_violation_stop_limit:
                return index, f"early_stop due to repeated violation {tools_total} (tool constraint)", no_new_streak
            if prefs_total >= repeated_violation_stop_limit:
                return index, f"early_stop due to repeated violation {prefs_total} (user prefs)", no_new_streak

        if no_new_violation_round_limit is not None and no_new_streak >= no_new_violation_round_limit:
            return (
                index,
                "early_stop due to no new tool/prefs violations for "
                f"{no_new_streak} consecutive turns",
                no_new_streak,
            )
    return None


def evaluate_record(record: RunRecord) -> dict[str, Any]:
    metrics = {}
    metrics.update(compute_accuracy(record.queries))
    metrics.update(compute_repeated_violation_rate(record.queries, dimension="tools"))
    metrics.update(compute_repeated_violation_rate(record.queries, dimension="prefs"))
    metrics.update(compute_early_stop_rate(record.metadata, record.queries))
    metrics.update(compute_average_turns(record.queries))
    metrics.update(compute_violation_turn_ratio(record.queries, dimension="tools"))
    metrics.update(compute_violation_turn_ratio(record.queries, dimension="prefs"))
    metrics.update(compute_violations_per_turn(record.queries, dimension="tools"))
    metrics.update(compute_violations_per_turn(record.queries, dimension="prefs"))

    return {
        "model": record.model,
        "source_file": str(record.source_path),
        "source_kind": "result_folder",
        "scope": record.scope,
        "temperature": record.metadata.get("model_temperature"),
        "verbal": record.metadata.get("ban_verbal_sample_num"),
        "iteration": record.metadata.get("ban_iterative_sample_num"),
        "memory": record.metadata.get("memory"),
        "refine_rubrics": record.metadata.get("refine_rubrics"),
        "hint": record.hint,
        "direct_elicit": record.direct_elicit,
        "trial_num": record.metadata.get("trial_num"),
        "total_query_count": len(record.queries),
        "unfinished_query_count": count_unfinished_queries(record.queries),
        "judge_error_query_count": count_judge_error_queries(record.queries),
        "metrics": metrics,
    }


def compute_accuracy(queries: list[dict[str, Any]]) -> dict[str, Any]:
    valid_queries = get_valid_queries(queries)
    return {
        "accuracy": compute_average(1.0 if is_success_query(query) else 0.0 for query in valid_queries),
        "valid_query_count": len(valid_queries),
    }


def compute_early_stop_rate(metadata: dict[str, Any], queries: list[dict[str, Any]]) -> dict[str, Any]:
    valid_queries = get_valid_queries(queries)
    early_stop_count = sum(1 for query in valid_queries if get_stop_reason(query).startswith("early_stop"))
    rate = None if not valid_queries else float(early_stop_count) / float(len(valid_queries))
    return {
        "early_stop_rate": rate,
        "early_stopped_query_count": int(early_stop_count),
        "metadata_early_stopped_query_count": int(metadata.get("early_stopped_query_count") or 0),
    }


def compute_average_turns(queries: list[dict[str, Any]]) -> dict[str, Any]:
    valid_queries = get_valid_queries(queries)
    return {
        "average_turns": compute_average(get_turn_count(query) for query in valid_queries),
        "valid_query_count": len(valid_queries),
    }


def compute_repeated_violation_rate(queries: list[dict[str, Any]], *, dimension: str) -> dict[str, Any]:
    valid_queries = get_valid_queries(queries)
    key = "objective_repeated_violation_rate" if dimension == "tools" else "subjective_repeated_violation_rate"
    return {
        key: compute_average(get_dimension_counter_total(query, dimension) for query in valid_queries),
        "valid_query_count": len(valid_queries),
    }


def compute_violation_turn_ratio(queries: list[dict[str, Any]], *, dimension: str) -> dict[str, Any]:
    valid_queries = get_valid_queries(queries)
    values = []
    for query in valid_queries:
        turn_count = get_turn_count(query)
        if turn_count > 0:
            values.append(count_turns_with_violation(query, dimension) / turn_count)
    key = "objective_violation_turn_ratio" if dimension == "tools" else "subjective_violation_turn_ratio"
    return {key: compute_average(values), "valid_query_count": len(valid_queries)}


def compute_violations_per_turn(queries: list[dict[str, Any]], *, dimension: str) -> dict[str, Any]:
    valid_queries = get_valid_queries(queries)
    values = []
    for query in valid_queries:
        turn_count = get_turn_count(query)
        if turn_count > 0:
            values.append(count_total_turn_violations(query, dimension) / turn_count)
    key = "objective_violations_per_turn" if dimension == "tools" else "subjective_violations_per_turn"
    return {key: compute_average(values), "valid_query_count": len(valid_queries)}


def build_latex_table(evaluations: Iterable[dict[str, Any]]) -> str:
    evaluations = list(evaluations)
    metric_specs = [
        ("accuracy", r"Acc. (\%) $\uparrow$", "up"),
        ("valid_plan_rate", r"VPR (\%) $\uparrow$", "up"),
        ("average_turns", "Avg Turns", None),
        ("objective_repeated_violation_rate", r"AWRV $\downarrow$", "down"),
        ("subjective_repeated_violation_rate", r"AURV $\downarrow$", "down"),
        ("objective_violations_per_turn", "ATWC", "up"),
        ("subjective_violations_per_turn", "ATUC", "up"),
    ]
    ranking = {key: compute_ranking(evaluations, key, direction) for key, _, direction in metric_specs}
    lines = [
        "% Requires \\usepackage{booktabs,multirow}",
        "\\begin{table*}[t]",
        "\\centering",
        "\\resizebox{\\linewidth}{!}{",
        "\\begin{tabular}{lccccccc}",
        "\\toprule",
        "\\multirow{2}{*}{Model} & \\multicolumn{3}{c}{Outcome} & \\multicolumn{2}{c}{Constraint Failure} & \\multicolumn{2}{c}{Constraint Elicitation} \\\\",
        "\\cmidrule(lr){2-4}\\cmidrule(lr){5-6}\\cmidrule(lr){7-8}",
        " & " + " & ".join(label for _, label, _ in metric_specs) + " \\\\",
        "\\midrule",
    ]
    for row_index, evaluation in enumerate(evaluations):
        row = [escape_latex(format_model_display_name(str(evaluation.get("model") or "")))]
        metrics = evaluation.get("metrics") or {}
        for metric_key, _, _ in metric_specs:
            value = get_latex_metric_value(metrics, metric_key)
            row.append(format_metric_value(value, metric_key, ranking[metric_key], row_index))
        lines.append(" & ".join(row) + " \\\\")
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "}",
            "\\caption{AdaPlanBench main-table evaluation results.}",
            "\\label{tab:main-table}",
            "\\end{table*}",
        ]
    )
    return "\n".join(lines) + "\n"


def select_best_record_per_key(records: Iterable[RunRecord]) -> list[RunRecord]:
    best_by_key: dict[tuple[Any, ...], RunRecord] = {}
    for record in records:
        key = (
            record.model,
            record.scope,
            record.metadata.get("model_temperature"),
            record.metadata.get("ban_verbal_sample_num"),
            record.metadata.get("ban_iterative_sample_num"),
            bool(record.metadata.get("memory")),
            bool(record.metadata.get("refine_rubrics")),
            record.hint,
            record.direct_elicit,
            record.metadata.get("trial_num"),
        )
        current = best_by_key.get(key)
        if current is None or record_score(record) > record_score(current):
            best_by_key[key] = record
    return list(best_by_key.values())


def record_score(record: RunRecord) -> tuple[Any, ...]:
    finished_count = len(get_finished_queries(record.queries))
    valid_count = len(get_valid_queries(record.queries))
    unfinished_count = count_unfinished_queries(record.queries)
    remaining = int(record.metadata.get("remaining_query_count") or unfinished_count)
    return (finished_count, valid_count, bool(record.metadata.get("progress_complete")), -remaining, str(record.source_path))


def sort_records(records: Iterable[RunRecord], *, requested_models: Optional[list[str]]) -> list[RunRecord]:
    model_order = {model: index for index, model in enumerate(requested_models or [])}
    return sorted(
        records,
        key=lambda record: (
            model_order.get(record.model, len(model_order)),
            record.model,
            metadata_int(record.metadata, "ban_iterative_sample_num", default=-1),
            record.suffix,
        ),
    )


def build_eval_outcome_stats(
    queries: list[dict[str, Any]],
    *,
    repeated_violation_stop_limit: Optional[int],
    no_new_violation_round_limit: Optional[int],
) -> dict[str, Any]:
    success_count = 0
    failed_count = 0
    early_stopped_count = 0
    finished_turns: list[int] = []
    remaining_query_count = 0
    for query in queries:
        status = get_query_status(query)
        turns = get_turn_count(query)
        stop_reason = get_stop_reason(query)
        if status not in _VALID_RESULT_STATUSES:
            remaining_query_count += 1
            continue
        finished_turns.append(turns)
        if status == "success":
            success_count += 1
        elif status == "failed":
            failed_count += 1
        elif status == "stopped" and stop_reason.startswith("early_stop"):
            early_stopped_count += 1
    return {
        "eval_early_stop_override": True,
        "eval_repeated_violation_stop_limit": repeated_violation_stop_limit,
        "eval_no_new_violation_round_limit": no_new_violation_round_limit,
        "finished_query_count": len(finished_turns),
        "remaining_query_count": remaining_query_count,
        "avg_turns_finished_queries": compute_average(finished_turns) or 0.0,
        "success_query_count": success_count,
        "failed_query_count": failed_count,
        "early_stopped_query_count": early_stopped_count,
    }


def get_finished_queries(queries: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [query for query in queries if get_query_status(query) in _VALID_RESULT_STATUSES]


def get_valid_queries(queries: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [query for query in get_finished_queries(queries) if not is_judge_error(query)]


def count_unfinished_queries(queries: Iterable[dict[str, Any]]) -> int:
    return sum(1 for query in queries if get_query_status(query) not in _VALID_RESULT_STATUSES)


def count_judge_error_queries(queries: Iterable[dict[str, Any]]) -> int:
    return sum(1 for query in get_finished_queries(queries) if is_judge_error(query))


def is_success_query(query: dict[str, Any]) -> bool:
    return get_query_status(query) == "success"


def is_judge_error(query: dict[str, Any]) -> bool:
    stop_reason = get_stop_reason(query)
    if stop_reason.endswith("_judge_error"):
        return True
    judge_side = get_last_turn(query).get("judge_side") or {}
    if isinstance(judge_side, dict):
        for stage_result in judge_side.values():
            if isinstance(stage_result, dict) and str(stage_result.get("status") or "") == "error":
                return True
    return False


def get_query_status(query: dict[str, Any]) -> str:
    return str((query.get("result") or {}).get("status") or "")


def get_stop_reason(query: dict[str, Any]) -> str:
    return str((query.get("result") or {}).get("stop_reason") or "")


def get_turn_count(query: dict[str, Any]) -> int:
    result = query.get("result") or {}
    if result.get("turns") is not None:
        return int(result["turns"])
    return len(get_trajectory(query))


def get_trajectory(query: dict[str, Any]) -> list[dict[str, Any]]:
    trajectory = query.get("trajectory") or []
    return trajectory if isinstance(trajectory, list) else []


def get_last_turn(query: dict[str, Any]) -> dict[str, Any]:
    trajectory = get_trajectory(query)
    return trajectory[-1] if trajectory and isinstance(trajectory[-1], dict) else {}


def get_tracker_state(query: dict[str, Any]) -> dict[str, Any]:
    tracker = query.get("tracker") or {}
    return tracker if isinstance(tracker, dict) else {}


def get_dimension_counter_total(query: dict[str, Any], dimension: str) -> int:
    counters = get_tracker_state(query).get(dimension_key(dimension)) or {}
    if not isinstance(counters, dict):
        return 0
    total = 0
    for payload in counters.values():
        if isinstance(payload, dict):
            total += int(payload.get("disclosed_violations", 0) or 0)
    return total


def count_turns_with_violation(query: dict[str, Any], dimension: str) -> int:
    key = turn_violation_key(dimension)
    count = 0
    for turn in get_trajectory(query):
        if isinstance(turn, dict) and isinstance(turn.get(key), list) and turn[key]:
            count += 1
    return count


def count_total_turn_violations(query: dict[str, Any], dimension: str) -> int:
    key = turn_violation_key(dimension)
    total = 0
    for turn in get_trajectory(query):
        items = turn.get(key) if isinstance(turn, dict) else None
        if isinstance(items, list):
            total += len(items)
    return total


def turn_newly_seen_items(turn: dict[str, Any]) -> list[Any]:
    disclosed = turn.get("disclosed_check") or {}
    if isinstance(disclosed, dict) and isinstance(disclosed.get("newly_seen"), list):
        return disclosed["newly_seen"]
    out: list[Any] = []
    by_dimension = turn.get("disclosed_check_by_dimension") or {}
    if isinstance(by_dimension, dict):
        for payload in by_dimension.values():
            if isinstance(payload, dict) and isinstance(payload.get("newly_seen"), list):
                out.extend(payload["newly_seen"])
    return out


def turn_disclosed_violation_totals(turn: dict[str, Any]) -> tuple[int, int]:
    snapshot = turn.get("counter_snapshot") or {}
    if not isinstance(snapshot, dict):
        return 0, 0
    return counter_snapshot_total(snapshot.get("tools")), counter_snapshot_total(snapshot.get("prefs"))


def counter_snapshot_total(counters: Any) -> int:
    if not isinstance(counters, dict):
        return 0
    total = 0
    for payload in counters.values():
        if isinstance(payload, dict):
            total += int(payload.get("disclosed_violations", 0) or 0)
    return total


def compute_average(values: Iterable[float]) -> Optional[float]:
    values_list = list(values)
    if not values_list:
        return None
    return float(sum(values_list)) / float(len(values_list))


def get_latex_metric_value(metrics: dict[str, Any], metric_key: str) -> Any:
    if metric_key == "valid_plan_rate":
        early_stop_rate = metrics.get("early_stop_rate")
        return None if early_stop_rate is None else 1.0 - float(early_stop_rate)
    return metrics.get(metric_key)


def format_metric_value(
    value: Any,
    metric_key: str,
    ranking: Optional[dict[str, set[int]]],
    row_index: int,
) -> str:
    if value is None:
        rendered = "--"
    elif isinstance(value, int):
        rendered = str(value)
    elif isinstance(value, float):
        rendered = f"{value * 100.0:.2f}" if metric_key in {"accuracy", "valid_plan_rate"} else f"{value:.3f}"
    else:
        rendered = escape_latex(str(value))
    if ranking is None:
        return rendered
    if row_index in ranking["best"]:
        return f"\\textbf{{{rendered}}}"
    if row_index in ranking["second"]:
        return f"\\underline{{{rendered}}}"
    return rendered


def compute_ranking(evaluations: list[dict[str, Any]], metric_key: str, direction: Optional[str]) -> Optional[dict[str, set[int]]]:
    if direction is None:
        return None
    indexed_values = []
    for row_index, evaluation in enumerate(evaluations):
        value = get_latex_metric_value(evaluation.get("metrics") or {}, metric_key)
        if value is None:
            continue
        numeric = float(value)
        if not math.isnan(numeric):
            indexed_values.append((row_index, numeric))
    if not indexed_values:
        return {"best": set(), "second": set()}
    ordered = sorted({value for _, value in indexed_values}, reverse=(direction == "up"))
    best = ordered[0]
    second = ordered[1] if len(ordered) > 1 else None
    return {
        "best": {row_index for row_index, value in indexed_values if value == best},
        "second": set() if second is None else {row_index for row_index, value in indexed_values if value == second},
    }


def format_model_display_name(model: str) -> str:
    replacements = {
        "gpt-5": "GPT-5",
        "gpt-5-mini": "GPT-5-Mini",
        "gpt-5-nano": "GPT-5-Nano",
        "gemini-3-flash": "Gemini-3-Flash",
        "gemini-3.1-pro": "Gemini-3.1-Pro",
    }
    return replacements.get(model, model)


def parse_model_list(raw_values: Optional[Iterable[str]]) -> Optional[list[str]]:
    if not raw_values:
        return None
    models: list[str] = []
    for raw in raw_values:
        for part in str(raw).split(","):
            item = part.split(":", 1)[0].strip()
            if item:
                models.append(item)
    return models or None


def parse_optional_bool(raw: Optional[str]) -> Optional[bool]:
    if raw is None:
        return None
    text = str(raw).strip().lower()
    if text in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise ValueError(f"Cannot parse bool from: {raw}")


def parse_optional_output_path(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() in {"false", "none", "null", "no", "off"}:
        return None
    return text


def infer_scope(metadata: dict[str, Any]) -> str:
    ban_only = metadata.get("ban_only")
    if ban_only in (None, "", "null"):
        return "both"
    return str(ban_only)


def infer_model_from_suffix(suffix: str) -> str:
    return suffix.split("_scope_", 1)[0]


def infer_direct_elicit(metadata: dict[str, Any], suffix: str) -> bool:
    value = metadata.get("direct_elicit")
    if value is not None:
        return bool(value)
    return infer_bool_flag("direct-elicit", suffix, default=False)


def infer_bool_flag(flag_name: str, suffix: str, *, default: bool) -> bool:
    match = re.search(rf"(?:^|_){re.escape(flag_name)}_(on|off)(?:_|$)", suffix)
    if not match:
        return default
    return match.group(1) == "on"


def metadata_int(metadata: dict[str, Any], key: str, *, default: int) -> int:
    value = metadata.get(key)
    if value is None:
        return default
    return int(value)


def float_matches(left: Any, right: float) -> bool:
    if left is None:
        return False
    return abs(float(left) - float(right)) <= _FLOAT_TOLERANCE


def dimension_key(dimension: str) -> str:
    if dimension in {"tools", "prefs"}:
        return dimension
    raise ValueError(f"Unsupported dimension: {dimension}")


def turn_violation_key(dimension: str) -> str:
    if dimension == "tools":
        return "violated_env_items"
    if dimension == "prefs":
        return "violated_pref_items"
    raise ValueError(f"Unsupported dimension: {dimension}")


def escape_latex(text: str) -> str:
    replacements = {
        "\\": "\\textbackslash{}",
        "&": "\\&",
        "%": "\\%",
        "$": "\\$",
        "#": "\\#",
        "_": "\\_",
        "{": "\\{",
        "}": "\\}",
        "~": "\\textasciitilde{}",
        "^": "\\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def write_text(path: str, text: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
