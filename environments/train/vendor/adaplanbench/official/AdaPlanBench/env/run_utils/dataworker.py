from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .llm import ModelConfig, load_model_config


_TEMPERATURE_SOURCE_LOOKUP_EXEMPT_MODELS = {"gpt-5", "gpt-5-mini", "gpt-5-nano"}


class DataWorker:
    def __init__(self, args):
        self.args = args
        self.project_root = Path(__file__).resolve().parents[2]
        self.query_path: Optional[Path] = None
        self.query_payload: Optional[Dict[str, Any]] = None

    def resolve_default_query_path(self) -> Path:
        return (
            self.project_root
            / "domain_metadata"
            / str(self.args.domain)
            / "final"
            / f"query_{self.args.domain}_{self.args.source}_resample.json"
        )

    def validate_query_path(self, cli_query_path: Optional[str]) -> Path:
        default_path = self.resolve_default_query_path().resolve()

        if cli_query_path:
            provided = Path(cli_query_path).resolve()
            if provided != default_path:
                raise ValueError(
                    f"query path mismatch: expected {default_path}, got {provided}"
                )
            final_path = provided
        else:
            final_path = default_path

        if not final_path.exists():
            raise FileNotFoundError(f"Query file not found: {final_path}")

        self.query_path = final_path
        return final_path

    def load_queries(self) -> List[dict]:
        if self.query_path is None:
            raise RuntimeError("query_path is not set; call validate_query_path first")

        payload = json.loads(self.query_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("query JSON payload must be a dict")

        data = payload.get("data")
        if not isinstance(data, list):
            raise ValueError("query JSON payload['data'] must be a list")

        for idx, entry in enumerate(data):
            if not isinstance(entry, dict):
                raise ValueError(f"entry at index {idx} is not a dict")
            for key in ("query", "query_id", "ban_pool"):
                if key not in entry:
                    raise ValueError(
                        f"entry missing required key {key!r} at index {idx}; query_id={entry.get('query_id')}"
                    )
            if not isinstance(entry.get("ban_pool"), list):
                raise ValueError(
                    f"entry['ban_pool'] must be list at index {idx}; query_id={entry.get('query_id')}"
                )

        self.query_payload = payload
        return data

    def load_model_config(self, model_name: str) -> ModelConfig:
        metadata_path = Path(self.args.model_metadata)
        return load_model_config(model_name, metadata_path)

    def _default_result_basename(self) -> str:
        return f"result_{self._runtime_settings_suffix()}.json"

    def _default_progress_basename(self) -> str:
        return f"progress_{self._runtime_settings_suffix()}.json"

    def _default_run_dirname(self) -> str:
        return self._runtime_settings_suffix()

    def _default_merge_progress_basename(self) -> str:
        return f"runtime_merge_{self._runtime_settings_suffix()}.json"

    def _runtime_settings_suffix(self, *, include_rubrics_refine_turns: bool = True) -> str:
        parts = [
            self._sanitize_filename_token(str(self.args.model)),
            "scope",
            self._scope_token(),
            "verbal",
            str(int(self.args.ban_verbal_sample_num)),
            "iter",
            str(int(self.args.ban_iterative_sample_num)),
            "tem",
            self._sanitize_filename_token(str(self.args.model_temperature)),
            "mem",
            self._bool_token(bool(self.args.memory)),
            "refine",
            self._bool_token(bool(self.args.refine_rubrics)),
        ]
        if include_rubrics_refine_turns:
            parts.extend(
                [
                    "mturns",
                    str(int(getattr(self.args, "rubrics_refine_max_turns", 0) or 0)),
                ]
            )
        parts.extend(
            [
            "hint",
            self._bool_token(bool(getattr(self.args, "hint", False))),
            "direct-elicit",
            self._bool_token(bool(getattr(self.args, "direct_elicit", False))),
            ]
        )
        if getattr(self.args, "trial_num", None) is not None:
            parts.extend(["trial", str(int(self.args.trial_num))])
        return "_".join(parts)

    def _scope_token(self) -> str:
        raw = getattr(self.args, "ban_only", None)
        if raw in (None, "", "null"):
            return "both"
        return self._sanitize_filename_token(str(raw))

    @staticmethod
    def _bool_token(value: bool) -> str:
        return "on" if value else "off"

    @staticmethod
    def _sanitize_filename_token(value: str) -> str:
        text = str(value).strip()
        text = text.replace("/", "-")
        text = re.sub(r"\s+", "-", text)
        text = re.sub(r"[^A-Za-z0-9._-]+", "-", text)
        text = re.sub(r"-{2,}", "-", text)
        return text.strip("-_.") or "unknown"

    def build_result_path(self) -> Path:
        return self.build_run_dir()

    def build_run_dir(self) -> Path:
        if getattr(self.args, "result_out", None):
            path = Path(self.args.result_out)
            if path.suffix == ".json":
                return path.with_suffix("")
            return path
        out_dir = Path(self.args.out)
        return out_dir / "runs" / self._default_run_dirname()

    def build_merge_progress_path(self) -> Path:
        out_dir = Path(self.args.out)
        return out_dir / "merge" / self._default_merge_progress_basename()

    def build_external_run_dir(self, base_dir: Path, *, legacy: bool = False) -> Path:
        suffix = self._runtime_settings_suffix(include_rubrics_refine_turns=not legacy)
        return Path(base_dir) / "runs" / suffix

    def load_external_progress(self, base_dir: Path) -> Optional[Dict[str, Any]]:
        for path in self._iter_external_candidate_paths(base_dir, kind="run"):
            if path.exists():
                return self.load_run_folder(path)
        return None

    def load_external_result(self, base_dir: Path) -> Optional[Dict[str, Any]]:
        for path in self._iter_external_candidate_paths(base_dir, kind="run"):
            if path.exists():
                return self.load_run_folder(path)
        return None

    def _iter_external_candidate_paths(self, base_dir: Path, *, kind: str) -> List[Path]:
        base_dir = Path(base_dir)
        if kind != "run":
            raise ValueError(f"Unsupported external path kind: {kind}")

        original_refine = bool(getattr(self.args, "refine_rubrics", False))
        original_mturns = int(getattr(self.args, "rubrics_refine_max_turns", 0) or 0)
        original_temperature = float(getattr(self.args, "model_temperature", 0.0) or 0.0)
        model_name = str(getattr(self.args, "model", "") or "")
        candidates: List[Path] = []
        seen = set()

        def add_current_candidates() -> None:
            for legacy in (False, True):
                path = self.build_external_run_dir(base_dir, legacy=legacy)
                key = str(path)
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(path)

        def add_temperature_fallback_candidates() -> None:
            if model_name not in _TEMPERATURE_SOURCE_LOOKUP_EXEMPT_MODELS:
                return
            for fallback_temperature in (1.0, 0.0):
                if abs(float(fallback_temperature) - float(original_temperature)) < 1e-9:
                    continue
                self.args.model_temperature = float(fallback_temperature)
                add_current_candidates()
            self.args.model_temperature = original_temperature

        add_current_candidates()
        add_temperature_fallback_candidates()

        try:
                                                                                        
                                                                                    
            self.args.refine_rubrics = False
            self.args.rubrics_refine_max_turns = 0
            add_current_candidates()
            add_temperature_fallback_candidates()
        finally:
            self.args.refine_rubrics = original_refine
            self.args.rubrics_refine_max_turns = original_mturns
            self.args.model_temperature = original_temperature

        return candidates

    def get_query_output_copy_path(self) -> Path:
        if self.query_path is None:
            raise RuntimeError("query_path is not set")
        out_dir = Path(self.args.out)
        return out_dir / self.query_path.name

    def load_progress(self) -> Optional[Dict[str, Any]]:
        run_dir = self.build_run_dir()
        if run_dir.exists():
            return self.load_run_folder(run_dir)
        return None

    def load_run_folder(self, run_dir: Path) -> Dict[str, Any]:
        run_dir = Path(run_dir)
        metadata_path = run_dir / "metadata.json"
        queries_dir = run_dir / "queries"
        if not metadata_path.exists():
            raise FileNotFoundError(f"Run folder metadata not found: {metadata_path}")
        if not queries_dir.exists() or not queries_dir.is_dir():
            raise FileNotFoundError(f"Run folder queries directory not found: {queries_dir}")

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not isinstance(metadata, dict):
            raise ValueError(f"metadata must be a dict in {metadata_path}")

        ordered_files = self._run_query_files_from_index(run_dir)
        if not ordered_files:
            ordered_files = sorted(queries_dir.glob("*.json"))

        data: List[dict] = []
        for path in ordered_files:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError(f"query payload must be a dict in {path}")
            data.append(payload)
        return {"metadata": metadata, "data": data}

    def _run_query_files_from_index(self, run_dir: Path) -> List[Path]:
        index_path = Path(run_dir) / "index.jsonl"
        if not index_path.exists():
            return []
        out: List[Path] = []
        for line in index_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                continue
            rel = row.get("file")
            if not rel:
                continue
            path = Path(run_dir) / str(rel)
            if path.exists():
                out.append(path)
        return out

    def load_merge_progress(self) -> Optional[Dict[str, Any]]:
        path = self.build_merge_progress_path()
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("runtime merge payload must be a dict")
        return payload

    def dump_progress(self, payload: dict) -> Path:
        return self.dump_run_folder(payload)

    def dump_merge_progress(self, payload: dict) -> Path:
        output_path = self.build_merge_progress_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return output_path

    def dump_results(self, payload: dict) -> Path:
        return self.dump_run_folder(payload)

    def dump_run_folder(self, payload: dict) -> Path:
        run_dir = self.build_run_dir()
        run_dir.mkdir(parents=True, exist_ok=True)
        queries = payload.get("data") or []
        if not isinstance(queries, list):
            raise ValueError("run payload['data'] must be a list")
        metadata = dict(payload.get("metadata") or {})
        metadata["storage_format"] = "result_folder_v1"
        metadata["result_path"] = str(run_dir)
        metadata.pop("progress_path", None)

        self._write_json_atomic(run_dir / "metadata.json", metadata)
        query_rows = []
        for idx, entry in enumerate(queries):
            self.dump_run_query(entry, idx=idx, run_dir=run_dir)
            query_rows.append(self._build_index_row(entry, idx=idx))
        self._write_index_atomic(run_dir / "index.jsonl", query_rows)
        self._write_json_atomic(run_dir / "summary.json", self._build_run_summary(metadata, query_rows))
        return run_dir

    def dump_run_query(self, entry: dict, *, idx: int, run_dir: Optional[Path] = None) -> Path:
        run_dir = Path(run_dir) if run_dir is not None else self.build_run_dir()
        queries_dir = run_dir / "queries"
        queries_dir.mkdir(parents=True, exist_ok=True)
        query_id = str(entry.get("query_id") or f"idx_{idx:04d}")
        output_path = queries_dir / f"{idx:04d}_{self._sanitize_filename_token(query_id)}.json"
        self._write_json_atomic(output_path, entry)
        return output_path

    def dump_run_index_and_summary(self, payload: dict) -> Path:
        run_dir = self.build_run_dir()
        run_dir.mkdir(parents=True, exist_ok=True)
        queries = payload.get("data") or []
        if not isinstance(queries, list):
            raise ValueError("run payload['data'] must be a list")
        metadata = dict(payload.get("metadata") or {})
        metadata["storage_format"] = "result_folder_v1"
        metadata["result_path"] = str(run_dir)
        metadata.pop("progress_path", None)
        rows = [self._build_index_row(entry, idx=idx) for idx, entry in enumerate(queries)]
        self._write_json_atomic(run_dir / "metadata.json", metadata)
        self._write_index_atomic(run_dir / "index.jsonl", rows)
        self._write_json_atomic(run_dir / "summary.json", self._build_run_summary(metadata, rows))
        return run_dir

    def _build_index_row(self, entry: dict, *, idx: int) -> Dict[str, Any]:
        result = entry.get("result") or {}
        query_id = str(entry.get("query_id") or f"idx_{idx:04d}")
        turns = result.get("turns")
        if turns is None:
            turns = len(entry.get("trajectory") or [])
        return {
            "idx": int(idx),
            "query_id": query_id,
            "status": result.get("status") or "unknown",
            "stop_reason": result.get("stop_reason"),
            "turns": int(turns or 0),
            "file": f"queries/{idx:04d}_{self._sanitize_filename_token(query_id)}.json",
        }

    @staticmethod
    def _build_run_summary(metadata: dict, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        status_counts: Dict[str, int] = {}
        stop_reason_counts: Dict[str, int] = {}
        turn_counts: Dict[str, int] = {}
        for row in rows:
            status = str(row.get("status") or "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            stop_reason = str(row.get("stop_reason"))
            stop_reason_counts[stop_reason] = stop_reason_counts.get(stop_reason, 0) + 1
            turns = str(int(row.get("turns") or 0))
            turn_counts[turns] = turn_counts.get(turns, 0) + 1
        return {
            "run_name": Path(str(metadata.get("result_path") or "")).name,
            "storage_format": "result_folder_v1",
            "query_count": len(rows),
            "status_counts": status_counts,
            "stop_reason_counts": stop_reason_counts,
            "turn_counts": dict(sorted(turn_counts.items(), key=lambda item: int(item[0]))),
            "layout": {
                "metadata": "metadata.json",
                "index": "index.jsonl",
                "queries": "queries/*.json",
            },
        }

    @staticmethod
    def _write_json_atomic(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(path.name + ".tmp")
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        tmp_path.replace(path)

    @staticmethod
    def _write_index_atomic(path: Path, rows: List[Dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(path.name + ".tmp")
        tmp_path.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
            encoding="utf-8",
        )
        tmp_path.replace(path)

    def write_query_payload_copy(self, payload: dict) -> Path:
        output_query_path = self.get_query_output_copy_path()
        output_query_path.parent.mkdir(parents=True, exist_ok=True)
        output_query_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return output_query_path
