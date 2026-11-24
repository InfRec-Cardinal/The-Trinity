                 

                                          
                        
                                                 
                                            
                                                                                        
   

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from env.construction.cons_utils.reasoning import normalize_reasoning_effort_map
from .run_utils.llm import load_dotenv_if_present
from .run_utils.runner import Runner, RunnerConfig


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "env" / "run_config.yaml"
DEFAULT_MODEL_METADATA = PROJECT_ROOT / "env" / "run_utils" / "model_metadata.yaml"
DEFAULT_DOTENV = PROJECT_ROOT / "env" / ".env"

try:
    import yaml
except Exception:                    
    yaml = None


BOOL_ACTION = argparse.BooleanOptionalAction if hasattr(argparse, "BooleanOptionalAction") else None


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Runtime evaluator for robustness benchmark.")

    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to runtime config YAML/JSON. CLI args override config values.",
    )

    parser.add_argument("--query_path", default=None)
    parser.add_argument("--out", default=None, help="Output directory for runtime files")
    parser.add_argument("--result_out", default=None)
    parser.add_argument("--domain", default=None)
    parser.add_argument("--source", default=None)
    parser.add_argument("--ban_only", default=None, help="Optional runtime ban scope: tools | prefs")
    parser.add_argument(
        "--rubrics_refine_continue_from",
        default=None,
        help="Optional base output directory of an older run to copy into {out}/rubrics_refine before continuing failed queries.",
    )

    parser.add_argument("--model", default=None)
    parser.add_argument("--model_max_tokens", type=int, default=None)
    parser.add_argument("--model_temperature", type=float, default=None)

    parser.add_argument("--judge_LLM_list", default=None)
    parser.add_argument("--judge_merge_mode", default=None)
    parser.add_argument("--tolerant_fail_judge_nums", type=int, default=None)
    parser.add_argument("--tools_judge_LLM_list", default=None)
    parser.add_argument("--prefs_judge_LLM_list", default=None)
    parser.add_argument("--rubrics_judge_LLM_list", default=None)
    parser.add_argument("--tools_judge_merge_mode", default=None)
    parser.add_argument("--prefs_judge_merge_mode", default=None)
    parser.add_argument("--rubrics_judge_merge_mode", default=None)
    parser.add_argument("--tools_tolerant_fail_judge_nums", type=int, default=None)
    parser.add_argument("--prefs_tolerant_fail_judge_nums", type=int, default=None)
    parser.add_argument("--rubrics_tolerant_fail_judge_nums", type=int, default=None)
    parser.add_argument("--rubrics_score_merge_mode", default=None)
    parser.add_argument("--rubrics_pass_mode", default=None)
    parser.add_argument("--rubrics_pass_threshold", type=float, default=None)
    parser.add_argument("--rubrics_feedback_threshold", type=float, default=None)
    parser.add_argument("--response_dimension", default=None)
    parser.add_argument("--ordered_elicit", default=None)
    parser.add_argument("--judge_max_tokens", type=int, default=None)
    parser.add_argument("--judge_temperature", type=float, default=None)
    parser.add_argument("--judge_reasoning_effort", default=None)
    parser.add_argument("--judge_reasoning_effort_by_model_json", default=None)

    parser.add_argument("--gen_LLM", default=None)
    parser.add_argument("--gen_max_tokens", type=int, default=None)
    parser.add_argument("--gen_temperature", type=float, default=None)

    parser.add_argument("--merge_LLM", default=None)
    parser.add_argument("--check_LLM", default=None)
    parser.add_argument("--merge_max_tokens", type=int, default=None)
    parser.add_argument("--merge_temperature", type=float, default=None)
    parser.add_argument("--merge_LLM_temperature", type=float, default=None)
    parser.add_argument("--check_LLM_temperature", type=float, default=None)
    parser.add_argument("--merge_timeout_s", type=int, default=None)
    parser.add_argument("--check_timeout_s", type=int, default=None)
    parser.add_argument("--llm_timeout_s", type=int, default=None)
    parser.add_argument("--llm_max_retries", type=int, default=None)
    parser.add_argument("--llm_retry_backoff_s", type=float, default=None)

    parser.add_argument("--max_concurrency", type=int, default=None)
    parser.add_argument("--max_turns", type=int, default=None)
    parser.add_argument("--max_resume_attempts", type=int, default=None)

    parser.add_argument("--ban_sample_num", type=int, default=None)
    parser.add_argument("--ban_iterative_sample_num", type=int, default=None)
    parser.add_argument("--ban_verbal_sample_num", type=int, default=None)

    if BOOL_ACTION is not None:
        parser.add_argument("--full_evidence", action=BOOL_ACTION, default=None)
        parser.add_argument("--refine_rubrics", action=BOOL_ACTION, default=None)
        parser.add_argument("--memory", action=BOOL_ACTION, default=None)
        parser.add_argument("--direct_elicit", action=BOOL_ACTION, default=None)
        parser.add_argument("--timer", action=BOOL_ACTION, default=None)
        parser.add_argument("--debug", action=BOOL_ACTION, default=None)
        parser.add_argument("--fail_fast", action=BOOL_ACTION, default=None)
        parser.add_argument("--truncate_history", action=BOOL_ACTION, default=None)
        parser.add_argument("--repetition_penalty_response", action=BOOL_ACTION, default=None)
        parser.add_argument("--early_stop", action=BOOL_ACTION, default=None)
    else:                    
        parser.add_argument("--full_evidence", action="store_true")
        parser.add_argument("--refine_rubrics", action="store_true")
        parser.add_argument("--memory", action="store_true")
        parser.add_argument("--direct_elicit", action="store_true")
        parser.add_argument("--timer", action="store_true")
        parser.add_argument("--debug", action="store_true")
        parser.add_argument("--fail_fast", action="store_true")
        parser.add_argument("--truncate_history", action="store_true")
        parser.add_argument("--repetition_penalty_response", action="store_true")
        parser.add_argument("--early_stop", action="store_true")

    parser.add_argument("--stop_limit", type=int, default=None)
    parser.add_argument("--early_stop_mode", default=None)
    parser.add_argument("--repeated_violation_stop_limit", type=int, default=None)
    parser.add_argument("--no_new_violation_round_limit", type=int, default=None)
    parser.add_argument("--rubrics_refine_max_turns", type=int, default=None)
    parser.add_argument("--debug_out_dir", default=None)
    parser.add_argument("--retry_num", type=int, default=None)
    parser.add_argument("--fail_threshold", type=float, default=None)
    parser.add_argument("--model_metadata", default=None)
    parser.add_argument("--dotenv", default=None)
    parser.add_argument("--num_ckpts", type=int, default=None)
    parser.add_argument("--trial_num", type=int, default=None)

    return parser


def _parse_yaml_scalar(raw: str) -> object:
    text = raw.strip()
    if text == "":
        return ""
    low = text.lower()
    if low in {"null", "~"}:
        return None
    if low in {"true", "yes"}:
        return True
    if low in {"false", "no"}:
        return False
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        return text[1:-1]
    try:
        if any(ch in text for ch in (".", "e", "E")):
            return float(text)
        return int(text)
    except ValueError:
        return text


def _load_simple_yaml_map(text: str, path: Path) -> Dict[str, object]:
    out: Dict[str, object] = {}
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"Invalid YAML line {lineno} in {path}: {raw_line}")
        key, val = line.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Empty YAML key at line {lineno} in {path}")
        out[key] = _parse_yaml_scalar(val)
    return out


def _load_config(path: Path) -> Dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.loads(text)
    else:
        if yaml is not None:
            data = yaml.safe_load(text)
        else:
            data = _load_simple_yaml_map(text, path)

    if not isinstance(data, dict):
        raise ValueError(f"Config must be a map/object: {path}")
    return data


def _pick(cli_value: object, cfg: Dict[str, object], key: str, default: object = None) -> object:
    if cli_value is not None:
        return cli_value
    if key in cfg and cfg[key] is not None:
        return cfg[key]
    return default


def _as_bool(val: object) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    text = str(val).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    raise ValueError(f"Cannot parse bool from: {val}")


def _require(value: object, name: str) -> object:
    if value is None:
        raise ValueError(f"--{name} is required (CLI or config)")
    if isinstance(value, str) and not value.strip():
        raise ValueError(f"--{name} must not be empty")
    return value


def _parse_judge_list(raw: object) -> List[str]:
    if isinstance(raw, list):
        items = [str(x).strip() for x in raw if str(x).strip()]
    else:
        text = str(raw or "")
        items = [part.strip() for part in text.split(",") if part.strip()]
    if not items:
        raise ValueError("--judge_LLM_list must contain at least one model")
    return items


def _parse_reasoning_effort_map(raw: object) -> Dict[str, str]:
    if raw in (None, "", "null"):
        return {}
    if isinstance(raw, dict):
        return normalize_reasoning_effort_map(raw)
    try:
        parsed = json.loads(str(raw))
    except json.JSONDecodeError as exc:
        raise ValueError("--judge_reasoning_effort_by_model_json must be a valid JSON object") from exc
    if not isinstance(parsed, dict):
        raise ValueError("--judge_reasoning_effort_by_model_json must be a JSON object")
    return normalize_reasoning_effort_map(parsed)


def _parse_dimension_list(raw: object) -> List[str]:
    allowed = {"tools", "prefs", "rubrics"}
    if isinstance(raw, list):
        items = [str(x).strip() for x in raw if str(x).strip()]
    else:
        text = str(raw or "")
        items = [part.strip() for part in text.split(",") if part.strip()]
    if not items:
        raise ValueError("--response_dimension must contain at least one of: tools, prefs, rubrics")
    unknown = [item for item in items if item not in allowed]
    if unknown:
        raise ValueError(
            "--response_dimension must contain only tools, prefs, rubrics; "
            f"got {unknown}"
        )
    return sorted(set(items))


def _parse_dimension_list_preserve_order(raw: object, *, arg_name: str) -> List[str]:
    allowed = {"tools", "prefs", "rubrics"}
    if isinstance(raw, list):
        items = [str(x).strip() for x in raw if str(x).strip()]
    else:
        text = str(raw or "")
        items = [part.strip() for part in text.split(",") if part.strip()]
    if not items:
        raise ValueError(f"--{arg_name} must contain at least one of: tools, prefs, rubrics")
    unknown = [item for item in items if item not in allowed]
    if unknown:
        raise ValueError(
            f"--{arg_name} must contain only tools, prefs, rubrics; got {unknown}"
        )
    out: List[str] = []
    seen = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _parse_early_stop_modes(raw: object) -> List[str]:
    allowed = {"repeated_violation", "no_new_violation"}
    if isinstance(raw, list):
        items = [str(x).strip() for x in raw if str(x).strip()]
    else:
        text = str(raw or "")
        items = [part.strip() for part in text.split(",") if part.strip()]
    if not items:
        items = ["repeated_violation"]
    unknown = [item for item in items if item not in allowed]
    if unknown:
        raise ValueError(
            "--early_stop_mode must contain only repeated_violation and/or no_new_violation; "
            f"got {unknown}"
        )
    return sorted(set(items))


def resolve_args(args) -> argparse.Namespace:
    cfg = _load_config(Path(args.config))

    out = argparse.Namespace()
    out.query_path = _pick(args.query_path, cfg, "query_path", None)
    out.out = str(_require(_pick(args.out, cfg, "out", None), "out"))
    out.result_out = _pick(args.result_out, cfg, "result_out", None)

    out.domain = str(_require(_pick(args.domain, cfg, "domain", None), "domain"))
    out.source = str(_require(_pick(args.source, cfg, "source", None), "source"))
    raw_ban_only = _pick(args.ban_only, cfg, "ban_only", None)
    if raw_ban_only in (None, "", "null"):
        out.ban_only = None
    else:
        out.ban_only = str(raw_ban_only).strip().lower()
        if out.ban_only not in {"tools", "prefs"}:
            raise ValueError("--ban_only must be one of: tools, prefs")
    raw_rubrics_refine_continue_from = _pick(
        args.rubrics_refine_continue_from,
        cfg,
        "rubrics_refine_continue_from",
        None,
    )
    if raw_rubrics_refine_continue_from in (None, "", "null"):
        out.rubrics_refine_continue_from = None
    else:
        out.rubrics_refine_continue_from = str(Path(str(raw_rubrics_refine_continue_from)).expanduser())
        out.out = str(Path(out.out) / "rubrics_refine")

    out.model = str(_require(_pick(args.model, cfg, "model", None), "model"))
    out.model_max_tokens = int(_pick(args.model_max_tokens, cfg, "model_max_tokens", 2048))
    out.model_temperature = float(_pick(args.model_temperature, cfg, "model_temperature", 0.7))

    judge_list_raw = _pick(
        args.judge_LLM_list,
        cfg,
        "judge_LLM_list",
        _pick(None, cfg, "judge_LLM", None),
    )
    fallback_judge_list = _parse_judge_list(_require(judge_list_raw, "judge_LLM_list"))
    out.judge_LLM_list = list(fallback_judge_list)
    out.judge_merge_mode = str(_pick(args.judge_merge_mode, cfg, "judge_merge_mode", "union"))
    out.tolerant_fail_judge_nums = int(
        _pick(args.tolerant_fail_judge_nums, cfg, "tolerant_fail_judge_nums", 0)
    )
    out.tools_judge_LLM_list = _parse_judge_list(
        _pick(args.tools_judge_LLM_list, cfg, "tools_judge_LLM_list", fallback_judge_list)
    )
    out.prefs_judge_LLM_list = _parse_judge_list(
        _pick(args.prefs_judge_LLM_list, cfg, "prefs_judge_LLM_list", fallback_judge_list)
    )
    out.rubrics_judge_LLM_list = _parse_judge_list(
        _pick(args.rubrics_judge_LLM_list, cfg, "rubrics_judge_LLM_list", fallback_judge_list)
    )
    out.tools_judge_merge_mode = str(
        _pick(args.tools_judge_merge_mode, cfg, "tools_judge_merge_mode", out.judge_merge_mode)
    )
    out.prefs_judge_merge_mode = str(
        _pick(args.prefs_judge_merge_mode, cfg, "prefs_judge_merge_mode", out.judge_merge_mode)
    )
    out.rubrics_judge_merge_mode = str(
        _pick(args.rubrics_judge_merge_mode, cfg, "rubrics_judge_merge_mode", out.judge_merge_mode)
    )
    out.tools_tolerant_fail_judge_nums = int(
        _pick(
            args.tools_tolerant_fail_judge_nums,
            cfg,
            "tools_tolerant_fail_judge_nums",
            out.tolerant_fail_judge_nums,
        )
    )
    out.prefs_tolerant_fail_judge_nums = int(
        _pick(
            args.prefs_tolerant_fail_judge_nums,
            cfg,
            "prefs_tolerant_fail_judge_nums",
            out.tolerant_fail_judge_nums,
        )
    )
    out.rubrics_tolerant_fail_judge_nums = int(
        _pick(
            args.rubrics_tolerant_fail_judge_nums,
            cfg,
            "rubrics_tolerant_fail_judge_nums",
            out.tolerant_fail_judge_nums,
        )
    )
    out.rubrics_score_merge_mode = str(
        _pick(args.rubrics_score_merge_mode, cfg, "rubrics_score_merge_mode", "mean")
    )
    out.rubrics_pass_mode = str(
        _pick(args.rubrics_pass_mode, cfg, "rubrics_pass_mode", "min")
    )
    out.rubrics_pass_threshold = float(
        _pick(args.rubrics_pass_threshold, cfg, "rubrics_pass_threshold", 4)
    )
    out.rubrics_feedback_threshold = float(
        _pick(
            args.rubrics_feedback_threshold,
            cfg,
            "rubrics_feedback_threshold",
            4,
        )
    )
    out.response_dimension = _parse_dimension_list(
        _pick(args.response_dimension, cfg, "response_dimension", "tools,prefs,rubrics")
    )
    raw_ordered_elicit = _pick(args.ordered_elicit, cfg, "ordered_elicit", None)
    if raw_ordered_elicit in (None, "", "null"):
        out.ordered_elicit = None
    else:
        out.ordered_elicit = _parse_dimension_list_preserve_order(
            raw_ordered_elicit,
            arg_name="ordered_elicit",
        )
    out.judge_max_tokens = int(_pick(args.judge_max_tokens, cfg, "judge_max_tokens", 2048))
    out.judge_temperature = float(_pick(args.judge_temperature, cfg, "judge_temperature", 0.0))
    raw_judge_reasoning_effort = _pick(
        args.judge_reasoning_effort,
        cfg,
        "judge_reasoning_effort",
        None,
    )
    if raw_judge_reasoning_effort in (None, "", "null"):
        out.judge_reasoning_effort = None
    else:
        out.judge_reasoning_effort = str(raw_judge_reasoning_effort).strip()
    out.judge_reasoning_effort_by_model = _parse_reasoning_effort_map(
        _pick(
            args.judge_reasoning_effort_by_model_json,
            cfg,
            "judge_reasoning_effort_by_model_json",
            _pick(None, cfg, "judge_reasoning_effort_by_model", None),
        )
    )

    out.gen_LLM = str(_require(_pick(args.gen_LLM, cfg, "gen_LLM", None), "gen_LLM"))
    out.gen_max_tokens = int(_pick(args.gen_max_tokens, cfg, "gen_max_tokens", 2048))
    out.gen_temperature = float(_pick(args.gen_temperature, cfg, "gen_temperature", 0.7))

    out.merge_LLM = _pick(args.merge_LLM, cfg, "merge_LLM", None)
    out.check_LLM = _pick(args.check_LLM, cfg, "check_LLM", None)
    out.merge_max_tokens = int(_pick(args.merge_max_tokens, cfg, "merge_max_tokens", 1024))
    out.merge_temperature = float(_pick(args.merge_temperature, cfg, "merge_temperature", 0.0))
    out.merge_LLM_temperature = float(
        _pick(
            args.merge_LLM_temperature,
            cfg,
            "merge_LLM_temperature",
            out.merge_temperature,
        )
    )
    out.check_LLM_temperature = float(
        _pick(
            args.check_LLM_temperature,
            cfg,
            "check_LLM_temperature",
            out.merge_LLM_temperature,
        )
    )
    out.merge_timeout_s = int(_pick(args.merge_timeout_s, cfg, "merge_timeout_s", _pick(args.llm_timeout_s, cfg, "llm_timeout_s", 120)))
    out.check_timeout_s = int(
        _pick(
            args.check_timeout_s,
            cfg,
            "check_timeout_s",
            out.merge_timeout_s,
        )
    )
    out.llm_timeout_s = int(_pick(args.llm_timeout_s, cfg, "llm_timeout_s", 120))
    out.llm_max_retries = int(_pick(args.llm_max_retries, cfg, "llm_max_retries", 2))
    out.llm_retry_backoff_s = float(
        _pick(args.llm_retry_backoff_s, cfg, "llm_retry_backoff_s", 2.0)
    )

    out.max_concurrency = int(_pick(args.max_concurrency, cfg, "max_concurrency", 8))
    out.max_turns = int(_pick(args.max_turns, cfg, "max_turns", 6))
    out.max_resume_attempts = int(_pick(args.max_resume_attempts, cfg, "max_resume_attempts", 3))

    out.ban_sample_num = int(_require(_pick(args.ban_sample_num, cfg, "ban_sample_num", None), "ban_sample_num"))
    out.ban_iterative_sample_num = int(
        _require(_pick(args.ban_iterative_sample_num, cfg, "ban_iterative_sample_num", None), "ban_iterative_sample_num")
    )
    out.ban_verbal_sample_num = int(
        _require(_pick(args.ban_verbal_sample_num, cfg, "ban_verbal_sample_num", None), "ban_verbal_sample_num")
    )

    out.full_evidence = _as_bool(_pick(args.full_evidence, cfg, "full_evidence", False))
    out.refine_rubrics = _as_bool(_pick(args.refine_rubrics, cfg, "refine_rubrics", False))
    out.memory = _as_bool(_pick(args.memory, cfg, "memory", False))
    out.direct_elicit = _as_bool(_pick(args.direct_elicit, cfg, "direct_elicit", False))
    out.timer = _as_bool(_pick(args.timer, cfg, "timer", False))
    out.debug = _as_bool(_pick(args.debug, cfg, "debug", False))
    out.debug_out_dir = _pick(args.debug_out_dir, cfg, "debug_out_dir", None)

    out.retry_num = int(_pick(args.retry_num, cfg, "retry_num", 0))
    out.fail_fast = _as_bool(_pick(args.fail_fast, cfg, "fail_fast", False))
    out.fail_threshold = float(_pick(args.fail_threshold, cfg, "fail_threshold", 1.0))
    out.truncate_history = _as_bool(_pick(args.truncate_history, cfg, "truncate_history", False))
    out.repetition_penalty_response = _as_bool(_pick(args.repetition_penalty_response, cfg, "repetition_penalty_response", False))

    out.early_stop = _as_bool(_pick(args.early_stop, cfg, "early_stop", False))
    out.early_stop_mode = _parse_early_stop_modes(
        _pick(args.early_stop_mode, cfg, "early_stop_mode", "repeated_violation")
    )
    repeated_limit_default = _pick(args.stop_limit, cfg, "stop_limit", 3)
    out.repeated_violation_stop_limit = int(
        _pick(
            args.repeated_violation_stop_limit,
            cfg,
            "repeated_violation_stop_limit",
            repeated_limit_default,
        )
    )
    out.no_new_violation_round_limit = int(
        _pick(
            args.no_new_violation_round_limit,
            cfg,
            "no_new_violation_round_limit",
            3,
        )
    )
    out.rubrics_refine_max_turns = int(
        _pick(
            args.rubrics_refine_max_turns,
            cfg,
            "rubrics_refine_max_turns",
            0,
        )
    )
    out.num_ckpts = int(_pick(args.num_ckpts, cfg, "num_ckpts", 1))

    _trial = _pick(args.trial_num, cfg, "trial_num", None)
    out.trial_num = int(_trial) if _trial is not None else None

    out.model_metadata = str(_pick(args.model_metadata, cfg, "model_metadata", str(DEFAULT_MODEL_METADATA)))
    out.dotenv = str(_pick(args.dotenv, cfg, "dotenv", str(DEFAULT_DOTENV)))
    out.config = args.config
    return out


def validate_args(args) -> None:
    if args.max_concurrency <= 0:
        raise ValueError("--max_concurrency must be > 0")
    if args.max_turns <= 0:
        raise ValueError("--max_turns must be > 0")
    if args.max_resume_attempts < 0:
        raise ValueError("--max_resume_attempts must be >= 0")
    if args.tolerant_fail_judge_nums < 0:
        raise ValueError("--tolerant_fail_judge_nums must be >= 0")
    if args.judge_merge_mode not in {"union", "intersec"}:
        raise ValueError("--judge_merge_mode must be one of: union, intersec")
    if args.tools_judge_merge_mode not in {"union", "intersec"}:
        raise ValueError("--tools_judge_merge_mode must be one of: union, intersec")
    if args.prefs_judge_merge_mode not in {"union", "intersec"}:
        raise ValueError("--prefs_judge_merge_mode must be one of: union, intersec")
    if args.rubrics_judge_merge_mode not in {"union", "intersec"}:
        raise ValueError("--rubrics_judge_merge_mode must be one of: union, intersec")
    if args.rubrics_score_merge_mode not in {"mean", "min", "max"}:
        raise ValueError("--rubrics_score_merge_mode must be one of: mean, min, max")
    if args.rubrics_pass_mode not in {"mean", "min"}:
        raise ValueError("--rubrics_pass_mode must be one of: mean, min")
    for name in (
        "tools_tolerant_fail_judge_nums",
        "prefs_tolerant_fail_judge_nums",
        "rubrics_tolerant_fail_judge_nums",
    ):
        if int(getattr(args, name)) < 0:
            raise ValueError(f"--{name} must be >= 0")
    if not (1.0 <= float(args.rubrics_pass_threshold) <= 5.0):
        raise ValueError("--rubrics_pass_threshold must be in [1, 5]")
    if not (1.0 <= float(args.rubrics_feedback_threshold) <= 5.0):
        raise ValueError("--rubrics_feedback_threshold must be in [1, 5]")
    if args.ban_only == "tools" and "prefs" in args.response_dimension:
        raise ValueError("--response_dimension cannot include prefs when --ban_only=tools")
    if args.ban_only == "prefs" and "tools" in args.response_dimension:
        raise ValueError("--response_dimension cannot include tools when --ban_only=prefs")
    if args.ordered_elicit is not None:
        if args.ban_only == "tools" and "prefs" in args.ordered_elicit:
            raise ValueError("--ordered_elicit cannot include prefs when --ban_only=tools")
        if args.ban_only == "prefs" and "tools" in args.ordered_elicit:
            raise ValueError("--ordered_elicit cannot include tools when --ban_only=prefs")

    for name in (
        "model_max_tokens",
        "judge_max_tokens",
        "gen_max_tokens",
        "merge_max_tokens",
        "merge_timeout_s",
        "check_timeout_s",
        "llm_timeout_s",
    ):
        if int(getattr(args, name)) <= 0:
            raise ValueError(f"--{name} must be > 0")

    if int(args.llm_max_retries) < 0:
        raise ValueError("--llm_max_retries must be >= 0")
    if float(args.llm_retry_backoff_s) < 0:
        raise ValueError("--llm_retry_backoff_s must be >= 0")

    if int(args.retry_num) < 0:
        raise ValueError("--retry_num must be >= 0")

    if not (0.0 <= float(args.fail_threshold) <= 1.0):
        raise ValueError("--fail_threshold must be in [0, 1]")

    if int(args.repeated_violation_stop_limit) < 1:
        raise ValueError("--repeated_violation_stop_limit must be >= 1")
    if int(args.no_new_violation_round_limit) < 1:
        raise ValueError("--no_new_violation_round_limit must be >= 1")
    if int(args.rubrics_refine_max_turns) < 0:
        raise ValueError("--rubrics_refine_max_turns must be >= 0")
    if args.rubrics_refine_continue_from is not None:
        source_dir = Path(str(args.rubrics_refine_continue_from))
        if not source_dir.exists() or not source_dir.is_dir():
            raise ValueError(
                "--rubrics_refine_continue_from must point to an existing results directory"
            )
        if not bool(args.refine_rubrics):
            raise ValueError(
                "--rubrics_refine_continue_from requires --refine_rubrics because continuation needs rubrics feedback"
            )
        if int(args.rubrics_refine_max_turns) <= 0:
            raise ValueError(
                "--rubrics_refine_continue_from requires --rubrics_refine_max_turns > 0"
            )

    if int(args.num_ckpts) < 1:
        raise ValueError("--num_ckpts must be >= 1")

    if args.trial_num is not None and int(args.trial_num) < 1:
        raise ValueError("--trial_num must be >= 1")

    if args.debug and args.debug_out_dir:
        out_dir = Path(args.debug_out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        if not out_dir.exists() or not out_dir.is_dir():
            raise ValueError(f"--debug_out_dir is not a writable directory: {out_dir}")


def _build_runner_config(args) -> RunnerConfig:
    run_time = datetime.now(timezone.utc).isoformat()
    return RunnerConfig(
        query_path=args.query_path,
        out=args.out,
        result_out=args.result_out,
        domain=args.domain,
        source=args.source,
        ban_only=args.ban_only,
        rubrics_refine_continue_from=args.rubrics_refine_continue_from,
        model=args.model,
        model_max_tokens=int(args.model_max_tokens),
        model_temperature=float(args.model_temperature),
        judge_LLM_list=list(args.judge_LLM_list),
        judge_merge_mode=args.judge_merge_mode,
        tolerant_fail_judge_nums=int(args.tolerant_fail_judge_nums),
        tools_judge_LLM_list=list(args.tools_judge_LLM_list),
        prefs_judge_LLM_list=list(args.prefs_judge_LLM_list),
        rubrics_judge_LLM_list=list(args.rubrics_judge_LLM_list),
        tools_judge_merge_mode=args.tools_judge_merge_mode,
        prefs_judge_merge_mode=args.prefs_judge_merge_mode,
        rubrics_judge_merge_mode=args.rubrics_judge_merge_mode,
        tools_tolerant_fail_judge_nums=int(args.tools_tolerant_fail_judge_nums),
        prefs_tolerant_fail_judge_nums=int(args.prefs_tolerant_fail_judge_nums),
        rubrics_tolerant_fail_judge_nums=int(args.rubrics_tolerant_fail_judge_nums),
        rubrics_score_merge_mode=args.rubrics_score_merge_mode,
        rubrics_pass_mode=args.rubrics_pass_mode,
        rubrics_pass_threshold=float(args.rubrics_pass_threshold),
        rubrics_feedback_threshold=float(args.rubrics_feedback_threshold),
        response_dimension=list(args.response_dimension),
        ordered_elicit=list(args.ordered_elicit) if args.ordered_elicit is not None else None,
        judge_max_tokens=int(args.judge_max_tokens),
        judge_temperature=float(args.judge_temperature),
        judge_reasoning_effort=args.judge_reasoning_effort,
        judge_reasoning_effort_by_model=dict(args.judge_reasoning_effort_by_model),
        gen_LLM=args.gen_LLM,
        gen_max_tokens=int(args.gen_max_tokens),
        gen_temperature=float(args.gen_temperature),
        merge_LLM=args.merge_LLM,
        check_LLM=args.check_LLM,
        merge_max_tokens=int(args.merge_max_tokens),
        merge_temperature=float(args.merge_temperature),
        merge_LLM_temperature=float(args.merge_LLM_temperature),
        check_LLM_temperature=float(args.check_LLM_temperature),
        merge_timeout_s=int(args.merge_timeout_s),
        check_timeout_s=int(args.check_timeout_s),
        llm_timeout_s=int(args.llm_timeout_s),
        llm_max_retries=int(args.llm_max_retries),
        llm_retry_backoff_s=float(args.llm_retry_backoff_s),
        max_turns=int(args.max_turns),
        max_concurrency=int(args.max_concurrency),
        max_resume_attempts=int(args.max_resume_attempts),
        ban_sample_num=int(args.ban_sample_num),
        ban_iterative_sample_num=int(args.ban_iterative_sample_num),
        ban_verbal_sample_num=int(args.ban_verbal_sample_num),
        full_evidence=bool(args.full_evidence),
        refine_rubrics=bool(args.refine_rubrics),
        memory=bool(args.memory),
        direct_elicit=bool(args.direct_elicit),
        timer=bool(args.timer),
        debug=bool(args.debug),
        debug_out_dir=args.debug_out_dir,
        retry_num=int(args.retry_num),
        fail_fast=bool(args.fail_fast),
        fail_threshold=float(args.fail_threshold),
        truncate_history=bool(args.truncate_history),
        repetition_penalty_response=bool(args.repetition_penalty_response),
        early_stop=bool(args.early_stop),
        early_stop_mode=list(args.early_stop_mode),
        repeated_violation_stop_limit=int(args.repeated_violation_stop_limit),
        no_new_violation_round_limit=int(args.no_new_violation_round_limit),
        rubrics_refine_max_turns=int(args.rubrics_refine_max_turns),
        num_ckpts=int(args.num_ckpts),
        trial_num=int(args.trial_num) if args.trial_num is not None else None,
        model_metadata=args.model_metadata,
        dotenv=args.dotenv,
        run_time=run_time,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_arg_parser()
    parsed_args = parser.parse_args(list(argv) if argv is not None else None)
    args = resolve_args(parsed_args)
    validate_args(args)

    load_dotenv_if_present(Path(args.dotenv))

    print(f"[run] config={args.config}")
    print(f"[run] domain={args.domain} source={args.source}")
    if args.ban_only:
        print(f"[run] ban_only={args.ban_only}")
    if args.rubrics_refine_continue_from:
        print(
            f"[run] rubrics_refine_continue_from={args.rubrics_refine_continue_from} "
            f"-> output_dir={args.out}"
        )
    print(
        "[run] model={model} tools_judges={tools} prefs_judges={prefs} "
        "rubrics_judges={rubrics} response_dimension={resp} gen={gen} merge={merge} check={check}".format(
            model=args.model,
            tools=",".join(args.tools_judge_LLM_list),
            prefs=",".join(args.prefs_judge_LLM_list),
            rubrics=",".join(args.rubrics_judge_LLM_list),
            resp=",".join(args.response_dimension),
            gen=args.gen_LLM,
            merge=args.merge_LLM or args.judge_LLM_list[0],
            check=args.check_LLM or args.merge_LLM or args.judge_LLM_list[0],
        )
    )
    print(
        "[run] rubrics_score_merge_mode={merge} rubrics_pass_mode={mode} "
        "rubrics_pass_threshold={pass_t} rubrics_feedback_threshold={fb_t} "
        "rubrics_refine_max_turns={mturns}".format(
            merge=args.rubrics_score_merge_mode,
            mode=args.rubrics_pass_mode,
            pass_t=args.rubrics_pass_threshold,
            fb_t=args.rubrics_feedback_threshold,
            mturns=args.rubrics_refine_max_turns,
        )
    )
    if args.judge_reasoning_effort:
        print(f"[run] judge_reasoning_effort={args.judge_reasoning_effort}")
    if args.judge_reasoning_effort_by_model:
        print(f"[run] judge_reasoning_effort_by_model configured for {len(args.judge_reasoning_effort_by_model)} models")
    if args.ordered_elicit:
        print(f"[run] ordered_elicit={','.join(args.ordered_elicit)}")
    cfg = _build_runner_config(args)
    runner = Runner(cfg)
    resolved_query_path = (
        runner.dataworker.resolve_default_query_path()
        if args.query_path is None
        else Path(args.query_path)
    )
    print(f"[run] loading queries from {resolved_query_path}")

    print("[run] preparing environment profiles ...")
    runner.prepare()

    result_path = runner.dataworker.build_result_path()

    if not runner.query_entries:
        if not result_path.exists():
            runner.dataworker.dump_results(runner.build_current_payload())
            print(f"[run] progress already complete; wrote missing result folder -> {result_path}")
            runner.print_timer_summary()
            return 0
        print(f"[run] already ran; nothing to resume from {result_path}")
        runner.print_timer_summary()
        return 0

    print(f"[run] starting runtime evaluation ...")
    payload = runner.run()
    runner.print_timer_summary()
    if payload["metadata"].get("progress_complete"):
        output_path = runner.dataworker.dump_results(payload)
        print(f"Wrote results -> {output_path}")
        return 0

    print(f"[run] incomplete after resume attempts; partial results kept at {result_path}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
