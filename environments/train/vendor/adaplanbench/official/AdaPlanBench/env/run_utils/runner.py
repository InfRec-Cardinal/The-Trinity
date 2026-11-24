from __future__ import annotations

import copy
import hashlib
import json
import re
import threading
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

try:
    from tqdm import tqdm
except Exception:
    tqdm = None

from . import run_prompts
from .dataworker import DataWorker
from .judgers import HousingJudger
from .llm import ModelConfig, format_prompt, openai_chat_request, resolve_api_key
from .run_merge import RuntimeMerger
from .timer import RuntimeTimer
from .tracker import Tracker


@dataclass
class RunnerConfig:
    query_path: Optional[str]
    out: str
    result_out: Optional[str]
    domain: str
    source: str
    ban_only: Optional[str]
    rubrics_refine_continue_from: Optional[str]

    model: str
    model_max_tokens: int
    model_temperature: float

    judge_LLM_list: List[str]
    judge_merge_mode: str
    tolerant_fail_judge_nums: int
    tools_judge_LLM_list: List[str]
    prefs_judge_LLM_list: List[str]
    rubrics_judge_LLM_list: List[str]
    tools_judge_merge_mode: str
    prefs_judge_merge_mode: str
    rubrics_judge_merge_mode: str
    tools_tolerant_fail_judge_nums: int
    prefs_tolerant_fail_judge_nums: int
    rubrics_tolerant_fail_judge_nums: int
    rubrics_score_merge_mode: str
    rubrics_pass_mode: str
    rubrics_pass_threshold: float
    rubrics_feedback_threshold: float
    response_dimension: List[str]
    ordered_elicit: Optional[List[str]]
    judge_max_tokens: int
    judge_temperature: float
    judge_reasoning_effort: Optional[str]
    judge_reasoning_effort_by_model: Dict[str, str]

    gen_LLM: str
    gen_max_tokens: int
    gen_temperature: float

    merge_LLM: Optional[str]
    check_LLM: Optional[str]
    merge_max_tokens: int
    merge_temperature: float
    merge_LLM_temperature: float
    check_LLM_temperature: float
    merge_timeout_s: int
    check_timeout_s: int
    llm_timeout_s: int
    llm_max_retries: int
    llm_retry_backoff_s: float

    max_turns: int
    max_concurrency: int
    max_resume_attempts: int

    ban_sample_num: int
    ban_iterative_sample_num: int
    ban_verbal_sample_num: int

    full_evidence: bool
    refine_rubrics: bool
    memory: bool
    direct_elicit: bool
    timer: bool
    debug: bool
    debug_out_dir: Optional[str]

    retry_num: int
    fail_fast: bool
    fail_threshold: float
    truncate_history: bool
    repetition_penalty_response: bool

    early_stop: bool
    early_stop_mode: List[str]
    repeated_violation_stop_limit: int
    no_new_violation_round_limit: int
    rubrics_refine_max_turns: int

    num_ckpts: int
    trial_num: Optional[int]

    model_metadata: str
    dotenv: str

    run_time: str


class Runner:
    _RERUN_STATUSES = {"error", "skipped", "pending"}
    _TERMINAL_STATUSES = {"success", "failed", "stopped"}
    _RUBRIC_NAMES = (
        "Tool-use feasibility",
        "Physical plausibility",
        "Logical step ordering",
        "Effectiveness",
        "Concreteness",
        "Safety",
        "Consequence awareness",
        "Autonomy",
        "Creativity",
    )
    _NON_FAILING_RUBRICS = {"Creativity"}
    _RESUME_MATCH_FIELDS = (
        "domain",
        "source",
        "ban_only",
        "ban_sample_num",
        "ban_iterative_sample_num",
        "ban_verbal_sample_num",
        "model",
        "model_temperature",
        "tools_judge_models",
        "prefs_judge_models",
        "rubrics_judge_models",
        "tools_judge_merge_mode",
        "prefs_judge_merge_mode",
        "rubrics_judge_merge_mode",
        "tools_tolerant_fail_judge_nums",
        "prefs_tolerant_fail_judge_nums",
        "rubrics_tolerant_fail_judge_nums",
        "rubrics_score_merge_mode",
        "rubrics_pass_mode",
        "rubrics_pass_threshold",
        "rubrics_feedback_threshold",
        "response_dimension",
        "ordered_elicit",
        "judge_reasoning_effort",
        "judge_reasoning_effort_by_model",
        "max_turns",
        "full_evidence",
        "refine_rubrics",
        "memory",
        "direct_elicit",
        "early_stop",
        "early_stop_mode",
        "repeated_violation_stop_limit",
        "no_new_violation_round_limit",
        "rubrics_refine_continue_from",
        "rubrics_refine_max_turns",
    )

    def __init__(self, cfg: RunnerConfig):
        self.cfg = cfg
        self.dataworker = DataWorker(cfg)

        self.model_cfg = self.dataworker.load_model_config(cfg.model)
        self.tools_judge_cfgs = [self.dataworker.load_model_config(name) for name in cfg.tools_judge_LLM_list]
        self.prefs_judge_cfgs = [self.dataworker.load_model_config(name) for name in cfg.prefs_judge_LLM_list]
        self.rubrics_judge_cfgs = [self.dataworker.load_model_config(name) for name in cfg.rubrics_judge_LLM_list]
        self.gen_cfg = self.dataworker.load_model_config(cfg.gen_LLM)

        fallback_merge_judge = (
            (cfg.tools_judge_LLM_list or cfg.prefs_judge_LLM_list or cfg.rubrics_judge_LLM_list)[0]
        )
        merge_model_name = cfg.merge_LLM or fallback_merge_judge
        check_model_name = cfg.check_LLM or merge_model_name
        self.merge_cfg = self.dataworker.load_model_config(merge_model_name)
        self.check_cfg = self.dataworker.load_model_config(check_model_name)

        self.model_api_key = resolve_api_key(self.model_cfg.api_key_env)
        self.merger = RuntimeMerger(cfg, self.dataworker, self.merge_cfg, self.check_cfg)

        if cfg.domain != "housing":
            raise ValueError(f"Unsupported domain for current runtime: {cfg.domain}")
        self.judger = HousingJudger(cfg, self.gen_cfg)

        self.query_entries: List[dict] = []
        self.debug_lock = threading.Lock()
        self.state_lock = threading.Lock()
        self.timer = RuntimeTimer(enabled=cfg.timer)

        self._all_results_by_id: Dict[str, dict] = {}
        self._ordered_query_ids: List[str] = []
        self._query_index_by_id: Dict[str, int] = {}
        self._checkpoint_metadata: Dict[str, object] = {}

    @staticmethod
    def _all_dimension_names() -> Tuple[str, str, str]:
        return ("tools", "prefs", "rubrics")

    def _response_dimension_set(self) -> set[str]:
        return set(self.cfg.response_dimension)

    def _select_elicited_dimensions(self, candidate_dimensions: List[str]) -> List[str]:
        if not candidate_dimensions:
            return []
        candidates = list(dict.fromkeys(candidate_dimensions))
        if not self.cfg.ordered_elicit:
            return candidates
        allowed = set(candidates)
        for name in self.cfg.ordered_elicit:
            if name in allowed:
                return [name]
        return candidates

    def _dimension_enabled(self, stage_name: str) -> bool:
        if stage_name == "tools":
            return self._ban_tools_enabled()
        if stage_name == "prefs":
            return self._ban_prefs_enabled()
        if stage_name == "rubrics":
            return True
        raise ValueError(f"Unknown stage_name: {stage_name}")

    def _get_stage_judge_cfgs(self, stage_name: str) -> List[ModelConfig]:
        if stage_name == "tools":
            return self.tools_judge_cfgs
        if stage_name == "prefs":
            return self.prefs_judge_cfgs
        if stage_name == "rubrics":
            return self.rubrics_judge_cfgs
        raise ValueError(f"Unknown stage_name: {stage_name}")

    def _get_stage_merge_mode(self, stage_name: str) -> str:
        if stage_name == "tools":
            return self.cfg.tools_judge_merge_mode
        if stage_name == "prefs":
            return self.cfg.prefs_judge_merge_mode
        if stage_name == "rubrics":
            return self.cfg.rubrics_judge_merge_mode
        raise ValueError(f"Unknown stage_name: {stage_name}")

    def _get_stage_tolerant_fail_limit(self, stage_name: str) -> int:
        if stage_name == "tools":
            return int(self.cfg.tools_tolerant_fail_judge_nums)
        if stage_name == "prefs":
            return int(self.cfg.prefs_tolerant_fail_judge_nums)
        if stage_name == "rubrics":
            return int(self.cfg.rubrics_tolerant_fail_judge_nums)
        raise ValueError(f"Unknown stage_name: {stage_name}")

    @staticmethod
    def _get_stage_timer_role(stage_name: str) -> str:
        if stage_name == "tools":
            return "judge_tools"
        if stage_name == "prefs":
            return "judge_prefs"
        if stage_name == "rubrics":
            return "judge_rubrics"
        raise ValueError(f"Unknown stage_name: {stage_name}")

    @staticmethod
    def _get_stage_parse_kind(stage_name: str) -> str:
        if stage_name == "tools":
            return "env"
        if stage_name == "prefs":
            return "prefs"
        if stage_name == "rubrics":
            return "rubrics"
        raise ValueError(f"Unknown stage_name: {stage_name}")

    def _ban_tools_enabled(self) -> bool:
        return self.cfg.ban_only != "prefs"

    def _ban_prefs_enabled(self) -> bool:
        return self.cfg.ban_only != "tools"

    def _apply_ban_scope_to_profile(self, env_profile: dict) -> dict:
        scoped = dict(env_profile or {})
        if not self._ban_tools_enabled():
            scoped["tools"] = []
        if not self._ban_prefs_enabled():
            scoped["prefs"] = []
        return scoped

    def _build_ban_scope_hint(self) -> str:
        if self._ban_tools_enabled() and self._ban_prefs_enabled():
            return run_prompts.ban_scope_hint_tools_and_prefs
        if self._ban_tools_enabled():
            return run_prompts.ban_scope_hint_tools_only
        return run_prompts.ban_scope_hint_prefs_only

    def _build_feedback_prompt_scope_fields(self) -> Dict[str, str]:
        response_dimensions = self._response_dimension_set()
        tools_enabled = self._ban_tools_enabled() and "tools" in response_dimensions
        prefs_enabled = self._ban_prefs_enabled() and "prefs" in response_dimensions
        if tools_enabled and prefs_enabled:
            return {
                "tools_placeholder": run_prompts.tools_placeholder,
                "prefs_placeholder": format_prompt(
                    run_prompts.prefs_placeholder,
                    {"or_text": getattr(run_prompts, "or_text", "or")},
                ),
            }
        if tools_enabled:
            return {
                "tools_placeholder": run_prompts.tools_placeholder,
                "prefs_placeholder": "",
            }
        if prefs_enabled:
            return {
                "tools_placeholder": "",
                "prefs_placeholder": format_prompt(run_prompts.prefs_placeholder, {"or_text": ""}).strip(),
            }
        return {"tools_placeholder": "", "prefs_placeholder": ""}

    @staticmethod
    def _safe_file_token(text: str) -> str:
        return re.sub(r"[^A-Za-z0-9._-]+", "_", str(text or ""))

    def _build_base_metadata(self) -> Dict[str, object]:
        return {
            "domain": self.cfg.domain,
            "source": self.cfg.source,
            "ban_only": self.cfg.ban_only,
            "rubrics_refine_continue_from": self.cfg.rubrics_refine_continue_from,
            "model": self.cfg.model,
            "model_temperature": float(self.cfg.model_temperature),
            "tools_judge_models": list(self.cfg.tools_judge_LLM_list),
            "prefs_judge_models": list(self.cfg.prefs_judge_LLM_list),
            "rubrics_judge_models": list(self.cfg.rubrics_judge_LLM_list),
            "tools_judge_merge_mode": self.cfg.tools_judge_merge_mode,
            "prefs_judge_merge_mode": self.cfg.prefs_judge_merge_mode,
            "rubrics_judge_merge_mode": self.cfg.rubrics_judge_merge_mode,
            "tools_tolerant_fail_judge_nums": int(self.cfg.tools_tolerant_fail_judge_nums),
            "prefs_tolerant_fail_judge_nums": int(self.cfg.prefs_tolerant_fail_judge_nums),
            "rubrics_tolerant_fail_judge_nums": int(self.cfg.rubrics_tolerant_fail_judge_nums),
            "rubrics_score_merge_mode": self.cfg.rubrics_score_merge_mode,
            "rubrics_pass_mode": self.cfg.rubrics_pass_mode,
            "rubrics_pass_threshold": float(self.cfg.rubrics_pass_threshold),
            "rubrics_feedback_threshold": float(self.cfg.rubrics_feedback_threshold),
            "response_dimension": list(self.cfg.response_dimension),
            "ordered_elicit": list(self.cfg.ordered_elicit) if self.cfg.ordered_elicit is not None else None,
            "judge_reasoning_effort": self.cfg.judge_reasoning_effort,
            "judge_reasoning_effort_by_model": dict(self.cfg.judge_reasoning_effort_by_model),
            "gen_model": self.cfg.gen_LLM,
            "merge_model": self.cfg.merge_LLM or self.merge_cfg.name,
            "check_model": self.cfg.check_LLM or self.check_cfg.name,
            "ban_sample_num": int(self.cfg.ban_sample_num),
            "ban_iterative_sample_num": int(self.cfg.ban_iterative_sample_num),
            "ban_verbal_sample_num": int(self.cfg.ban_verbal_sample_num),
            "llm_timeout_s": int(self.cfg.llm_timeout_s),
            "llm_max_retries": int(self.cfg.llm_max_retries),
            "llm_retry_backoff_s": float(self.cfg.llm_retry_backoff_s),
            "max_turns": int(self.cfg.max_turns),
            "max_concurrency": int(self.cfg.max_concurrency),
            "max_resume_attempts": int(self.cfg.max_resume_attempts),
            "full_evidence": bool(self.cfg.full_evidence),
            "refine_rubrics": bool(self.cfg.refine_rubrics),
            "memory": bool(self.cfg.memory),
            "direct_elicit": bool(self.cfg.direct_elicit),
            "early_stop": bool(self.cfg.early_stop),
            "early_stop_mode": list(self.cfg.early_stop_mode),
            "repeated_violation_stop_limit": int(self.cfg.repeated_violation_stop_limit),
            "no_new_violation_round_limit": int(self.cfg.no_new_violation_round_limit),
            "rubrics_refine_max_turns": int(self.cfg.rubrics_refine_max_turns),
            "timer": bool(self.cfg.timer),
            "debug": bool(self.cfg.debug),
            "debug_out_dir": self.cfg.debug_out_dir,
            "retry_num": int(self.cfg.retry_num),
            "fail_fast": bool(self.cfg.fail_fast),
            "fail_threshold": float(self.cfg.fail_threshold),
            "num_ckpts": int(self.cfg.num_ckpts),
            "trial_num": self.cfg.trial_num,
            "merge_progress_path": str(self.dataworker.build_merge_progress_path()),
            "result_path": str(self.dataworker.build_result_path()),
            "run_time": self.cfg.run_time,
            "progress_complete": False,
        }

    def _build_resume_metadata_view(self) -> Dict[str, object]:
        metadata = self._build_base_metadata()
        return {key: metadata.get(key) for key in self._RESUME_MATCH_FIELDS}

    @staticmethod
    def _format_resume_value(value: object) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _normalize_resume_value(key: str, value: object) -> object:
                                                                                 
                                                    
        if key == "direct_elicit" and value is None:
            return False
        return value

    def _validate_resume_metadata(self, saved_metadata: Dict[str, object]) -> None:
        expected = self._build_resume_metadata_view()
        mismatches: List[str] = []
        for key in self._RESUME_MATCH_FIELDS:
            old_value = self._normalize_resume_value(key, saved_metadata.get(key))
            new_value = self._normalize_resume_value(key, expected.get(key))
            if old_value != new_value:
                mismatches.append(
                    f"{key}: progress={self._format_resume_value(old_value)} current={self._format_resume_value(new_value)}"
                )
        if mismatches:
            mismatch_text = "\n- ".join(mismatches)
            raise ValueError(
                "progress metadata mismatch; refusing to resume with the same file.\n- "
                + mismatch_text
            )

    @staticmethod
    def _make_judge_result_slot() -> dict:
        return {
            "status": "pending",
            "prompt": None,
            "raw_response": None,
            "parsed_result": None,
            "error_type": None,
            "error_message": None,
        }

    def _make_stage_progress(self, stage_name: str) -> dict:
        return {
            "status": "pending",
            "prompt": None,
            "per_judge": {
                cfg.name: self._make_judge_result_slot() for cfg in self._get_stage_judge_cfgs(stage_name)
            },
            "final_result": None,
        }

    def _make_turn_record(self, turn_id: int, user_prompt: str) -> dict:
        return {
            "turn_id": int(turn_id),
            "status": "pending",
            "user_prompt": user_prompt,
            "violated_env_items": [],
            "violated_pref_items": [],
            "disclosed_check": {"already_disclosed": [], "newly_seen": []},
            "disclosed_check_by_dimension": {"tools": {"already_disclosed": [], "newly_seen": []}, "prefs": {"already_disclosed": [], "newly_seen": []}},
            "chosen_feedback_type": None,
            "chosen_feedback_items": [],
            "chosen_feedback_dimensions": [],
            "chosen_feedback_items_by_dimension": {"tools": [], "prefs": [], "rubrics": []},
            "counter_snapshot": {},
            "tracker_applied": False,
            "warnings": [],
        }

    @staticmethod
    def _make_agent_side(user_prompt: str) -> dict:
        return {
            "status": "pending",
            "prompt": user_prompt,
            "raw_response": None,
            "history_content": None,
            "error_type": None,
            "error_message": None,
        }

    @staticmethod
    def _make_feedback_side() -> dict:
        return {
            "status": "pending",
            "feedback_type": None,
            "feedback_items": [],
            "repeated_items": [],
            "judge_feedback": None,
            "prompt": None,
            "raw_response": None,
            "user_feedback": None,
            "error_type": None,
            "error_message": None,
        }

    def _ensure_agent_side(self, turn: dict) -> dict:
        agent_side = self._make_agent_side(str(turn.get("user_prompt") or ""))
        agent_side.update(turn.get("agent_side") or {})
        turn["agent_side"] = agent_side
        return agent_side

    def _ensure_judge_stage(self, turn: dict, stage_name: str) -> dict:
        judge_side = turn.setdefault("judge_side", {})
        source_key = stage_name
        if stage_name == "tools" and stage_name not in judge_side and "env" in judge_side:
            source_key = "env"
        stage = self._make_stage_progress(stage_name)
        stage.update(judge_side.get(source_key) or {})
        per_judge = stage.get("per_judge") or {}
        for cfg in self._get_stage_judge_cfgs(stage_name):
            slot = self._make_judge_result_slot()
            slot.update(per_judge.get(cfg.name) or {})
            per_judge[cfg.name] = slot
        stage["per_judge"] = per_judge
        judge_side[stage_name] = stage
        return stage

    def _ensure_feedback_side(self, turn: dict) -> dict:
        feedback_side = self._make_feedback_side()
        feedback_side.update(turn.get("feedback_side") or {})
        turn["feedback_side"] = feedback_side
        return feedback_side

    @classmethod
    def _make_pending_result(cls, query_id: str, query: str, env_profile: dict) -> dict:
        tracker = Tracker(env_profile)
        return {
            "query_id": query_id,
            "query": query,
            "env_profile": env_profile,
            "tracker": tracker.export_state(),
            "no_new_violation_streak": 0,
            "rubrics_refine_active": False,
            "rubrics_refine_turns_used": 0,
            "rubrics_refine_max_turns": 0,
            "first_constraint_clean_rubrics_fail_turn": None,
            "rubrics_refine_bootstrap_pending": False,
            "rubrics_refine_origin_result": None,
            "trajectory": [],
            "result": {
                "status": "pending",
                "stop_reason": "pending",
                "turns": 0,
            },
        }

    def _ensure_progress_entry(self, entry: dict) -> dict:
        query_id = str(entry.get("query_id") or "")
        query = str(entry.get("query") or "")
        env_profile = entry.get("env_profile") or {}
        base = self._make_pending_result(query_id, query, env_profile)
        base.update({k: v for k, v in entry.items() if k not in {"tracker", "trajectory", "result"}})
        base["tracker"] = entry.get("tracker") or base["tracker"]
        base["no_new_violation_streak"] = int(entry.get("no_new_violation_streak", base["no_new_violation_streak"]) or 0)
        base["rubrics_refine_active"] = bool(
            entry.get("rubrics_refine_active", base["rubrics_refine_active"])
        )
        base["rubrics_refine_turns_used"] = int(
            entry.get("rubrics_refine_turns_used", base["rubrics_refine_turns_used"]) or 0
        )
        base["rubrics_refine_max_turns"] = int(
            entry.get("rubrics_refine_max_turns", base["rubrics_refine_max_turns"]) or 0
        )
        first_fail_turn = entry.get(
            "first_constraint_clean_rubrics_fail_turn",
            base["first_constraint_clean_rubrics_fail_turn"],
        )
        base["first_constraint_clean_rubrics_fail_turn"] = (
            int(first_fail_turn) if first_fail_turn is not None else None
        )
        base["rubrics_refine_bootstrap_pending"] = bool(
            entry.get(
                "rubrics_refine_bootstrap_pending",
                base["rubrics_refine_bootstrap_pending"],
            )
        )
        base["rubrics_refine_origin_result"] = copy.deepcopy(
            entry.get("rubrics_refine_origin_result")
        ) if entry.get("rubrics_refine_origin_result") is not None else base["rubrics_refine_origin_result"]
        base["trajectory"] = list(entry.get("trajectory") or [])
        base["result"] = entry.get("result") or base["result"]
        return base

    def _write_progress_checkpoint(self) -> None:
        self.dataworker.dump_progress(self.build_current_payload())

    def _write_query_checkpoint(self, query_id: str) -> None:
        idx = self._query_index_by_id.get(query_id)
        if idx is None:
            return
        entry = self._all_results_by_id.get(query_id)
        if entry is None:
            return
        self.dataworker.dump_run_query(entry, idx=idx)

    def _write_index_checkpoint(self) -> None:
        self.dataworker.dump_run_index_and_summary(self.build_current_payload())

    def _record_timer(self, role: str, model_label: str, duration_s: float) -> None:
        self.timer.record(role, model_label, duration_s)

    def _timed_call(self, role: str, model_label: str, fn, *args, **kwargs):
        return self.timer.timed_call(role, model_label, fn, *args, **kwargs)

    def get_timer_summary(self) -> List[dict]:
        return self.timer.summary_rows()

    def print_timer_summary(self) -> None:
        self.timer.print_summary()

    def build_current_payload(self) -> dict:
        metadata = dict(self._checkpoint_metadata or {})
        metadata.update(self._build_outcome_stats())
        data = [self._all_results_by_id[qid] for qid in self._ordered_query_ids]
        return {"metadata": metadata, "data": data}

    def _build_outcome_stats(self) -> Dict[str, object]:
        success_count = 0
        failed_count = 0
        early_stopped_count = 0
        finished_turns: List[int] = []
        remaining_query_count = 0

        for qid in self._ordered_query_ids:
            entry = self._all_results_by_id.get(qid) or {}
            result = entry.get("result") or {}
            status = str(result.get("status") or "")
            turns = int(result.get("turns") or 0)
            stop_reason = str(result.get("stop_reason") or "")

            if status in self._RERUN_STATUSES:
                remaining_query_count += 1
            if status in self._TERMINAL_STATUSES:
                finished_turns.append(turns)
            if status == "success":
                success_count += 1
            elif status == "failed":
                failed_count += 1
            elif status == "stopped" and stop_reason.startswith("early_stop"):
                early_stopped_count += 1

        finished_query_count = len(finished_turns)
        avg_turns_finished = (
            float(sum(finished_turns)) / float(finished_query_count)
            if finished_query_count > 0
            else 0.0
        )

        return {
            "finished_query_count": int(finished_query_count),
            "remaining_query_count": int(remaining_query_count),
            "avg_turns_finished_queries": avg_turns_finished,
            "success_query_count": int(success_count),
            "failed_query_count": int(failed_count),
            "early_stopped_query_count": int(early_stopped_count),
        }

    def _pending_query_entries_from_store(self) -> List[dict]:
        out: List[dict] = []
        for qid in self._ordered_query_ids:
            entry = self._all_results_by_id[qid]
            status = (entry.get("result") or {}).get("status")
            if status not in self._RERUN_STATUSES:
                continue
            out.append(
                {
                    "query_id": qid,
                    "query": str(entry.get("query") or ""),
                    "_runtime_env_profile": entry.get("env_profile") or {},
                }
            )
        return out

    def _turn_is_constraint_clean_rubrics_fail(self, turn: dict) -> bool:
        if not isinstance(turn, dict):
            return False
        judge_side = turn.get("judge_side") or {}
        tools_final = ((judge_side.get("tools") or {}).get("final_result")) or {"violation": False}
        prefs_final = ((judge_side.get("prefs") or {}).get("final_result")) or {"violation": False}
        rubrics_final = ((judge_side.get("rubrics") or {}).get("final_result")) or {"passed": True}
        tools_clean = (not self._dimension_enabled("tools")) or (not bool(tools_final.get("violation")))
        prefs_clean = (not self._dimension_enabled("prefs")) or (not bool(prefs_final.get("violation")))
        rubrics_fail = not bool(rubrics_final.get("passed", True))
        return tools_clean and prefs_clean and rubrics_fail

    def _find_first_constraint_clean_rubrics_fail_turn(self, trajectory: List[dict]) -> Optional[int]:
        for idx, turn in enumerate(trajectory, start=1):
            if self._turn_is_constraint_clean_rubrics_fail(turn):
                return idx
        return None

    def _eligible_for_rubrics_refine_reopen(self, entry: dict) -> bool:
        result = entry.get("result") or {}
        if str(result.get("status") or "") != "failed":
            return False
        trajectory = list(entry.get("trajectory") or [])
        if not trajectory:
            return False
        return self._turn_is_constraint_clean_rubrics_fail(trajectory[-1])

    def _reopen_entry_for_rubrics_refine(self, entry: dict) -> dict:
        reopened = self._ensure_progress_entry(copy.deepcopy(entry))
        if reopened.get("rubrics_refine_origin_result") is None:
            reopened["rubrics_refine_origin_result"] = copy.deepcopy(reopened.get("result") or {})
        reopened["rubrics_refine_active"] = True
        reopened["rubrics_refine_turns_used"] = 0
        reopened["rubrics_refine_max_turns"] = int(self.cfg.rubrics_refine_max_turns)
        reopened["first_constraint_clean_rubrics_fail_turn"] = self._find_first_constraint_clean_rubrics_fail_turn(
            list(reopened.get("trajectory") or [])
        )
        reopened["rubrics_refine_bootstrap_pending"] = True
        reopened["result"] = {
            "status": "pending",
            "stop_reason": "rubrics_refine_reopened",
            "turns": len(reopened.get("trajectory") or []),
        }
        return reopened

    def _initialize_rubrics_refine_payload_from_source(self) -> Optional[dict]:
        source_dir_raw = self.cfg.rubrics_refine_continue_from
        if not source_dir_raw:
            return None

        source_dir = Path(source_dir_raw)
        source_payload = self.dataworker.load_external_progress(source_dir)
        if source_payload is None:
            raise FileNotFoundError(
                f"Could not find source result folder for rubrics refine continuation under {source_dir}"
            )
        source_result = self.dataworker.load_external_result(source_dir)

        source_data = source_payload.get("data") or []
        if not isinstance(source_data, list):
            raise ValueError("source result-folder payload['data'] must be a list")

        copied_entries: List[dict] = []
        reopened_count = 0
        for raw_entry in source_data:
            entry = self._ensure_progress_entry(copy.deepcopy(raw_entry))
            if self._eligible_for_rubrics_refine_reopen(entry):
                entry = self._reopen_entry_for_rubrics_refine(entry)
                reopened_count += 1
            copied_entries.append(entry)

        self._ordered_query_ids = [str(e.get("query_id") or "") for e in copied_entries]
        self._query_index_by_id = {qid: idx for idx, qid in enumerate(self._ordered_query_ids)}
        self._all_results_by_id = {
            str(e.get("query_id") or ""): e
            for e in copied_entries
        }
        self._checkpoint_metadata = self._build_base_metadata()
        self._checkpoint_metadata.update(
            {
                "total_query_count": len(self._ordered_query_ids),
                "remaining_query_count": reopened_count,
                "resume_passes_completed": 0,
                "progress_complete": False,
                "rubrics_refine_initialized_from": str(source_dir),
                "rubrics_refine_reopened_query_count": int(reopened_count),
            }
        )

        payload = self.build_current_payload()
        self.dataworker.dump_progress(payload)
        copied_result_payload = {
            "metadata": dict(payload["metadata"]),
            "data": payload["data"],
        }
        if source_result is not None:
            copied_result_payload["metadata"]["source_result_metadata"] = source_result.get("metadata")
        self.dataworker.dump_results(copied_result_payload)

        self.query_entries = self._pending_query_entries_from_store()
        print(
            f"[run] rubrics_refine init: copied {len(copied_entries)} queries from {source_dir}; "
            f"reopened {reopened_count} failed queries"
        )
        return payload

    def prepare(self) -> List[dict]:
        self.dataworker.validate_query_path(self.cfg.query_path)
        query_entries = self.dataworker.load_queries()
        if self.cfg.trial_num is not None:
            query_entries = query_entries[: int(self.cfg.trial_num)]
            print(f"[run] trial_num={self.cfg.trial_num}: truncated to {len(query_entries)} queries")

        env_profiles = self.merger.ensure_profiles(query_entries)
        if len(env_profiles) != len(query_entries):
            raise RuntimeError("env_profiles length mismatch after prepare")

        query_entries_with_profiles: List[dict] = []
        for entry, profile in zip(query_entries, env_profiles):
            scoped_profile = self._apply_ban_scope_to_profile(profile)
            entry["_runtime_env_profile"] = scoped_profile
            query_entries_with_profiles.append(entry)

        progress_payload = self.dataworker.load_progress()
        if progress_payload is None and self.cfg.rubrics_refine_continue_from:
            progress_payload = self._initialize_rubrics_refine_payload_from_source()
        if progress_payload is not None:
            saved_metadata = progress_payload.get("metadata") or {}
            if not isinstance(saved_metadata, dict):
                raise ValueError("progress payload['metadata'] must be a dict")
            self._validate_resume_metadata(saved_metadata)

            existing_data = progress_payload.get("data") or []
            if not isinstance(existing_data, list):
                raise ValueError("progress payload['data'] must be a list")

            self._ordered_query_ids = [str(e.get("query_id") or "") for e in existing_data]
            self._query_index_by_id = {qid: idx for idx, qid in enumerate(self._ordered_query_ids)}
            self._all_results_by_id = {
                str(e.get("query_id") or ""): self._ensure_progress_entry(e)
                for e in existing_data
            }
            self._checkpoint_metadata = saved_metadata or self._build_base_metadata()

            rerun_entries = self._pending_query_entries_from_store()
            self.query_entries = rerun_entries
            print(
                f"[run] resume mode: {len(rerun_entries)}/{len(existing_data)} queries to re-run"
            )
            return rerun_entries

        self._ordered_query_ids = []
        self._query_index_by_id = {}
        self._all_results_by_id = {}
        for entry in query_entries_with_profiles:
            qid = str(entry.get("query_id") or "")
            query = str(entry.get("query") or "")
            self._ordered_query_ids.append(qid)
            self._all_results_by_id[qid] = self._make_pending_result(
                qid,
                query,
                entry.get("_runtime_env_profile") or {},
            )
        self._query_index_by_id = {qid: idx for idx, qid in enumerate(self._ordered_query_ids)}

        self._checkpoint_metadata = self._build_base_metadata()
        self._checkpoint_metadata["total_query_count"] = len(self._ordered_query_ids)
        self._checkpoint_metadata["remaining_query_count"] = len(self._ordered_query_ids)
        self._write_progress_checkpoint()

        self.query_entries = [
            {
                "query_id": str(entry.get("query_id") or ""),
                "query": str(entry.get("query") or ""),
                "_runtime_env_profile": entry.get("_runtime_env_profile") or {},
            }
            for entry in query_entries_with_profiles
        ]
        return self.query_entries

    def run(self) -> dict:
        total_queries = len(self._ordered_query_ids)
        total_submitted = 0
        total_completed = 0
        any_fail_fast_triggered = False
        completed = False

        current_entries = list(self.query_entries)
        pass_index = 0

        while current_entries:
            submitted, completed_count, fail_fast_triggered = self._run_one_pass(
                current_entries,
                pass_index=pass_index,
            )
            total_submitted += submitted
            total_completed += completed_count
            any_fail_fast_triggered = any_fail_fast_triggered or fail_fast_triggered

            remaining_entries = self._pending_query_entries_from_store()
            if not remaining_entries:
                completed = True
                break

            pass_index += 1
            if pass_index > int(self.cfg.max_resume_attempts):
                break
            current_entries = remaining_entries

        remaining_count = len(self._pending_query_entries_from_store())
        metadata = self._build_base_metadata()
        metadata.update(
            {
                "submitted_query_count": int(total_submitted),
                "completed_query_count": int(total_completed),
                "total_query_count": int(total_queries),
                "remaining_query_count": int(remaining_count),
                "resume_passes_completed": int(pass_index),
                "fail_fast_triggered": bool(any_fail_fast_triggered),
                "progress_complete": bool(completed),
            }
        )
        self._checkpoint_metadata = metadata
        self._write_progress_checkpoint()

        return self.build_current_payload()

    def _run_one_pass(
        self,
        query_entries: List[dict],
        *,
        pass_index: int,
    ) -> Tuple[int, int, bool]:
        total = len(query_entries)
        if total == 0:
            return 0, 0, False

        checkpoint_interval = max(1, total // int(self.cfg.num_ckpts)) if total > 0 else 1
        max_workers = max(1, min(int(self.cfg.max_concurrency), total))

        failed_count = 0
        submitted_count = 0
        completed_count = 0
        fail_fast_triggered = False
        stop_event = threading.Event()
        progress = None
        next_idx = 0
        future_to_idx: Dict[Future, int] = {}

        if tqdm is not None:
            progress = tqdm(
                total=total,
                desc=f"runtime[{self.cfg.model}]/pass{pass_index}",
                unit="query",
            )

        executor = ThreadPoolExecutor(max_workers=max_workers)
        try:
            def submit_more() -> None:
                nonlocal next_idx, submitted_count
                while (
                    not stop_event.is_set()
                    and next_idx < total
                    and len(future_to_idx) < max_workers
                ):
                    fut = executor.submit(self._run_single_query, query_entries[next_idx])
                    future_to_idx[fut] = next_idx
                    next_idx += 1
                    submitted_count += 1

            submit_more()

            while future_to_idx:
                done_set, _ = wait(
                    list(future_to_idx.keys()),
                    return_when=FIRST_COMPLETED,
                )

                for fut in done_set:
                    idx = future_to_idx.pop(fut)
                    query_entry = query_entries[idx]
                    qid = str(query_entry.get("query_id") or "")
                    try:
                        result = fut.result()
                    except Exception as exc:                    
                        result = self._make_error_result_from_exception(query_entry, exc)

                    with self.state_lock:
                        self._all_results_by_id[qid] = result
                        self._write_query_checkpoint(qid)
                    completed_count += 1

                    status = (result.get("result") or {}).get("status")
                    if status == "error":
                        failed_count += 1

                    if progress is not None:
                        progress.update(1)

                    if completed_count % checkpoint_interval == 0:
                        with self.state_lock:
                            self._write_index_checkpoint()

                    if self._should_trigger_fail_fast(failed_count, total):
                        fail_fast_triggered = True
                        stop_event.set()

                if stop_event.is_set():
                    for fut, fut_idx in list(future_to_idx.items()):
                        if fut.cancel():
                            entry = query_entries[fut_idx]
                            qid = str(entry.get("query_id") or "")
                            skipped = self._mark_query_result_status(
                                self._all_results_by_id[qid],
                                status="skipped",
                                stop_reason="fail_fast_not_submitted",
                            )
                            with self.state_lock:
                                self._all_results_by_id[qid] = skipped
                                self._write_query_checkpoint(qid)
                            future_to_idx.pop(fut, None)
                    while next_idx < total:
                        entry = query_entries[next_idx]
                        qid = str(entry.get("query_id") or "")
                        skipped = self._mark_query_result_status(
                            self._all_results_by_id[qid],
                            status="skipped",
                            stop_reason="fail_fast_not_submitted",
                        )
                        with self.state_lock:
                            self._all_results_by_id[qid] = skipped
                            self._write_query_checkpoint(qid)
                        next_idx += 1
                                                                                      
                                                                              
                    continue

                submit_more()
        finally:
            executor.shutdown(wait=True, cancel_futures=False)
            if progress is not None:
                progress.close()

        with self.state_lock:
            self._write_index_checkpoint()

        return submitted_count, completed_count, fail_fast_triggered

    def _make_error_result_from_exception(self, query_entry: dict, exc: Exception) -> dict:
        qid = str(query_entry.get("query_id") or "")
        existing = copy.deepcopy(self._all_results_by_id.get(qid) or self._make_pending_result(
            qid,
            str(query_entry.get("query") or ""),
            query_entry.get("_runtime_env_profile") or {},
        ))
        existing["result"] = {
            "status": "error",
            "stop_reason": "runner_exception",
            "turns": len(existing.get("trajectory") or []),
        }
        existing["error_type"] = type(exc).__name__
        existing["error_message"] = str(exc)
        existing["error_stage"] = "_run_single_query"
        return existing

    def _should_trigger_fail_fast(self, failed_count: int, total_count: int) -> bool:
        if not self.cfg.fail_fast:
            return False
        if total_count <= 0:
            return False
        return float(failed_count) / float(total_count) >= float(self.cfg.fail_threshold)

    def _check_early_stop(self, tracker: Tracker, *, no_new_violation_streak: int) -> Optional[str]:
        if not self.cfg.early_stop:
            return None
        modes = set(self.cfg.early_stop_mode)
        if "repeated_violation" in modes:
            totals = tracker.sum_disclosed_violations()
            total_tool = totals["tools"]
            total_pref = totals["prefs"]
            limit = int(self.cfg.repeated_violation_stop_limit)
            if total_tool >= limit:
                return f"early_stop due to repeated violation {total_tool} (tool constraint)"
            if total_pref >= limit:
                return f"early_stop due to repeated violation {total_pref} (user prefs)"
        if "no_new_violation" in modes and int(no_new_violation_streak) >= int(
            self.cfg.no_new_violation_round_limit
        ):
            return (
                "early_stop due to no new tool/prefs violations for "
                f"{int(no_new_violation_streak)} consecutive turns"
            )
        return None

    def _update_no_new_violation_streak(
        self,
        current_streak: int,
        *,
        env_newly_seen: Optional[List[str]] = None,
        prefs_newly_seen: Optional[List[str]] = None,
    ) -> int:
        had_new = bool(env_newly_seen or prefs_newly_seen)
        return 0 if had_new else int(current_streak) + 1

    def _call_agent(self, messages: List[Dict[str, str]]) -> str:
        return self._timed_call(
            "agent",
            self.model_cfg.name,
            openai_chat_request,
            provider=self.model_cfg.provider,
            base_url=self.model_cfg.base_url,
            api_key=self.model_api_key,
            model_id=self.model_cfg.model_id,
            model_name=self.model_cfg.name,
            messages=messages,
            temperature=float(self.cfg.model_temperature),
            max_tokens=int(self.cfg.model_max_tokens),
            timeout_s=int(self.cfg.llm_timeout_s),
            max_retries=int(self.cfg.llm_max_retries),
            retry_backoff_s=float(self.cfg.llm_retry_backoff_s),
        )

    @staticmethod
    def _format_numbered_list(items: List[str]) -> Tuple[str, Dict[int, str]]:
        clean = [str(x).strip() for x in items if str(x).strip()]
        mapping = {idx + 1: item for idx, item in enumerate(clean)}
        if not clean:
            return "None", mapping
        text = "\n".join(f"{idx}. {val}" for idx, val in mapping.items())
        return text, mapping

    def _write_query_debug(self, query_id: str, payload: dict) -> None:
        if not self.cfg.debug or not self.cfg.debug_out_dir:
            return
        out_dir = Path(self.cfg.debug_out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        name = f"debug_{self._safe_file_token(query_id)}.jsonl"
        path = out_dir / name
        line = json.dumps(payload, ensure_ascii=False)
        with self.debug_lock:
            with path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

    def _map_constraint_numbers_to_items_1based(
        self,
        numbers: List[int],
        source_items: List[str],
        *,
        raw_marked_items: Optional[List[str]] = None,
    ) -> Tuple[List[str], List[str]]:
        warnings: List[str] = []
        mapped: List[str] = []
        seen = set()

        for n in numbers:
            if n < 1 or n > len(source_items):
                warnings.append(f"out_of_range_constraint_number:{n}")
                continue
            item = source_items[n - 1]
            key = item.casefold()
            if key in seen:
                continue
            seen.add(key)
            mapped.append(item)

        if not mapped and raw_marked_items:
            norm_to_item = {item.casefold(): item for item in source_items}
            for token in raw_marked_items:
                cleaned = re.sub(r"^\s*\d+[\.\)\]:-]?\s*", "", str(token).strip())
                norm = cleaned.casefold()
                if norm in norm_to_item and norm not in seen:
                    seen.add(norm)
                    mapped.append(norm_to_item[norm])

        return mapped, warnings

    def _map_named_items_to_canonical(
        self,
        raw_items: List[str],
        source_items: List[str],
    ) -> Tuple[List[str], List[str]]:
        warnings: List[str] = []
        mapped: List[str] = []
        seen = set()
        norm_to_item = {item.casefold(): item for item in source_items}
        for token in raw_items:
            cleaned = re.sub(r"^\s*\d+[\.\)\]:-]?\s*", "", str(token).strip())
            norm = cleaned.casefold()
            if not norm:
                continue
            item = norm_to_item.get(norm)
            if item is None:
                warnings.append(f"unmapped_named_item:{cleaned}")
                continue
            key = item.casefold()
            if key in seen:
                continue
            seen.add(key)
            mapped.append(item)
        return mapped, warnings

    def _select_dimension_feedback_items(self, stage_name: str, items: List[str]) -> List[str]:
        normalized = self._normalize_items(items)
        if not normalized:
            return []
        if stage_name == "rubrics":
            if self.cfg.full_evidence:
                return normalized
            return [normalized[0]]
        if self.cfg.full_evidence:
            return normalized
        return [self._stable_pick_one(normalized)]

    @staticmethod
    def _stable_pick_one(items: List[str]) -> str:
        if not items:
            raise ValueError("_stable_pick_one received empty items")
        digest = hashlib.sha256("\n".join(items).encode("utf-8")).hexdigest()
        idx = int(digest, 16) % len(items)
        return items[idx]

    def _build_memory_block(self, tracker: Tracker) -> str:
        if not self.cfg.memory:
            return ""
        response_dimensions = self._response_dimension_set()
        disclosed = tracker.get_disclosed_constraints()
        disclosed_tools = disclosed.get("tools") or []
        disclosed_prefs = disclosed.get("prefs") or []

        tools_text = "None" if not disclosed_tools else "\n".join(f"- {x}" for x in disclosed_tools)
        prefs_text = "None" if not disclosed_prefs else "\n".join(f"- {x}" for x in disclosed_prefs)
        tools_memory = run_prompts.tools_memory if self._ban_tools_enabled() and "tools" in response_dimensions else ""
        prefs_memory = run_prompts.prefs_memory if self._ban_prefs_enabled() and "prefs" in response_dimensions else ""
        tools_in_memory = bool(tools_memory)
        prefs_in_memory = bool(prefs_memory)
        if tools_in_memory and prefs_in_memory:
            memory_scope_hint = "the environment constraints and the user's preferences"
        elif tools_in_memory:
            memory_scope_hint = "the environment constraints"
        elif prefs_in_memory:
            memory_scope_hint = "the user's preferences"
        else:
            return ""
        if not tools_in_memory:
            tools_text = ""
        if not prefs_in_memory:
            prefs_text = ""

        return format_prompt(
            run_prompts.memory,
            {
                "memory_scope_hint": memory_scope_hint,
                "tools_memory": tools_memory,
                "disclosed_tools": tools_text,
                "prefs_memory": prefs_memory,
                "disclosed_prefs": prefs_text,
            },
        )

    def _build_agent_runtime_prompt(self, user_prompt: str, tracker: Tracker) -> str:
        pass                                         

                                                                                    
                                                                                  
           
        base = str(user_prompt or "").strip()
        memory_block = self._build_memory_block(tracker).strip()
        if not memory_block:
            return base
        if not base:
            return memory_block
        return f"{base}\n\n{memory_block}"

    @staticmethod
    def _build_direct_elicit_feedback(judge_feedback: str) -> str:
        format_suffix = str(run_prompts.agent_response_format or "").strip()
        return format_prompt(
            run_prompts.direct_elicit_feedback_prompt,
            {
                "judge_feedback": judge_feedback or "None",
                "Judge_feedback": judge_feedback or "None",
                "agent_response_format": format_suffix,
                "Agent_response_format": format_suffix,
            },
        ).strip()

    def _build_judge_feedback_text(
        self,
        feedback_type: Optional[str],
        feedback_items: List[str],
        repeated_items: Optional[List[str]] = None,
    ) -> str:
        items_text = "\n".join(f"- {item}" for item in feedback_items) if feedback_items else "None"
        repeated_items = repeated_items or []
        if feedback_type == "env":
            if repeated_items:
                repeat_sub = format_prompt(
                    run_prompts.env_cons_repeat_violation_template,
                    {"repeatedly_violated_tools": "\n".join(f"- {x}" for x in repeated_items)},
                )
            else:
                repeat_sub = ""
            return format_prompt(
                run_prompts.judge_feedback_template_env_cons,
                {"absent_tools": items_text, "env_cons_repeat_violation_template": repeat_sub},
            )
        if feedback_type == "prefs":
            if repeated_items:
                repeat_sub = format_prompt(
                    run_prompts.user_prefs_repeat_violation_template,
                    {"repeatedly_violated_prefs": "\n".join(f"- {x}" for x in repeated_items)},
                )
            else:
                repeat_sub = ""
            return format_prompt(
                run_prompts.judge_feedback_template_user_prefs,
                {"contradicted_prefs": items_text, "user_prefs_repeat_violation_template": repeat_sub},
            )
        return items_text

    def _build_combined_judge_feedback(
        self,
        *,
        tools_feedback: Optional[str] = None,
        prefs_feedback: Optional[str] = None,
        rubrics_feedback: Optional[str] = None,
    ) -> str:
        blocks: List[str] = []
        if tools_feedback:
            blocks.append("[Tool Constraints Feedback]\n" + tools_feedback.strip())
        if prefs_feedback:
            blocks.append("[User Preferences Feedback]\n" + prefs_feedback.strip())
        if rubrics_feedback:
            blocks.append("[Rubrics Feedback]\n" + rubrics_feedback.strip())
        return "\n\n".join(blocks).strip()

    def _build_rubrics_feedback_text(
        self,
        failed_rubrics: List[str],
        reasons: Dict[str, str],
        scores_by_rubric: Dict[str, float],
    ) -> str:
        lines = []
        for rubric in failed_rubrics:
            score = float(scores_by_rubric.get(rubric, 5))
            if score < 2:
                template = run_prompts.rubrics_feedback_template_score_1
            elif score < 3:
                template = run_prompts.rubrics_feedback_template_score_2
            elif score < 4:
                template = run_prompts.rubrics_feedback_template_score_3
            else:
                template = run_prompts.rubrics_feedback_template_score_4
            reason = str(reasons.get(rubric) or "").strip()
            reason_clause = f" {reason}" if reason else ""
            lines.append(
                format_prompt(
                    template,
                    {
                        "rubric": rubric,
                        "reason_clause": reason_clause,
                    },
                )
            )
        text = "\n".join(lines) if lines else "None"
        return format_prompt(
            run_prompts.judge_feedback_template_rubrics,
            {"failed_rubrics_with_reasons": text},
        )

    def _generate_feedback_message(
        self,
        *,
        query: str,
        plan: str,
        judge_feedback: str,
        tracker: Tracker,
        response_dimensions: set[str],
    ) -> Tuple[str, Optional[str], Optional[str]]:
        if self.cfg.direct_elicit:
            user_feedback = self._build_direct_elicit_feedback(judge_feedback)
            return user_feedback, user_feedback, None

        memory_block = self._build_memory_block(tracker)
        feedback_scope = self._build_feedback_prompt_scope_fields()
        refine_block = run_prompts.refine_rubrics if "rubrics" in response_dimensions else ""
        user_feedback = self._timed_call(
            "user_feedback",
            self.gen_cfg.name,
            self.judger.generate_user_feedback,
            query=query,
            plan=plan,
            judge_feedback=judge_feedback,
            memory=memory_block,
            refine_rubrics=refine_block,
            tools_placeholder=feedback_scope["tools_placeholder"],
            prefs_placeholder=feedback_scope["prefs_placeholder"],
        )
        return user_feedback, self.judger.last_feedback_prompt, self.judger.last_feedback_raw

    def _bootstrap_rubrics_refine_feedback(
        self,
        *,
        query: str,
        query_id: str,
        tracker: Tracker,
        trajectory: List[dict],
        current_user_prompt: str,
        existing: dict,
        no_new_violation_streak: int,
    ) -> Tuple[List[dict], str]:
        if not trajectory:
            raise ValueError("Cannot bootstrap rubrics refine feedback without a prior turn")

        last_turn = trajectory[-1]
        rubrics_final = (((last_turn.get("judge_side") or {}).get("rubrics") or {}).get("final_result")) or {}
        rubrics_feedback_items = self._select_dimension_feedback_items(
            "rubrics",
            list(rubrics_final.get("failed_rubrics") or []),
        )
        rubrics_feedback_text = self._build_rubrics_feedback_text(
            rubrics_feedback_items,
            rubrics_final.get("reasons_by_rubric") or {},
            rubrics_final.get("scores_by_rubric") or {},
        )
        judge_feedback = self._build_combined_judge_feedback(rubrics_feedback=rubrics_feedback_text) or "None"
        feedback_side = self._ensure_feedback_side(last_turn)
        feedback_side["feedback_type"] = "rubrics"
        feedback_side["feedback_items"] = list(rubrics_feedback_items)
        feedback_side["repeated_items"] = []
        feedback_side["judge_feedback"] = judge_feedback

        try:
            user_feedback, prompt_text, raw_response = self._generate_feedback_message(
                query=query,
                plan=self._extract_plan_from_answer_start(str((last_turn.get("agent_side") or {}).get("raw_response") or "")),
                judge_feedback=judge_feedback,
                tracker=tracker,
                response_dimensions=self._response_dimension_set() | {"rubrics"},
            )
        except Exception as exc:
            feedback_side["status"] = "error"
            feedback_side["error_type"] = type(exc).__name__
            feedback_side["error_message"] = str(exc)
            existing["rubrics_refine_bootstrap_pending"] = True
            self._persist_query_progress(
                existing,
                tracker=tracker,
                trajectory=trajectory,
                no_new_violation_streak=no_new_violation_streak,
            )
            existing["result"] = {
                "status": "error",
                "stop_reason": "rubrics_refine_bootstrap_error",
                "turns": len(trajectory),
            }
            self._write_query_debug(query_id, {"stage": "rubrics_refine_bootstrap_error", "turn": last_turn})
            raise

        feedback_side["status"] = "success"
        feedback_side["prompt"] = prompt_text
        feedback_side["raw_response"] = raw_response
        feedback_side["user_feedback"] = user_feedback
        feedback_side["error_type"] = None
        feedback_side["error_message"] = None
        last_turn["feedback_side"] = feedback_side
        existing["rubrics_refine_bootstrap_pending"] = False
        return trajectory, str(user_feedback or current_user_prompt)

    def _compute_rubrics_pass(self, scores_by_rubric: Dict[str, float]) -> Tuple[bool, Optional[float]]:
        active_scores = [
            float(score)
            for rubric, score in scores_by_rubric.items()
            if rubric not in self._NON_FAILING_RUBRICS
        ]
        if not active_scores:
            return True, None
        if self.cfg.rubrics_pass_mode == "mean":
            metric = float(sum(active_scores)) / float(len(active_scores))
            return metric >= float(self.cfg.rubrics_pass_threshold), metric
        metric = min(active_scores)
        return metric >= float(self.cfg.rubrics_pass_threshold), metric

    def _extract_plan_from_answer_start(self, plan: str) -> str:
        text = str(plan or "")
        idx = text.lower().find("<answer_start>")
        if idx == -1:
            return text
        return text[idx:]

    def _has_answer_start(self, plan: str) -> bool:
        return "<answer_start>" in str(plan or "").lower()

    def _truncate_plan_for_history(self, plan: str) -> str:
        return self._extract_plan_from_answer_start(plan)

    def _mark_query_result_status(self, entry: dict, *, status: str, stop_reason: str) -> dict:
        out = copy.deepcopy(entry)
        out["result"] = {
            "status": status,
            "stop_reason": stop_reason,
            "turns": len(out.get("trajectory") or []),
        }
        out["tracker"] = out.get("tracker") or {}
        out["trajectory"] = out.get("trajectory") or []
        return out

    def _build_stage_prompt(
        self,
        *,
        stage_name: str,
        query: str,
        plan: str,
        constraints_text: Optional[str] = None,
    ) -> str:
        if stage_name == "tools":
            return format_prompt(
                run_prompts.judge_by_env_cons_prompt,
                {
                    "query": query,
                    "Query": query,
                    "plan": plan,
                    "Plan": plan,
                    "banned_tools": str(constraints_text or "None"),
                    "BANNED_TOOLS": str(constraints_text or "None"),
                },
            )
        if stage_name == "prefs":
            return format_prompt(
                run_prompts.judge_by_user_prefs_prompt,
                {
                    "query": query,
                    "Query": query,
                    "plan": plan,
                    "Plan": plan,
                    "user_prefs": str(constraints_text or "None"),
                    "USER_PREFS": str(constraints_text or "None"),
                },
            )
        if stage_name == "rubrics":
            return format_prompt(
                run_prompts.judge_by_rubrics_prompt,
                {
                    "query": query,
                    "Query": query,
                    "plan": plan,
                    "Plan": plan,
                },
            )
        raise ValueError(f"Unknown stage_name: {stage_name}")

    def _persist_query_progress(
        self,
        entry: dict,
        *,
        tracker: Tracker,
        trajectory: List[dict],
        no_new_violation_streak: int,
    ) -> None:
        entry["tracker"] = tracker.export_state()
        entry["no_new_violation_streak"] = int(no_new_violation_streak)
        entry["trajectory"] = trajectory
        entry["rubrics_refine_active"] = bool(entry.get("rubrics_refine_active", False))
        entry["rubrics_refine_turns_used"] = int(entry.get("rubrics_refine_turns_used", 0) or 0)
        entry["rubrics_refine_max_turns"] = int(entry.get("rubrics_refine_max_turns", 0) or 0)
        first_fail_turn = entry.get("first_constraint_clean_rubrics_fail_turn")
        entry["first_constraint_clean_rubrics_fail_turn"] = (
            int(first_fail_turn) if first_fail_turn is not None else None
        )
        entry["rubrics_refine_bootstrap_pending"] = bool(
            entry.get("rubrics_refine_bootstrap_pending", False)
        )

    def _ensure_turn_record(self, turn: Optional[dict], *, turn_id: int, user_prompt: str) -> dict:
        base = self._make_turn_record(turn_id, user_prompt)
        if not isinstance(turn, dict):
            return base
        base.update({k: v for k, v in turn.items() if k not in {"agent_side", "judge_side", "feedback_side"}})
        if not base.get("user_prompt"):
            base["user_prompt"] = user_prompt
        if "agent_side" in turn:
            agent_side = self._make_agent_side(str(base.get("user_prompt") or ""))
            agent_side.update(turn.get("agent_side") or {})
            base["agent_side"] = agent_side
        if "judge_side" in turn:
            base["judge_side"] = {}
            judge_side = turn.get("judge_side") or {}
            for stage_name in self._all_dimension_names():
                source_key = stage_name
                if stage_name == "tools" and stage_name not in judge_side and "env" in judge_side:
                    source_key = "env"
                if source_key not in judge_side:
                    continue
                stage = self._make_stage_progress(stage_name)
                stage.update(judge_side.get(source_key) or {})
                per_judge = stage.get("per_judge") or {}
                for cfg in self._get_stage_judge_cfgs(stage_name):
                    slot = self._make_judge_result_slot()
                    slot.update(per_judge.get(cfg.name) or {})
                    per_judge[cfg.name] = slot
                stage["per_judge"] = per_judge
                base["judge_side"][stage_name] = stage
        if "feedback_side" in turn:
            feedback_side = self._make_feedback_side()
            feedback_side.update(turn.get("feedback_side") or {})
            base["feedback_side"] = feedback_side
        return base

    def _restore_query_progress(
        self,
        query: str,
        env_profile: dict,
        progress_entry: dict,
    ) -> Tuple[Tracker, List[dict], List[Dict[str, str]], str, int, int]:
        tracker = Tracker.from_exported_state(env_profile, progress_entry.get("tracker"))
        no_new_violation_streak = int(progress_entry.get("no_new_violation_streak", 0) or 0)
        stored_trajectory = list(progress_entry.get("trajectory") or [])

        env_prompt_template = run_prompts.Env_prompt_router.get(self.cfg.domain)
        if env_prompt_template is None:
            raise ValueError(f"No Env prompt found for domain={self.cfg.domain}")
        initial_user_prompt = format_prompt(
            env_prompt_template,
            {
                "query": query,
                "Query": query,
                "ban_scope_hint": self._build_ban_scope_hint(),
            },
        )

        history: List[Dict[str, str]] = []
        current_user_prompt = initial_user_prompt
        restored_trajectory: List[dict] = []
        resume_index = len(stored_trajectory)

        for idx, raw_turn in enumerate(stored_trajectory):
            turn = self._ensure_turn_record(raw_turn, turn_id=idx + 1, user_prompt=current_user_prompt)
            restored_trajectory.append(turn)
            if turn.get("status") != "success":
                resume_index = idx
                break

            history.append({"role": "user", "content": turn.get("user_prompt") or current_user_prompt})
            history.append(
                {
                    "role": "assistant",
                    "content": turn["agent_side"].get("history_content")
                    or turn["agent_side"].get("raw_response")
                    or "",
                }
            )
            feedback_side = turn.get("feedback_side") or {}
            if feedback_side.get("status") == "success" and feedback_side.get("user_feedback"):
                current_user_prompt = str(feedback_side["user_feedback"])

        return tracker, restored_trajectory, history, current_user_prompt, resume_index, no_new_violation_streak

    def _normalize_items(self, items: Sequence[str]) -> List[str]:
        seen = set()
        out: List[str] = []
        for item in items:
            text = str(item).strip()
            if not text:
                continue
            key = text.casefold()
            if key in seen:
                continue
            seen.add(key)
            out.append(text)
        return out

    def _merge_item_sets(self, item_lists: List[List[str]], *, stage_name: str) -> List[str]:
        if not item_lists:
            return []
        normalized = [self._normalize_items(items) for items in item_lists]
        if self._get_stage_merge_mode(stage_name) == "union":
            merged: List[str] = []
            seen = set()
            for items in normalized:
                for item in items:
                    key = item.casefold()
                    if key in seen:
                        continue
                    seen.add(key)
                    merged.append(item)
            return merged

        common = {item.casefold(): item for item in normalized[0]}
        for items in normalized[1:]:
            allowed = {item.casefold() for item in items}
            common = {k: v for k, v in common.items() if k in allowed}
        return list(common.values())

    def _aggregate_env_or_prefs_stage(
        self,
        *,
        stage_name: str,
        stage_progress: dict,
        source_items: List[str],
    ) -> dict:
        success_models = []
        error_count = 0
        violated_by_model: Dict[str, List[str]] = {}
        warnings: List[str] = []

        for judge_name in [cfg.name for cfg in self._get_stage_judge_cfgs(stage_name)]:
            slot = stage_progress["per_judge"][judge_name]
            if slot.get("status") == "success":
                parsed = slot.get("parsed_result") or {}
                if bool(parsed.get("violation")):
                    items, item_warnings = self._map_constraint_numbers_to_items_1based(
                        parsed.get("constraint_numbers_1based") or [],
                        source_items,
                        raw_marked_items=parsed.get("raw_marked_items") or [],
                    )
                    warnings.extend(item_warnings)
                    if not items:
                        slot["status"] = "error"
                        slot["error_type"] = "mapping_error"
                        slot["error_message"] = (
                            f"Could not map parsed {stage_name} violation items back to canonical source items."
                        )
                        stage_progress["per_judge"][judge_name] = slot
                        error_count += 1
                        continue
                    violated_by_model[judge_name] = items
                success_models.append(judge_name)
            elif slot.get("status") == "error":
                error_count += 1

        stage_progress.setdefault("warnings", [])
        stage_progress["warnings"] = self._normalize_items([*stage_progress["warnings"], *warnings])

        if error_count > self._get_stage_tolerant_fail_limit(stage_name) or not success_models:
            stage_progress["status"] = "error"
            stage_progress["final_result"] = None
            return stage_progress

        violating_models = [
            judge_name for judge_name in [cfg.name for cfg in self._get_stage_judge_cfgs(stage_name)]
            if judge_name in violated_by_model
        ]
        if not violating_models:
            stage_progress["status"] = "success"
            stage_progress["final_result"] = {
                "parse_ok": True,
                "violation": False,
                "violated_items": [],
                "source_model": None,
            }
            return stage_progress

        merged_items = self._merge_item_sets(
            [violated_by_model[m] for m in violating_models],
            stage_name=stage_name,
        )
        fallback_model = violating_models[0]
        if not merged_items:
            merged_items = list(violated_by_model.get(fallback_model) or [])

        stage_progress["status"] = "success"
        stage_progress["final_result"] = {
            "parse_ok": True,
            "violation": True,
            "violated_items": self._normalize_items(merged_items),
            "source_model": fallback_model,
            "violating_models": violating_models,
            "violated_items_by_model": violated_by_model,
        }
        return stage_progress

    def _aggregate_rubrics_stage(self, *, stage_progress: dict) -> dict:
        success_models = []
        error_count = 0
        scores_by_model: Dict[str, Dict[str, int]] = {}
        reasons_by_model: Dict[str, Dict[str, str]] = {}
        warnings: List[str] = []

        for judge_name in [cfg.name for cfg in self._get_stage_judge_cfgs("rubrics")]:
            slot = stage_progress["per_judge"][judge_name]
            if slot.get("status") == "success":
                parsed = slot.get("parsed_result") or {}
                parsed_scores = {
                    str(k): int(v)
                    for k, v in (parsed.get("scores_by_rubric") or {}).items()
                    if str(k).strip()
                }
                if not all(rubric in parsed_scores for rubric in self._RUBRIC_NAMES):
                    slot["status"] = "error"
                    slot["error_type"] = "mapping_error"
                    slot["error_message"] = (
                        "Could not map parsed rubric scores back to the canonical rubric names."
                    )
                    stage_progress["per_judge"][judge_name] = slot
                    error_count += 1
                    continue
                scores_by_model[judge_name] = {rubric: int(parsed_scores[rubric]) for rubric in self._RUBRIC_NAMES}
                reasons_by_model[judge_name] = {
                    str(k): str(v).strip()
                    for k, v in (parsed.get("reasons_by_rubric") or {}).items()
                    if str(k).strip() and str(v).strip()
                }
                success_models.append(judge_name)
            elif slot.get("status") == "error":
                error_count += 1

        stage_progress.setdefault("warnings", [])
        stage_progress["warnings"] = self._normalize_items([*stage_progress["warnings"], *warnings])

        if error_count > self._get_stage_tolerant_fail_limit("rubrics") or not success_models:
            stage_progress["status"] = "error"
            stage_progress["final_result"] = None
            return stage_progress

        aggregated_scores: Dict[str, float] = {}
        merged_reasons: Dict[str, str] = {}
        ordered_success_models = [
            judge_name for judge_name in [cfg.name for cfg in self._get_stage_judge_cfgs("rubrics")]
            if judge_name in scores_by_model
        ]

        for rubric in self._RUBRIC_NAMES:
            rubric_scores = [int(scores_by_model[m][rubric]) for m in ordered_success_models]
            if self.cfg.rubrics_score_merge_mode == "min":
                aggregated = float(min(rubric_scores))
            elif self.cfg.rubrics_score_merge_mode == "max":
                aggregated = float(max(rubric_scores))
            else:
                aggregated = float(sum(rubric_scores)) / float(len(rubric_scores))
            aggregated_scores[rubric] = aggregated

            worst_score = min(rubric_scores)
            for model_name in ordered_success_models:
                if int(scores_by_model[model_name][rubric]) == worst_score:
                    reason = str(reasons_by_model.get(model_name, {}).get(rubric) or "").strip()
                    if reason:
                        merged_reasons[rubric] = reason
                    break

        passed, pass_metric_value = self._compute_rubrics_pass(aggregated_scores)
        failed_rubrics = [
            rubric
            for rubric in self._RUBRIC_NAMES
            if rubric not in self._NON_FAILING_RUBRICS
            and float(aggregated_scores.get(rubric, 5.0)) < float(self.cfg.rubrics_feedback_threshold)
        ]

        stage_progress["status"] = "success"
        stage_progress["final_result"] = {
            "parse_ok": True,
            "passed": bool(passed),
            "scores_by_rubric": aggregated_scores,
            "scores_by_judge": {model_name: scores_by_model[model_name] for model_name in ordered_success_models},
            "reasons_by_rubric": merged_reasons,
            "failed_rubrics": failed_rubrics,
            "pass_metric_value": pass_metric_value,
            "source_model": ordered_success_models[0] if ordered_success_models else None,
            "success_models": ordered_success_models,
        }
        return stage_progress

    def _run_multi_judge_stage(
        self,
        *,
        stage_name: str,
        stage_progress: dict,
        query: str,
        plan: str,
        banned_tools: Optional[str] = None,
        user_prefs: Optional[str] = None,
        source_items: Optional[List[str]] = None,
    ) -> dict:
        if stage_progress.get("status") == "success" and stage_progress.get("final_result") is not None:
            return stage_progress

        stage_cfgs = self._get_stage_judge_cfgs(stage_name)
        to_run: List[Tuple[ModelConfig, dict]] = []
        for judge_cfg in stage_cfgs:
            slot = stage_progress["per_judge"][judge_cfg.name]
            if slot.get("status") == "success":
                continue
            slot["status"] = "pending"
            to_run.append((judge_cfg, slot))

        if to_run:
            max_workers = max(1, len(to_run))
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                future_map: Dict[Future, Tuple[str, dict]] = {}
                for judge_cfg, slot in to_run:
                    if stage_name == "tools":
                        fut = pool.submit(
                            self._timed_call,
                            self._get_stage_timer_role(stage_name),
                            judge_cfg.name,
                            self.judger.judge_env_constraints_one_model,
                            query=query,
                            plan=plan,
                            banned_tools=str(banned_tools or "None"),
                            judge_model=judge_cfg,
                        )
                    elif stage_name == "prefs":
                        fut = pool.submit(
                            self._timed_call,
                            self._get_stage_timer_role(stage_name),
                            judge_cfg.name,
                            self.judger.judge_user_prefs_one_model,
                            query=query,
                            plan=plan,
                            user_prefs=str(user_prefs or "None"),
                            judge_model=judge_cfg,
                        )
                    elif stage_name == "rubrics":
                        fut = pool.submit(
                            self._timed_call,
                            self._get_stage_timer_role(stage_name),
                            judge_cfg.name,
                            self.judger.judge_rubrics_one_model,
                            query=query,
                            plan=plan,
                            judge_model=judge_cfg,
                        )
                    else:
                        raise ValueError(f"Unknown stage_name: {stage_name}")
                    future_map[fut] = (judge_cfg.name, slot)

                for fut in future_map:
                    judge_name, slot = future_map[fut]
                    try:
                        result = fut.result()
                    except Exception as exc:                    
                        result = {
                            "status": "error",
                            "prompt": None,
                            "raw_response": None,
                            "parsed_result": None,
                            "error_type": type(exc).__name__,
                            "error_message": str(exc),
                        }
                    slot.update(result)
                    stage_progress["per_judge"][judge_name] = slot

        if stage_name in {"tools", "prefs"}:
            return self._aggregate_env_or_prefs_stage(
                stage_name=stage_name,
                stage_progress=stage_progress,
                source_items=source_items or [],
            )
        return self._aggregate_rubrics_stage(stage_progress=stage_progress)

    def _run_single_query(self, query_entry: dict) -> dict:
        query = str(query_entry.get("query") or "")
        query_id = str(query_entry.get("query_id") or "")
        env_profile = query_entry.get("_runtime_env_profile") or {}

        existing = copy.deepcopy(
            self._all_results_by_id.get(query_id)
            or self._make_pending_result(query_id, query, env_profile)
        )
        tracker, trajectory, history, current_user_prompt, resume_index, no_new_violation_streak = self._restore_query_progress(
            query,
            env_profile,
            existing,
        )
        rubrics_refine_active = bool(existing.get("rubrics_refine_active", False))
        rubrics_refine_turns_used = int(existing.get("rubrics_refine_turns_used", 0) or 0)
        rubrics_refine_limit = int(existing.get("rubrics_refine_max_turns", 0) or 0)
        existing["rubrics_refine_active"] = rubrics_refine_active
        existing["rubrics_refine_turns_used"] = rubrics_refine_turns_used
        existing["rubrics_refine_max_turns"] = rubrics_refine_limit

        status = "stopped"
        stop_reason = "max_turns_reached"
        enabled_dimensions = [name for name in self._all_dimension_names() if self._dimension_enabled(name)]
        response_dimensions = self._response_dimension_set()
        if rubrics_refine_active and bool(existing.get("rubrics_refine_bootstrap_pending")):
            try:
                trajectory, current_user_prompt = self._bootstrap_rubrics_refine_feedback(
                    query=query,
                    query_id=query_id,
                    tracker=tracker,
                    trajectory=trajectory,
                    current_user_prompt=current_user_prompt,
                    existing=existing,
                    no_new_violation_streak=no_new_violation_streak,
                )
            except Exception:
                return existing

        turn_idx = int(resume_index)
        while True:
            if rubrics_refine_active:
                if rubrics_refine_turns_used >= rubrics_refine_limit:
                    status = "failed"
                    stop_reason = "rubrics_refine_budget_exhausted"
                    break
            elif turn_idx >= int(self.cfg.max_turns):
                status = "stopped"
                stop_reason = "max_turns_reached"
                break

            turn_id = turn_idx + 1
            if turn_idx < len(trajectory):
                turn = self._ensure_turn_record(
                    trajectory[turn_idx],
                    turn_id=turn_id,
                    user_prompt=current_user_prompt,
                )
                trajectory[turn_idx] = turn
            else:
                turn = self._make_turn_record(turn_id, current_user_prompt)
                trajectory.append(turn)

            active_before_turn = rubrics_refine_active

            if not turn.get("user_prompt"):
                turn["user_prompt"] = current_user_prompt

            user_prompt = str(turn.get("user_prompt") or current_user_prompt)
            agent_runtime_prompt = self._build_agent_runtime_prompt(user_prompt, tracker)
            agent_side = self._ensure_agent_side(turn)
            if agent_side.get("status") != "success":
                agent_side["status"] = "pending"
                agent_side["prompt"] = agent_runtime_prompt
                try:
                    messages = list(history) + [{"role": "user", "content": agent_runtime_prompt}]
                    agent_plan = self._call_agent(messages)
                except Exception as exc:
                    agent_side["status"] = "error"
                    agent_side["error_type"] = type(exc).__name__
                    agent_side["error_message"] = str(exc)
                    turn["status"] = "error"
                    self._persist_query_progress(
                        existing,
                        tracker=tracker,
                        trajectory=trajectory,
                        no_new_violation_streak=no_new_violation_streak,
                    )
                    existing["result"] = {
                        "status": "error",
                        "stop_reason": "agent_error",
                        "turns": len(trajectory),
                    }
                    self._write_query_debug(query_id, {"stage": "agent_error", "turn": turn})
                    return existing
                if not self._has_answer_start(agent_plan):
                    agent_side["status"] = "error"
                    agent_side["raw_response"] = agent_plan
                    agent_side["history_content"] = None
                    agent_side["error_type"] = "parse_error"
                    agent_side["error_message"] = "Agent response is missing <answer_start>."
                    turn["status"] = "error"
                    self._persist_query_progress(
                        existing,
                        tracker=tracker,
                        trajectory=trajectory,
                        no_new_violation_streak=no_new_violation_streak,
                    )
                    existing["result"] = {
                        "status": "error",
                        "stop_reason": "agent_error",
                        "turns": len(trajectory),
                    }
                    self._write_query_debug(
                        query_id,
                        {
                            "stage": "agent_parse_error",
                            "turn": turn,
                            "missing_answer_start_debug": {
                                "conversation_history": messages,
                                "history_message_count": len(messages),
                                "agent_raw_response": agent_plan,
                            },
                        },
                    )
                    return existing
                agent_side["status"] = "success"
                agent_side["raw_response"] = agent_plan
                agent_side["history_content"] = (
                    self._truncate_plan_for_history(agent_plan)
                    if self.cfg.truncate_history
                    else agent_plan
                )
                agent_side["error_type"] = None
                agent_side["error_message"] = None

            agent_plan = str(agent_side.get("raw_response") or "")
            judge_plan = self._extract_plan_from_answer_start(agent_plan)
            history_for_turn = list(history) + [
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": agent_side.get("history_content") or agent_plan},
            ]

            all_constraints = tracker.get_all_constraints()
            stage_inputs = {
                "tools": {
                    "items": all_constraints.get("tools") or [],
                    "text": self._format_numbered_list(all_constraints.get("tools") or [])[0],
                },
                "prefs": {
                    "items": all_constraints.get("prefs") or [],
                    "text": self._format_numbered_list(all_constraints.get("prefs") or [])[0],
                },
                "rubrics": {"items": list(self._RUBRIC_NAMES), "text": None},
            }

            stage_results: Dict[str, dict] = {}
            with ThreadPoolExecutor(max_workers=max(1, len(enabled_dimensions))) as pool:
                future_map: Dict[Future, str] = {}
                for stage_name in enabled_dimensions:
                    stage_progress = self._ensure_judge_stage(turn, stage_name)
                    stage_progress["prompt"] = self._build_stage_prompt(
                        stage_name=stage_name,
                        query=query,
                        plan=judge_plan,
                        constraints_text=stage_inputs[stage_name]["text"],
                    )
                    kwargs = {
                        "stage_name": stage_name,
                        "stage_progress": stage_progress,
                        "query": query,
                        "plan": judge_plan,
                    }
                    if stage_name == "tools":
                        kwargs["banned_tools"] = stage_inputs[stage_name]["text"]
                        kwargs["source_items"] = stage_inputs[stage_name]["items"]
                    elif stage_name == "prefs":
                        kwargs["user_prefs"] = stage_inputs[stage_name]["text"]
                        kwargs["source_items"] = stage_inputs[stage_name]["items"]
                    future = pool.submit(self._run_multi_judge_stage, **kwargs)
                    future_map[future] = stage_name

                for future, stage_name in future_map.items():
                    try:
                        stage_result = future.result()
                    except Exception as exc:                    
                        stage_result = self._ensure_judge_stage(turn, stage_name)
                        stage_result["status"] = "error"
                        stage_result["final_result"] = None
                        stage_result.setdefault("warnings", [])
                        stage_result["warnings"] = self._normalize_items(
                            [*stage_result.get("warnings", []), f"runner_exception:{type(exc).__name__}:{exc}"]
                        )
                    turn.setdefault("judge_side", {})[stage_name] = stage_result
                    stage_results[stage_name] = stage_result

            for stage_name in enabled_dimensions:
                stage_result = stage_results.get(stage_name) or {}
                if stage_result.get("status") != "success":
                    turn["status"] = "error"
                    self._persist_query_progress(
                        existing,
                        tracker=tracker,
                        trajectory=trajectory,
                        no_new_violation_streak=no_new_violation_streak,
                    )
                    existing["result"] = {
                        "status": "error",
                        "stop_reason": f"{stage_name}_judge_error",
                        "turns": len(trajectory),
                    }
                    self._write_query_debug(query_id, {"stage": f"{stage_name}_judge_error", "turn": turn})
                    return existing

            tools_final = (stage_results.get("tools") or {}).get("final_result") or {"violation": False}
            prefs_final = (stage_results.get("prefs") or {}).get("final_result") or {"violation": False}
            rubrics_final = (stage_results.get("rubrics") or {}).get("final_result") or {"passed": True}

            turn["violated_env_items"] = list(tools_final.get("violated_items") or [])
            turn["violated_pref_items"] = list(prefs_final.get("violated_items") or [])

            feedback_side = self._ensure_feedback_side(turn)
            disclosed_tools = ((turn.get("disclosed_check_by_dimension") or {}).get("tools")) or {
                "already_disclosed": [],
                "newly_seen": [],
            }
            disclosed_prefs = ((turn.get("disclosed_check_by_dimension") or {}).get("prefs")) or {
                "already_disclosed": [],
                "newly_seen": [],
            }
            chosen_feedback_dimensions: List[str] = list(turn.get("chosen_feedback_dimensions") or [])
            chosen_feedback_items_by_dimension = dict(
                turn.get("chosen_feedback_items_by_dimension")
                or {"tools": [], "prefs": [], "rubrics": []}
            )
            tools_feedback_text = None
            prefs_feedback_text = None
            rubrics_feedback_text = None

            if not turn.get("tracker_applied"):
                disclosed_tools = {"already_disclosed": [], "newly_seen": []}
                disclosed_prefs = {"already_disclosed": [], "newly_seen": []}
                chosen_feedback_dimensions = []
                chosen_feedback_items_by_dimension = {"tools": [], "prefs": [], "rubrics": []}
                candidate_dimensions: List[str] = []
                constraints_clean_now = (not bool(tools_final.get("violation"))) and (not bool(prefs_final.get("violation")))
                rubrics_feedback_eligible = (
                    "rubrics" in response_dimensions
                    or (bool(self.cfg.refine_rubrics) and constraints_clean_now)
                    or rubrics_refine_active
                )

                if "tools" in response_dimensions and bool(tools_final.get("violation")):
                    candidate_dimensions.append("tools")
                if "prefs" in response_dimensions and bool(prefs_final.get("violation")):
                    candidate_dimensions.append("prefs")
                if rubrics_feedback_eligible and not bool(rubrics_final.get("passed", True)):
                    candidate_dimensions.append("rubrics")

                elicited_dimensions = self._select_elicited_dimensions(candidate_dimensions)

                if "tools" in elicited_dimensions:
                    tool_feedback_items = self._select_dimension_feedback_items(
                        "tools",
                        turn["violated_env_items"],
                    )
                    disclosed_tools = tracker.apply_violation_counters("tool", tool_feedback_items)
                    tracker.mark_disclosed("tool", tool_feedback_items)
                    already_set = {x.casefold().strip() for x in disclosed_tools.get("already_disclosed") or []}
                    repeated_items = [x for x in tool_feedback_items if x.casefold().strip() in already_set]
                    if not self.cfg.repetition_penalty_response:
                        repeated_items = []
                    tools_feedback_text = self._build_judge_feedback_text("env", tool_feedback_items, repeated_items)
                    chosen_feedback_dimensions.append("tools")
                    chosen_feedback_items_by_dimension["tools"] = list(tool_feedback_items)

                if "prefs" in elicited_dimensions:
                    pref_feedback_items = self._select_dimension_feedback_items(
                        "prefs",
                        turn["violated_pref_items"],
                    )
                    disclosed_prefs = tracker.apply_violation_counters("pref", pref_feedback_items)
                    tracker.mark_disclosed("pref", pref_feedback_items)
                    already_set = {x.casefold().strip() for x in disclosed_prefs.get("already_disclosed") or []}
                    repeated_items = [x for x in pref_feedback_items if x.casefold().strip() in already_set]
                    if not self.cfg.repetition_penalty_response:
                        repeated_items = []
                    prefs_feedback_text = self._build_judge_feedback_text("prefs", pref_feedback_items, repeated_items)
                    chosen_feedback_dimensions.append("prefs")
                    chosen_feedback_items_by_dimension["prefs"] = list(pref_feedback_items)

                if "rubrics" in elicited_dimensions:
                    rubrics_feedback_items = self._select_dimension_feedback_items(
                        "rubrics",
                        list(rubrics_final.get("failed_rubrics") or []),
                    )
                    rubrics_feedback_text = self._build_rubrics_feedback_text(
                        rubrics_feedback_items,
                        rubrics_final.get("reasons_by_rubric") or {},
                        rubrics_final.get("scores_by_rubric") or {},
                    )
                    chosen_feedback_dimensions.append("rubrics")
                    chosen_feedback_items_by_dimension["rubrics"] = list(rubrics_feedback_items)

                turn["disclosed_check_by_dimension"] = {
                    "tools": disclosed_tools,
                    "prefs": disclosed_prefs,
                }
                turn["disclosed_check"] = {
                    "already_disclosed": self._normalize_items(
                        [*(disclosed_tools.get("already_disclosed") or []), *(disclosed_prefs.get("already_disclosed") or [])]
                    ),
                    "newly_seen": self._normalize_items(
                        [*(disclosed_tools.get("newly_seen") or []), *(disclosed_prefs.get("newly_seen") or [])]
                    ),
                }
                turn["chosen_feedback_dimensions"] = list(chosen_feedback_dimensions)
                turn["chosen_feedback_items_by_dimension"] = chosen_feedback_items_by_dimension
                turn["chosen_feedback_type"] = chosen_feedback_dimensions[0] if len(chosen_feedback_dimensions) == 1 else None
                turn["chosen_feedback_items"] = self._normalize_items(
                    [
                        *chosen_feedback_items_by_dimension["tools"],
                        *chosen_feedback_items_by_dimension["prefs"],
                        *chosen_feedback_items_by_dimension["rubrics"],
                    ]
                )
                turn["counter_snapshot"] = tracker.snapshot_counters()
                turn["tracker_applied"] = True

                no_new_violation_streak = self._update_no_new_violation_streak(
                    no_new_violation_streak,
                    env_newly_seen=disclosed_tools.get("newly_seen") or [],
                    prefs_newly_seen=disclosed_prefs.get("newly_seen") or [],
                )
                early_stop_reason = self._check_early_stop(
                    tracker,
                    no_new_violation_streak=no_new_violation_streak,
                )
            else:
                if chosen_feedback_items_by_dimension.get("tools"):
                    already_set = {x.casefold().strip() for x in disclosed_tools.get("already_disclosed") or []}
                    repeated_items = [
                        x for x in chosen_feedback_items_by_dimension.get("tools", [])
                        if x.casefold().strip() in already_set
                    ]
                    if not self.cfg.repetition_penalty_response:
                        repeated_items = []
                    tools_feedback_text = self._build_judge_feedback_text(
                        "env",
                        chosen_feedback_items_by_dimension.get("tools", []),
                        repeated_items,
                    )
                if chosen_feedback_items_by_dimension.get("prefs"):
                    already_set = {x.casefold().strip() for x in disclosed_prefs.get("already_disclosed") or []}
                    repeated_items = [
                        x for x in chosen_feedback_items_by_dimension.get("prefs", [])
                        if x.casefold().strip() in already_set
                    ]
                    if not self.cfg.repetition_penalty_response:
                        repeated_items = []
                    prefs_feedback_text = self._build_judge_feedback_text(
                        "prefs",
                        chosen_feedback_items_by_dimension.get("prefs", []),
                        repeated_items,
                    )
                if chosen_feedback_items_by_dimension.get("rubrics"):
                    rubrics_feedback_text = self._build_rubrics_feedback_text(
                        chosen_feedback_items_by_dimension.get("rubrics", []),
                        rubrics_final.get("reasons_by_rubric") or {},
                        rubrics_final.get("scores_by_rubric") or {},
                    )
                early_stop_reason = self._check_early_stop(
                    tracker,
                    no_new_violation_streak=no_new_violation_streak,
                )
            if early_stop_reason:
                turn["status"] = "success"
                self._persist_query_progress(
                    existing,
                    tracker=tracker,
                    trajectory=trajectory,
                    no_new_violation_streak=no_new_violation_streak,
                )
                existing["result"] = {
                    "status": "stopped",
                    "stop_reason": early_stop_reason,
                    "turns": len(trajectory),
                }
                self._write_query_debug(query_id, {"stage": "early_stop", "turn": turn})
                return existing

            tools_violation = bool(tools_final.get("violation")) if self._dimension_enabled("tools") else False
            prefs_violation = bool(prefs_final.get("violation")) if self._dimension_enabled("prefs") else False
            rubrics_pass = bool(rubrics_final.get("passed", True))
            response_dimension_issues: List[str] = []
            if "tools" in response_dimensions and tools_violation:
                response_dimension_issues.append("tools")
            if "prefs" in response_dimensions and prefs_violation:
                response_dimension_issues.append("prefs")
            if "rubrics" in response_dimensions and not rubrics_pass:
                response_dimension_issues.append("rubrics")
            turn["response_dimension_issues"] = list(response_dimension_issues)
            response_dimensions_clean = not response_dimension_issues

            if not tools_violation and not prefs_violation and rubrics_pass:
                turn["status"] = "success"
                history = history_for_turn
                existing["rubrics_refine_active"] = False
                existing["rubrics_refine_turns_used"] = rubrics_refine_turns_used
                self._persist_query_progress(
                    existing,
                    tracker=tracker,
                    trajectory=trajectory,
                    no_new_violation_streak=no_new_violation_streak,
                )
                existing["result"] = {
                    "status": "success",
                    "stop_reason": "all_judges_pass",
                    "turns": len(trajectory),
                }
                self._write_query_debug(query_id, {"stage": "query_end", "result": existing["result"]})
                return existing

                                                                                            
                                                                                             
            if not rubrics_pass and not self.cfg.refine_rubrics and response_dimensions_clean:
                turn["status"] = "success"
                history = history_for_turn
                existing["rubrics_refine_active"] = False
                existing["rubrics_refine_turns_used"] = rubrics_refine_turns_used
                self._persist_query_progress(
                    existing,
                    tracker=tracker,
                    trajectory=trajectory,
                    no_new_violation_streak=no_new_violation_streak,
                )
                existing["result"] = {
                    "status": "failed",
                    "stop_reason": "rubrics_failed_no_refine",
                    "turns": len(trajectory),
                }
                self._write_query_debug(query_id, {"stage": "query_end", "result": existing["result"]})
                return existing

            entered_rubrics_refine_this_turn = False
            if (
                bool(self.cfg.refine_rubrics)
                and int(self.cfg.rubrics_refine_max_turns) > 0
                and not rubrics_refine_active
                and not tools_violation
                and not prefs_violation
                and not rubrics_pass
            ):
                rubrics_refine_active = True
                rubrics_refine_turns_used = 0
                existing["first_constraint_clean_rubrics_fail_turn"] = turn_id
                entered_rubrics_refine_this_turn = True
            existing["rubrics_refine_active"] = rubrics_refine_active
            existing["rubrics_refine_turns_used"] = rubrics_refine_turns_used

            combined_judge_feedback = self._build_combined_judge_feedback(
                tools_feedback=tools_feedback_text,
                prefs_feedback=prefs_feedback_text,
                rubrics_feedback=rubrics_feedback_text,
            )
            feedback_side["feedback_type"] = ",".join(chosen_feedback_dimensions) if chosen_feedback_dimensions else None
            feedback_side["feedback_items"] = list(turn["chosen_feedback_items"])
            feedback_side["repeated_items"] = self._normalize_items(
                [*(disclosed_tools.get("already_disclosed") or []), *(disclosed_prefs.get("already_disclosed") or [])]
            )
            feedback_side["judge_feedback"] = combined_judge_feedback or "None"

            if feedback_side.get("status") != "success":
                feedback_side["status"] = "pending"
                try:
                    user_feedback, prompt_text, raw_response = self._generate_feedback_message(
                        query=query,
                        plan=judge_plan,
                        judge_feedback=str(feedback_side.get("judge_feedback") or "None"),
                        tracker=tracker,
                        response_dimensions=response_dimensions | (
                            {"rubrics"} if rubrics_refine_active or entered_rubrics_refine_this_turn else set()
                        ),
                    )
                    feedback_side["prompt"] = prompt_text
                    feedback_side["raw_response"] = raw_response
                except Exception as exc:
                    feedback_side["status"] = "error"
                    feedback_side["error_type"] = type(exc).__name__
                    feedback_side["error_message"] = str(exc)
                    turn["status"] = "error"
                    self._persist_query_progress(
                        existing,
                        tracker=tracker,
                        trajectory=trajectory,
                        no_new_violation_streak=no_new_violation_streak,
                    )
                    existing["result"] = {
                        "status": "error",
                        "stop_reason": "feedback_error",
                        "turns": len(trajectory),
                    }
                    self._write_query_debug(query_id, {"stage": "feedback_error", "turn": turn})
                    return existing
                feedback_side["status"] = "success"
                feedback_side["user_feedback"] = user_feedback
                feedback_side["error_type"] = None
                feedback_side["error_message"] = None

            turn["status"] = "success"
            history = history_for_turn
            current_user_prompt = str(feedback_side.get("user_feedback") or "")
            if active_before_turn:
                rubrics_refine_turns_used += 1
            existing["rubrics_refine_active"] = rubrics_refine_active
            existing["rubrics_refine_turns_used"] = rubrics_refine_turns_used
            self._write_query_debug(query_id, {"stage": "turn_end", "turn": turn})
            turn_idx += 1

        existing["rubrics_refine_active"] = rubrics_refine_active
        existing["rubrics_refine_turns_used"] = rubrics_refine_turns_used
        existing["rubrics_refine_max_turns"] = rubrics_refine_limit
        self._persist_query_progress(
            existing,
            tracker=tracker,
            trajectory=trajectory,
            no_new_violation_streak=no_new_violation_streak,
        )
        existing["result"] = {
            "status": status,
            "stop_reason": stop_reason,
            "turns": len(trajectory),
        }
        self._write_query_debug(query_id, {"stage": "query_end", "result": existing["result"]})
        return existing
