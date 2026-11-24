from __future__ import annotations

import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from tqdm import tqdm
except Exception:
    tqdm = None

from env.construction import prompts as construction_prompts

from .dataworker import DataWorker
from .llm import ModelConfig, format_prompt, openai_chat_request, resolve_api_key


STATUS_PENDING = "pending"
STATUS_SUCCESS = "success"
STATUS_ERROR = "error"
FLUSH_EVERY = 10


@dataclass
class MergeCheckResult:
    matched: bool
    matched_pool_index: Optional[int]
    reason: str


def _normalize_loose_text(text: str) -> str:
    normalized = re.sub(r"[^a-z0-9\s]+", " ", str(text).casefold())
    normalized = re.sub(r"\b(a|an|the)\b", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _loosely_matches_pool_item(item: str, pool: Sequence[str]) -> bool:
    item_norm = _normalize_loose_text(item)
    if not item_norm:
        return False
    item_tokens = set(item_norm.split())
    for candidate in pool:
        cand_norm = _normalize_loose_text(candidate)
        if not cand_norm:
            continue
        if item_norm == cand_norm or item_norm in cand_norm or cand_norm in item_norm:
            return True
        cand_tokens = set(cand_norm.split())
        if item_tokens and cand_tokens:
            overlap = len(item_tokens & cand_tokens)
            if overlap >= max(1, min(len(item_tokens), len(cand_tokens)) // 2):
                return True
    return False


def _apply_merge_sanity_guard(merged_items: Sequence[str], pool_items: Sequence[str]) -> Tuple[List[str], Dict[str, Any]]:
    deduped_pool = RuntimeMerger._dedupe_preserve_order_casefold(pool_items)
    deduped_merged = RuntimeMerger._dedupe_preserve_order_casefold(merged_items)
    reasons: List[str] = []
    if len(deduped_merged) > len(deduped_pool):
        reasons.append("len(merged) > len(rule_deduped_pool)")
    if len(deduped_merged) < (len(deduped_pool) // 2):
        reasons.append("len(merged) < floor(len(rule_deduped_pool) * 0.5)")
    unmatched = [item for item in deduped_merged if not _loosely_matches_pool_item(item, deduped_pool)]
    if unmatched:
        reasons.append(f"unmatched_items={unmatched}")
    fallback_used = bool(reasons)
    final_items = deduped_pool if fallback_used else deduped_merged
    return final_items, {
        "fallback_used": fallback_used,
        "reasons": reasons,
        "rule_deduped_pool": deduped_pool,
        "llm_merged": deduped_merged,
        "final_items": final_items,
    }


class RuntimeMerger:
    def __init__(
        self,
        args,
        dataworker: DataWorker,
        merge_model: ModelConfig,
        check_model: ModelConfig,
    ):
        self.args = args
        self.dataworker = dataworker
        self.merge_model = merge_model
        self.check_model = check_model
        self.merge_api_key = resolve_api_key(merge_model.api_key_env)
        self.check_api_key = resolve_api_key(check_model.api_key_env)
        self._persist_lock = threading.Lock()

    def check_merge_metadata(self, query_entries: List[dict]) -> MergeCheckResult:
        if not query_entries:
            return MergeCheckResult(False, None, "query entries empty")

        target = self._target_post_sampling()
        first_pool = query_entries[0].get("ban_pool") or []
        for pool_index, pool_item in enumerate(first_pool):
            if not isinstance(pool_item, dict):
                continue
            post = ((pool_item.get("metadata") or {}).get("post_sampling") or {})
            if not isinstance(post, dict):
                continue
            if not self._match_post_sampling(post, target):
                continue

            for entry in query_entries[1:]:
                pool = entry.get("ban_pool") or []
                if pool_index >= len(pool):
                    raise ValueError(
                        "ban_pool index mismatch across queries: "
                        f"query_id={entry.get('query_id')} missing index {pool_index}"
                    )
            return MergeCheckResult(True, pool_index, f"matched post_sampling at pool index {pool_index}")

        return MergeCheckResult(False, None, "no post_sampling match; runtime merge required")

    @staticmethod
    def _match_post_sampling(post: dict, target: dict) -> bool:
        for key, value in target.items():
            if int(post.get(key, -10**9)) != int(value):
                return False
        return True

    def select_existing_profiles(self, query_entries: List[dict], pool_index: int) -> List[dict]:
        selected: List[dict] = []
        for entry in query_entries:
            pool = entry.get("ban_pool") or []
            if pool_index >= len(pool):
                raise ValueError(
                    "ban_pool index mismatch across queries while selecting profiles: "
                    f"query_id={entry.get('query_id')} index={pool_index}"
                )
            profile = pool[pool_index]
            if not isinstance(profile, dict):
                raise ValueError(
                    f"Invalid ban_pool item type for query_id={entry.get('query_id')} index={pool_index}"
                )
            selected.append(profile)
        return selected

    def ensure_profiles(self, query_entries: List[dict]) -> List[dict]:
        check = self.check_merge_metadata(query_entries)
        if check.matched:
            return self.select_existing_profiles(query_entries, int(check.matched_pool_index))

        metadata, records = self._load_or_initialize_progress(query_entries)
        if self._all_ready(records):
            self._append_profiles_if_needed(records, metadata)
            return self._profiles_from_records(records)

        attempts_tools = self._run_stage(
            metadata,
            records,
            step="merge_tools",
            label="runtime_merge[merge_tools]",
            should_run=self._should_run_merge_tools,
            worker=self._merge_tools_worker,
        )
        attempts_prefs = self._run_stage(
            metadata,
            records,
            step="merge_prefs",
            label="runtime_merge[merge_prefs]",
            should_run=self._should_run_merge_prefs,
            worker=self._merge_prefs_worker,
        )
        attempts_check = self._run_stage(
            metadata,
            records,
            step="check",
            label="runtime_merge[check]",
            should_run=self._should_run_check,
            worker=self._check_worker,
        )

        for resume_attempt in range(1, int(self.args.max_resume_attempts) + 1):
            remaining = self._remaining_counts(records)
            if sum(remaining.values()) == 0:
                break
            reasons_text = ", ".join(f"{k}={v}" for k, v in sorted(remaining.items()))
            print(
                f"[runtime-merge-resume] attempt {resume_attempt}/{self.args.max_resume_attempts}: "
                f"rerun pending/error queries={sum(remaining.values())} ({reasons_text})"
            )
            attempts_tools += self._run_stage(
                metadata,
                records,
                step="merge_tools",
                label=f"runtime_merge_resume{resume_attempt}[tools]",
                should_run=self._should_run_merge_tools,
                worker=self._merge_tools_worker,
            )
            attempts_prefs += self._run_stage(
                metadata,
                records,
                step="merge_prefs",
                label=f"runtime_merge_resume{resume_attempt}[prefs]",
                should_run=self._should_run_merge_prefs,
                worker=self._merge_prefs_worker,
            )
            attempts_check += self._run_stage(
                metadata,
                records,
                step="check",
                label=f"runtime_merge_resume{resume_attempt}[check]",
                should_run=self._should_run_check,
                worker=self._check_worker,
            )

        remaining = self._remaining_counts(records)
        metadata["summary"] = {
            "merge_tools_attempts": attempts_tools,
            "merge_prefs_attempts": attempts_prefs,
            "check_attempts": attempts_check,
            "remaining": remaining,
        }
        self._write_progress(metadata, records)

        if sum(remaining.values()) > 0:
            raise RuntimeError(
                "runtime merge/check still has unfinished queries: "
                f"merge_tools={remaining['merge_tools']}, "
                f"merge_prefs={remaining['merge_prefs']}, "
                f"check={remaining['check']}. "
                f"Resume file: {self.dataworker.build_merge_progress_path()}"
            )

        self._append_profiles_if_needed(records, metadata)
        return self._profiles_from_records(records)

    def _target_post_sampling(self) -> Dict[str, int]:
        return {
            "candidate_verbal_sample_num": int(self.args.ban_verbal_sample_num),
            "candidate_sample_num": int(self.args.ban_sample_num),
            "candidate_iterative_sample_num": int(self.args.ban_iterative_sample_num),
        }

    def _build_progress_metadata(self, query_entries: List[dict]) -> Dict[str, Any]:
        if self.dataworker.query_path is None:
            raise RuntimeError("query_path is not set before runtime merge progress init")
        return {
            "version": 1,
            "query_path": str(self.dataworker.query_path),
            "merge_model": self.merge_model.name,
            "check_model": self.check_model.name,
            "target_post_sampling": self._target_post_sampling(),
            "trial_num": getattr(self.args, "trial_num", None),
            "total_query_count": len(query_entries),
            "query_append_completed": False,
        }

    def _validate_progress_metadata(self, metadata: Dict[str, Any], query_entries: List[dict]) -> None:
        if self.dataworker.query_path is None:
            raise RuntimeError("query_path is not set before runtime merge progress validation")
        expected = self._build_progress_metadata(query_entries)
        for key in ("version", "query_path", "merge_model", "check_model", "trial_num", "total_query_count"):
            if metadata.get(key) != expected.get(key):
                raise ValueError(
                    f"runtime merge progress metadata mismatch on {key}: "
                    f"expected {expected.get(key)!r}, got {metadata.get(key)!r}"
                )
        if dict(metadata.get("target_post_sampling") or {}) != dict(expected.get("target_post_sampling") or {}):
            raise ValueError("runtime merge progress target_post_sampling mismatch")

    def _make_progress_entry(self, query_entry: dict) -> Dict[str, Any]:
        tools_pool = self._collect_candidates_from_ban_details(query_entry, kind="tools")
        prefs_pool = self._collect_candidates_from_ban_details(query_entry, kind="prefs")
        return {
            "query": query_entry.get("query"),
            "query_id": query_entry.get("query_id"),
            "ban_details": query_entry.get("ban_details"),
            "tools_pool": tools_pool,
            "prefs_pool": prefs_pool,
            "ref_gt": query_entry.get("ref_gt"),
            "merged_tools": [],
            "merged_prefs": [],
            "ban_pool": None,
            "ban_pool_tracking": None,
            "ready_for_downstream": False,
            "merge_tools_status": STATUS_PENDING,
            "merge_tools_output": None,
            "merge_tools_error": None,
            "merge_prefs_status": STATUS_PENDING,
            "merge_prefs_output": None,
            "merge_prefs_error": None,
            "check_status": STATUS_PENDING,
            "check_output": None,
            "check_error": None,
        }

    def _merge_progress_entry(self, base: Dict[str, Any], prior: Dict[str, Any]) -> Dict[str, Any]:
        entry = dict(base)
        for key, value in prior.items():
            if key in {"query", "query_id", "ban_details", "tools_pool", "prefs_pool", "ref_gt"}:
                continue
            entry[key] = value
        self._normalize_legacy_entry(entry)
        entry["ready_for_downstream"] = self._entry_ready_for_downstream(entry)
        return entry

    def _normalize_legacy_entry(self, entry: Dict[str, Any]) -> None:
        ban_pool = entry.get("ban_pool")
        if not isinstance(ban_pool, list) or not ban_pool or not isinstance(ban_pool[0], dict):
            return
        metadata = ban_pool[0].get("metadata") or {}
        if not isinstance(metadata, dict):
            return
        if "pre_sampling" not in metadata:
            return
        entry["check_status"] = STATUS_PENDING
        entry["check_output"] = None
        entry["check_error"] = None
        entry["ban_pool"] = None
        entry["ban_pool_tracking"] = None

    def _load_or_initialize_progress(self, query_entries: List[dict]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        payload = self.dataworker.load_merge_progress()
        metadata = self._build_progress_metadata(query_entries)
        prior_by_query_id: Dict[str, Dict[str, Any]] = {}
        if payload is not None:
            existing_metadata = payload.get("metadata") or {}
            if not isinstance(existing_metadata, dict):
                raise ValueError("runtime merge progress metadata must be a dict")
            self._validate_progress_metadata(existing_metadata, query_entries)
            metadata.update(existing_metadata)
            existing_data = payload.get("data") or []
            if not isinstance(existing_data, list):
                raise ValueError("runtime merge progress data must be a list")
            for item in existing_data:
                if not isinstance(item, dict):
                    continue
                query_id = str(item.get("query_id") or "").strip()
                if query_id:
                    prior_by_query_id[query_id] = item

        records: List[Dict[str, Any]] = []
        for query_entry in query_entries:
            query_id = str(query_entry.get("query_id") or "")
            base = self._make_progress_entry(query_entry)
            prior = prior_by_query_id.get(query_id)
            if prior is not None:
                base = self._merge_progress_entry(base, prior)
            records.append(base)

        self._write_progress(metadata, records)
        return metadata, records

    def _write_progress(self, metadata: Dict[str, Any], records: Sequence[Dict[str, Any]]) -> None:
        self.dataworker.dump_merge_progress(
            {
                "metadata": metadata,
                "data": list(records),
            }
        )

    def _profiles_from_records(self, records: Sequence[Dict[str, Any]]) -> List[dict]:
        profiles: List[dict] = []
        for entry in records:
            ban_pool = entry.get("ban_pool")
            if not isinstance(ban_pool, list) or not ban_pool or not isinstance(ban_pool[0], dict):
                raise RuntimeError(
                    f"runtime merge ready entry missing ban_pool for query_id={entry.get('query_id')}"
                )
            profiles.append(dict(ban_pool[0]))
        return profiles

    def _all_ready(self, records: Sequence[Dict[str, Any]]) -> bool:
        return all(self._entry_ready_for_downstream(entry) for entry in records)

    def _entry_ready_for_downstream(self, entry: Dict[str, Any]) -> bool:
        return (
            entry.get("merge_tools_status") == STATUS_SUCCESS
            and entry.get("merge_prefs_status") == STATUS_SUCCESS
            and entry.get("check_status") == STATUS_SUCCESS
            and isinstance(entry.get("ban_pool"), list)
            and bool(entry.get("ban_pool"))
        )

    def _append_profiles_if_needed(self, records: Sequence[Dict[str, Any]], metadata: Dict[str, Any]) -> None:
        check = self.check_merge_metadata(self.dataworker.load_queries())
        if check.matched:
            metadata["query_append_completed"] = True
            self._write_progress(metadata, records)
            return

        appended_pool_by_query_id: Dict[str, dict] = {}
        for entry in records:
            if not self._entry_ready_for_downstream(entry):
                raise RuntimeError(
                    f"Cannot append runtime merge outputs before all queries succeed; query_id={entry.get('query_id')}"
                )
            ban_pool = entry.get("ban_pool") or []
            if not isinstance(ban_pool, list) or not ban_pool or not isinstance(ban_pool[0], dict):
                raise RuntimeError(
                    f"runtime merge ban_pool missing for query_id={entry.get('query_id')}"
                )
            appended_pool_by_query_id[str(entry.get("query_id"))] = dict(ban_pool[0])

        if self.dataworker.query_payload is None:
            raise RuntimeError("DataWorker.query_payload is None before persist_appended_pool")
        self.persist_appended_pool(self.dataworker.query_payload, appended_pool_by_query_id)
        metadata["query_append_completed"] = True
        self._write_progress(metadata, records)

    def _should_run_merge_tools(self, entry: Dict[str, Any]) -> bool:
        return entry.get("merge_tools_status") in {STATUS_PENDING, STATUS_ERROR}

    def _should_run_merge_prefs(self, entry: Dict[str, Any]) -> bool:
        return entry.get("merge_prefs_status") in {STATUS_PENDING, STATUS_ERROR}

    def _should_run_check(self, entry: Dict[str, Any]) -> bool:
        return (
            entry.get("check_status") in {STATUS_PENDING, STATUS_ERROR}
            and entry.get("merge_tools_status") == STATUS_SUCCESS
            and entry.get("merge_prefs_status") == STATUS_SUCCESS
        )

    def _update_entry(self, step: str, entry: Dict[str, Any], result: Dict[str, Any]) -> None:
        entry[f"{step}_status"] = result.get("status", STATUS_ERROR)
        entry[f"{step}_output"] = result.get("output")
        entry[f"{step}_error"] = result.get("error")
        if result.get("merged_tools") is not None:
            entry["merged_tools"] = result.get("merged_tools")
        if result.get("merged_prefs") is not None:
            entry["merged_prefs"] = result.get("merged_prefs")
        if result.get("ban_pool") is not None:
            entry["ban_pool"] = result.get("ban_pool")
        if "ban_pool_tracking" in result:
            entry["ban_pool_tracking"] = result.get("ban_pool_tracking")
        entry["ready_for_downstream"] = self._entry_ready_for_downstream(entry)

    def _run_stage(
        self,
        metadata: Dict[str, Any],
        records: List[Dict[str, Any]],
        *,
        step: str,
        label: str,
        should_run,
        worker,
    ) -> int:
        candidates = [entry for entry in records if should_run(entry)]
        if not candidates:
            return 0

        max_workers = max(1, min(int(self.args.max_concurrency), len(candidates)))
        processed = 0
        lock = threading.Lock()

        def _safe_worker(entry: Dict[str, Any]) -> Dict[str, Any]:
            try:
                return worker(entry)
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                return {"status": STATUS_ERROR, "output": None, "error": str(exc)}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_entry = {executor.submit(_safe_worker, entry): entry for entry in candidates}
            iterator = as_completed(future_to_entry)
            if tqdm is not None:
                iterator = tqdm(iterator, total=len(future_to_entry), desc=label, unit="query")
            try:
                for fut in iterator:
                    entry = future_to_entry[fut]
                    result = fut.result()
                    with lock:
                        self._update_entry(step, entry, result)
                        processed += 1
                        if processed % FLUSH_EVERY == 0:
                            self._write_progress(metadata, records)
            except KeyboardInterrupt:
                self._write_progress(metadata, records)
                raise

        self._write_progress(metadata, records)
        return processed

    def _extract_planned_solution(self, entry: Dict[str, Any]) -> str:
        ref_gt = entry.get("ref_gt")
        if isinstance(ref_gt, dict):
            content = str(ref_gt.get("content") or "").strip()
            if content:
                return content
        return str(entry.get("gt") or "").strip()

    def _merge_tools_worker(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        tools_pool = self._dedupe_preserve_order_casefold(entry.get("tools_pool") or [])
        prompt = self._build_merge_prompt_tools(tools_pool)
        raw = self._request_llm(
            model=self.merge_model,
            api_key=self.merge_api_key,
            prompt=prompt,
            temperature=float(self.args.merge_LLM_temperature),
            max_tokens=int(self.args.merge_max_tokens),
            timeout_s=int(self.args.merge_timeout_s),
        )
        parsed_tools = self._extract_bold_items(raw) or list(tools_pool)
        merged_tools, sanity_guard = _apply_merge_sanity_guard(parsed_tools, tools_pool)
        return {
            "status": STATUS_SUCCESS,
            "output": raw,
            "error": None,
            "merged_tools": merged_tools,
            "ban_pool_tracking": {"tools_merge_sanity_guard": sanity_guard},
        }

    def _merge_prefs_worker(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        prefs_pool = self._dedupe_preserve_order_casefold(entry.get("prefs_pool") or [])
        prompt = self._build_merge_prompt_prefs(prefs_pool)
        raw = self._request_llm(
            model=self.merge_model,
            api_key=self.merge_api_key,
            prompt=prompt,
            temperature=float(self.args.merge_LLM_temperature),
            max_tokens=int(self.args.merge_max_tokens),
            timeout_s=int(self.args.merge_timeout_s),
        )
        parsed_prefs = self._extract_bold_items(raw) or list(prefs_pool)
        merged_prefs, sanity_guard = _apply_merge_sanity_guard(parsed_prefs, prefs_pool)
        return {
            "status": STATUS_SUCCESS,
            "output": raw,
            "error": None,
            "merged_prefs": merged_prefs,
            "ban_pool_tracking": {"prefs_merge_sanity_guard": sanity_guard},
        }

    def _check_worker(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        merged_tools_before = list(entry.get("merged_tools") or [])
        merged_prefs_before = list(entry.get("merged_prefs") or [])
        planned_solution = self._extract_planned_solution(entry)
        merged_tools, merged_prefs, raw_output, check_tracking = self._filter_invalid_items(
            merged_tools_before,
            merged_prefs_before,
            planned_solution=planned_solution,
            query_text=str(entry.get("query") or ""),
        )
        ban_pool = [
            {
                "tools": merged_tools,
                "prefs": merged_prefs,
                "metadata": self._build_ban_pool_metadata(entry),
            }
        ]
        ban_pool_tracking = None
        if bool(getattr(self.args, "debug", False)):
            ban_pool_tracking = {
                "tools": {
                    "trace": {
                        "pool": list(entry.get("tools_pool") or []),
                        "merge_raw_response": entry.get("merge_tools_output"),
                        "merged_before_check": merged_tools_before,
                        "check": check_tracking.get("tools", {}),
                        "final_ban_pool": list(merged_tools),
                    },
                    "counts": {
                        "pool": len(entry.get("tools_pool") or []),
                        "merged_before_check": len(merged_tools_before),
                        "final_ban_pool": len(merged_tools),
                    },
                },
                "prefs": {
                    "trace": {
                        "pool": list(entry.get("prefs_pool") or []),
                        "merge_raw_response": entry.get("merge_prefs_output"),
                        "merged_before_check": merged_prefs_before,
                        "check": check_tracking.get("prefs", {}),
                        "final_ban_pool": list(merged_prefs),
                    },
                    "counts": {
                        "pool": len(entry.get("prefs_pool") or []),
                        "merged_before_check": len(merged_prefs_before),
                        "final_ban_pool": len(merged_prefs),
                    },
                },
            }
        return {
            "status": STATUS_SUCCESS,
            "output": raw_output,
            "error": None,
            "ban_pool": ban_pool,
            "ban_pool_tracking": ban_pool_tracking,
        }

    def _remaining_counts(self, records: Sequence[Dict[str, Any]]) -> Dict[str, int]:
        return {
            "merge_tools": sum(1 for entry in records if self._should_run_merge_tools(entry)),
            "merge_prefs": sum(1 for entry in records if self._should_run_merge_prefs(entry)),
            "check": sum(1 for entry in records if self._should_run_check(entry)),
        }

    def _collect_candidates_from_ban_details(self, query_entry: dict, *, kind: str) -> List[str]:
        if kind not in {"tools", "prefs"}:
            raise ValueError(f"Unknown merge kind: {kind}")

        ban_details = query_entry.get("ban_details") or {}
        by_model = ban_details.get(kind)
        if not isinstance(by_model, dict):
            raise ValueError(
                f"Missing ban_details.{kind} for query_id={query_entry.get('query_id')}"
            )

        round_key = f"plan_round_{int(self.args.ban_iterative_sample_num)}"
        field = "merged_tools" if kind == "tools" else "merged_prefs"
        collected: List[str] = []
        for model_name, samples in by_model.items():
            if not isinstance(samples, list):
                raise ValueError(
                    f"Invalid ban_details.{kind}[{model_name}] type for query_id={query_entry.get('query_id')}"
                )
            for sample_idx, sample in enumerate(samples):
                if not isinstance(sample, dict):
                    continue
                if round_key not in sample:
                    raise KeyError(
                        f"Missing {round_key} in ban_details.{kind} for query_id={query_entry.get('query_id')} "
                        f"model={model_name} sample_idx={sample_idx}"
                    )
                round_block = sample.get(round_key) or {}
                merged_items = round_block.get(field)
                if merged_items is None:
                    raise KeyError(
                        f"Missing {field} in {round_key} for query_id={query_entry.get('query_id')} "
                        f"model={model_name} sample_idx={sample_idx}"
                    )
                for item in merged_items:
                    text = str(item).strip()
                    if text:
                        collected.append(text)
        return self._dedupe_preserve_order_casefold(collected)

    def _build_merge_prompt_tools(self, used_tools: Sequence[str]) -> str:
        return format_prompt(
            construction_prompts.merge_entity_prompt,
            {
                "Used_tools": self._format_list(used_tools),
                "used_tools": self._format_list(used_tools),
            },
        )

    def _build_merge_prompt_prefs(self, used_prefs: Sequence[str]) -> str:
        return format_prompt(
            construction_prompts.merge_user_prefs_prompt,
            {
                "Used_prefs": self._format_list(used_prefs),
                "used_prefs": self._format_list(used_prefs),
            },
        )

    def _build_check_prompt(self, used_tools: Sequence[str], used_prefs: Sequence[str], *, planned_solution: str, query: str) -> str:
        rule_text = format_prompt(
            construction_prompts.resample_check_rule,
            {
                "query": str(query or "").strip(),
                "Query": str(query or "").strip(),
                "planned_solution": str(planned_solution or "").strip(),
                "PLANNED_SOLUTION": str(planned_solution or "").strip(),
            },
        )
        return format_prompt(
            construction_prompts.check_cons_prefs_prompt,
            {
                "banned_tools_to_check": self._format_list(used_tools),
                "user_prefs_to_check": self._format_list(used_prefs),
                "BANNED_TOOLS_TO_CHECK": self._format_list(used_tools),
                "USER_PREFS_TO_CHECK": self._format_list(used_prefs),
                "resample_check_rule": rule_text,
                "RESAMPLE_CHECK_RULE": rule_text,
            },
        )

    def _request_llm(
        self,
        *,
        model: ModelConfig,
        api_key: Optional[str],
        prompt: str,
        temperature: float,
        max_tokens: int,
        timeout_s: int,
    ) -> str:
        return openai_chat_request(
            provider=model.provider,
            base_url=model.base_url,
            api_key=api_key,
            model_id=model.model_id,
            model_name=model.name,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_s=timeout_s,
            max_retries=int(getattr(self.args, "llm_max_retries", 0)),
            retry_backoff_s=float(getattr(self.args, "llm_retry_backoff_s", 2.0)),
        )

    def _filter_invalid_items(
        self,
        tools_list: Sequence[str],
        prefs_list: Sequence[str],
        *,
        planned_solution: str,
        query_text: str,
    ) -> Tuple[List[str], List[str], str, Dict[str, Any]]:
        if not tools_list and not prefs_list:
            tracking = {
                "tools": {
                    "before_check": list(tools_list),
                    "filtered_out_numbers": [],
                    "filtered_out_items": [],
                    "after_check": list(tools_list),
                    "counts": {"before_check": len(tools_list), "filtered_out": 0, "after_check": len(tools_list)},
                },
                "prefs": {
                    "before_check": list(prefs_list),
                    "filtered_out_numbers": [],
                    "filtered_out_items": [],
                    "after_check": list(prefs_list),
                    "counts": {"before_check": len(prefs_list), "filtered_out": 0, "after_check": len(prefs_list)},
                },
            }
            return list(tools_list), list(prefs_list), "SKIPPED: empty tools/prefs pool", tracking

        prompt = self._build_check_prompt(
            tools_list,
            prefs_list,
            planned_solution=planned_solution,
            query=query_text,
        )
        raw = self._request_llm(
            model=self.check_model,
            api_key=self.check_api_key,
            prompt=prompt,
            temperature=float(self.args.check_LLM_temperature),
            max_tokens=int(self.args.merge_max_tokens),
            timeout_s=int(self.args.check_timeout_s),
        )
        tool_nums, pref_nums = self._extract_filter_numbers(raw)
        filtered_tools = self._filter_by_numbers(tools_list, tool_nums)
        filtered_prefs = self._filter_by_numbers(prefs_list, pref_nums)
        removed_tools = self._select_by_numbers(tools_list, tool_nums)
        removed_prefs = self._select_by_numbers(prefs_list, pref_nums)
        tracking = {
            "tools": {
                "before_check": list(tools_list),
                "filtered_out_numbers": list(tool_nums),
                "filtered_out_items": removed_tools,
                "after_check": filtered_tools,
                "counts": {
                    "before_check": len(tools_list),
                    "filtered_out": len(removed_tools),
                    "after_check": len(filtered_tools),
                },
            },
            "prefs": {
                "before_check": list(prefs_list),
                "filtered_out_numbers": list(pref_nums),
                "filtered_out_items": removed_prefs,
                "after_check": filtered_prefs,
                "counts": {
                    "before_check": len(prefs_list),
                    "filtered_out": len(removed_prefs),
                    "after_check": len(filtered_prefs),
                },
            },
        }
        return filtered_tools, filtered_prefs, raw, tracking

    def _build_ban_pool_metadata(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "post_sampling": self._target_post_sampling(),
        }

    @staticmethod
    def _format_list(items: Sequence[str]) -> str:
        cleaned = [str(i).strip() for i in items if str(i).strip()]
        if not cleaned:
            return "None"
        return "\n".join(f"{idx + 1}. {val}" for idx, val in enumerate(cleaned))

    @staticmethod
    def _strip_think(text: str) -> str:
        if not text:
            return text
        cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
        return cleaned.replace("<think>", "").replace("</think>", "")

    @classmethod
    def _extract_after_final_answer(cls, text: str) -> str:
        if not text:
            return ""
        idx = text.lower().find("<answer_start>")
        if idx == -1:
            return text
        return text[idx + len("<answer_start>") :]

    @classmethod
    def _extract_bold_items(cls, text: str) -> List[str]:
        cleaned = cls._strip_think(cls._extract_after_final_answer(text))
        items = [m.strip() for m in re.findall(r"\*\*([^*]+)\*\*", cleaned) if m.strip()]
        return cls._dedupe_preserve_order_casefold(items)

    @classmethod
    def _extract_filter_numbers(cls, text: str) -> Tuple[List[int], List[int]]:
        cleaned = cls._strip_think(cls._extract_after_final_answer(text))
        tool_nums: List[int] = []
        pref_nums: List[int] = []
        current_section: Optional[str] = None
        for line in cleaned.splitlines():
            if not line.strip():
                continue
            line_lower = line.lower()
            if "[" in line_lower and "]" in line_lower:
                if "tools/objects to filter out" in line_lower:
                    current_section = "tool"
                elif "user preferences to filter out" in line_lower:
                    current_section = "pref"
            line_items = re.findall(r"\*\*([^*]+)\*\*", line)
            if not line_items or current_section is None:
                continue
            for token in line_items:
                token_text = str(token).strip()
                if not token_text:
                    continue
                match = re.search(r"\d+", token_text)
                if match is None:
                    continue
                num = int(match.group(0))
                if num <= 0:
                    continue
                if current_section == "tool":
                    tool_nums.append(num)
                elif current_section == "pref":
                    pref_nums.append(num)
        return cls._dedupe_ints(tool_nums), cls._dedupe_ints(pref_nums)

    @staticmethod
    def _dedupe_ints(items: Sequence[int]) -> List[int]:
        seen = set()
        out: List[int] = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            out.append(int(item))
        return out

    @staticmethod
    def _filter_by_numbers(items: Sequence[str], numbers: Sequence[int]) -> List[str]:
        to_remove = {n for n in numbers if isinstance(n, int) and n > 0}
        if not to_remove:
            return list(items)
        return [item for idx, item in enumerate(items, start=1) if idx not in to_remove]

    @staticmethod
    def _select_by_numbers(items: Sequence[str], numbers: Sequence[int]) -> List[str]:
        to_select = {n for n in numbers if isinstance(n, int) and n > 0}
        if not to_select:
            return []
        return [item for idx, item in enumerate(items, start=1) if idx in to_select]

    @staticmethod
    def _dedupe_preserve_order_casefold(items: Sequence[str]) -> List[str]:
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

    def persist_appended_pool(
        self,
        original_payload: dict,
        appended_pool_by_query_id: Dict[str, dict],
    ) -> None:
        if not isinstance(original_payload, dict):
            raise ValueError("original_payload must be dict")
        data = original_payload.get("data")
        if not isinstance(data, list):
            raise ValueError("original_payload['data'] must be list")

        with self._persist_lock:
            new_payload = json.loads(json.dumps(original_payload, ensure_ascii=False))
            new_data = new_payload.get("data") or []

            for entry in new_data:
                if not isinstance(entry, dict):
                    continue
                query_id = str(entry.get("query_id") or "")
                if not query_id:
                    continue
                appended = appended_pool_by_query_id.get(query_id)
                if appended is None:
                    continue
                pool = entry.get("ban_pool")
                if not isinstance(pool, list):
                    pool = []
                    entry["ban_pool"] = pool
                pool.append(appended)

            metadata = new_payload.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}
            metadata = dict(metadata)
            metadata["stats"] = self._build_grouped_stats(new_payload)
            new_payload["metadata"] = metadata

            query_path = self.dataworker.query_path
            if query_path is None:
                raise RuntimeError("DataWorker.query_path is None while persisting merged ban_pool")
            query_path.write_text(
                json.dumps(new_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.dataworker.query_payload = new_payload

    @staticmethod
    def _extract_sampling_metadata(pool_item: Dict[str, Any]) -> Dict[str, int]:
        metadata = pool_item.get("metadata") or {}
        if not isinstance(metadata, dict):
            return {}
        sampling = metadata.get("post_sampling") or metadata.get("pre_sampling") or {}
        if not isinstance(sampling, dict):
            return {}
        out: Dict[str, int] = {}
        for key in (
            "candidate_verbal_sample_num",
            "candidate_sample_num",
            "candidate_iterative_sample_num",
        ):
            if key not in sampling:
                return {}
            out[key] = int(sampling[key])
        return out

    @staticmethod
    def _stats_setting_key(sampling: Dict[str, int]) -> str:
        ordered_keys = (
            "candidate_verbal_sample_num",
            "candidate_sample_num",
            "candidate_iterative_sample_num",
        )
        return ", ".join(f"{key}={int(sampling[key])}" for key in ordered_keys)

    def _build_grouped_stats(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = payload.get("data")
        if not isinstance(data, list):
            raise ValueError("payload['data'] must be list when building grouped stats")

        grouped: Dict[str, Dict[str, Any]] = {}
        for entry in data:
            if not isinstance(entry, dict):
                continue
            for pool_item in entry.get("ban_pool") or []:
                if not isinstance(pool_item, dict):
                    continue
                sampling = self._extract_sampling_metadata(pool_item)
                if not sampling:
                    continue
                key = self._stats_setting_key(sampling)
                group = grouped.setdefault(
                    key,
                    {
                        **sampling,
                        "query_count": 0,
                        "_total_tools": 0,
                        "_total_prefs": 0,
                    },
                )
                group["query_count"] += 1
                tools = pool_item.get("tools") or []
                prefs = pool_item.get("prefs") or []
                group["_total_tools"] += len(tools) if isinstance(tools, list) else 0
                group["_total_prefs"] += len(prefs) if isinstance(prefs, list) else 0

        stats: Dict[str, Any] = {"query_count": len(data)}
        for key in sorted(grouped.keys()):
            group = grouped[key]
            count = int(group["query_count"])
            total_tools = int(group.pop("_total_tools", 0))
            total_prefs = int(group.pop("_total_prefs", 0))
            group["avg_tools"] = (float(total_tools) / float(count)) if count else 0.0
            group["avg_prefs"] = (float(total_prefs) / float(count)) if count else 0.0
            stats[key] = group
        return stats
