from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Optional


@dataclass
class ViolationCounter:
    disclosed_violations: int = 0
    undisclosed_violated: int = 0


@dataclass
class TurnTrace:
    turn_id: int
    agent_plan: str
    env_judge_result: dict
    prefs_judge_result: Optional[dict]
    rubrics_result: Optional[dict]
    violated_env_items: List[str]
    violated_pref_items: List[str]
    disclosed_check: dict
    chosen_feedback_type: Optional[str]
    chosen_feedback_items: List[str]
    counter_snapshot: dict
    debug: Optional[dict] = None


class Tracker:
    def __init__(self, env_profile: dict):
        self.env_profile = env_profile or {}
        self._all_tools = [str(x).strip() for x in (self.env_profile.get("tools") or []) if str(x).strip()]
        self._all_prefs = [str(x).strip() for x in (self.env_profile.get("prefs") or []) if str(x).strip()]

        self._tool_counters: Dict[str, ViolationCounter] = {}
        self._pref_counters: Dict[str, ViolationCounter] = {}
        self._tool_text_by_norm: Dict[str, str] = {}
        self._pref_text_by_norm: Dict[str, str] = {}

        self._disclosed_tools_norm: set[str] = set()
        self._disclosed_prefs_norm: set[str] = set()
        self._disclosed_tools_ordered: List[str] = []
        self._disclosed_prefs_ordered: List[str] = []

        self.turn_traces: List[TurnTrace] = []

        for tool in self._all_tools:
            norm = self._norm(tool)
            self._tool_text_by_norm.setdefault(norm, tool)
            self._tool_counters.setdefault(norm, ViolationCounter())

        for pref in self._all_prefs:
            norm = self._norm(pref)
            self._pref_text_by_norm.setdefault(norm, pref)
            self._pref_counters.setdefault(norm, ViolationCounter())

    @staticmethod
    def _norm(text: str) -> str:
        return str(text).strip().casefold()

    def _ensure_item_registered(self, item_type: str, item: str) -> str:
        norm = self._norm(item)
        if item_type == "tool":
            self._tool_text_by_norm.setdefault(norm, str(item).strip())
            self._tool_counters.setdefault(norm, ViolationCounter())
        elif item_type == "pref":
            self._pref_text_by_norm.setdefault(norm, str(item).strip())
            self._pref_counters.setdefault(norm, ViolationCounter())
        else:
            raise ValueError(f"Unknown item_type: {item_type}")
        return norm

    def get_all_constraints(self) -> dict:
        return {
            "tools": list(self._all_tools),
            "prefs": list(self._all_prefs),
        }

    def get_disclosed_constraints(self) -> dict:
        return {
            "tools": list(self._disclosed_tools_ordered),
            "prefs": list(self._disclosed_prefs_ordered),
        }

    def mark_disclosed(self, item_type: str, items: List[str]) -> None:
        for item in items:
            text = str(item).strip()
            if not text:
                continue
            norm = self._ensure_item_registered(item_type, text)
            if item_type == "tool":
                if norm not in self._disclosed_tools_norm:
                    self._disclosed_tools_norm.add(norm)
                    self._disclosed_tools_ordered.append(self._tool_text_by_norm.get(norm, text))
            else:
                if norm not in self._disclosed_prefs_norm:
                    self._disclosed_prefs_norm.add(norm)
                    self._disclosed_prefs_ordered.append(self._pref_text_by_norm.get(norm, text))

    def classify_disclosed(self, item_type: str, items: List[str]) -> dict[str, List[str]]:
        already: List[str] = []
        newly_seen: List[str] = []
        seen_local: set[str] = set()

        for item in items:
            text = str(item).strip()
            if not text:
                continue
            norm = self._ensure_item_registered(item_type, text)
            if norm in seen_local:
                continue
            seen_local.add(norm)

            if item_type == "tool":
                if norm in self._disclosed_tools_norm:
                    already.append(self._tool_text_by_norm.get(norm, text))
                else:
                    newly_seen.append(self._tool_text_by_norm.get(norm, text))
            elif item_type == "pref":
                if norm in self._disclosed_prefs_norm:
                    already.append(self._pref_text_by_norm.get(norm, text))
                else:
                    newly_seen.append(self._pref_text_by_norm.get(norm, text))
            else:
                raise ValueError(f"Unknown item_type: {item_type}")

        return {
            "already_disclosed": already,
            "newly_seen": newly_seen,
        }

    def apply_violation_counters(self, item_type: str, items: List[str]) -> dict:
        disclosed_info = self.classify_disclosed(item_type, items)

        for item in disclosed_info["already_disclosed"]:
            norm = self._ensure_item_registered(item_type, item)
            counters = self._tool_counters if item_type == "tool" else self._pref_counters
            counters[norm].disclosed_violations += 1

        for item in disclosed_info["newly_seen"]:
            norm = self._ensure_item_registered(item_type, item)
            counters = self._tool_counters if item_type == "tool" else self._pref_counters
            counters[norm].undisclosed_violated = 1

        return disclosed_info

    def sum_disclosed_violations(self) -> dict:
        total_tools = sum(c.disclosed_violations for c in self._tool_counters.values())
        total_prefs = sum(c.disclosed_violations for c in self._pref_counters.values())
        return {"tools": total_tools, "prefs": total_prefs}

    def snapshot_counters(self) -> dict:
        tool_snapshot = {
            self._tool_text_by_norm.get(norm, norm): asdict(counter)
            for norm, counter in self._tool_counters.items()
        }
        pref_snapshot = {
            self._pref_text_by_norm.get(norm, norm): asdict(counter)
            for norm, counter in self._pref_counters.items()
        }
        return {
            "tools": tool_snapshot,
            "prefs": pref_snapshot,
        }

    def record_turn(self, trace: TurnTrace) -> None:
        self.turn_traces.append(trace)

    @classmethod
    def from_exported_state(cls, env_profile: dict, state: Optional[dict]) -> "Tracker":
        tracker = cls(env_profile)
        if not isinstance(state, dict):
            return tracker

        tools = state.get("tools") or {}
        prefs = state.get("prefs") or {}

        for name, payload in tools.items():
            norm = tracker._ensure_item_registered("tool", str(name))
            counter = tracker._tool_counters[norm]
            if isinstance(payload, dict):
                counter.disclosed_violations = int(payload.get("disclosed_violations", 0) or 0)
                counter.undisclosed_violated = int(payload.get("undisclosed_violated", 0) or 0)

        for name, payload in prefs.items():
            norm = tracker._ensure_item_registered("pref", str(name))
            counter = tracker._pref_counters[norm]
            if isinstance(payload, dict):
                counter.disclosed_violations = int(payload.get("disclosed_violations", 0) or 0)
                counter.undisclosed_violated = int(payload.get("undisclosed_violated", 0) or 0)

        disclosed_tools = state.get("disclosed_tools") or []
        disclosed_prefs = state.get("disclosed_prefs") or []
        if isinstance(disclosed_tools, list):
            tracker.mark_disclosed("tool", [str(x) for x in disclosed_tools])
        if isinstance(disclosed_prefs, list):
            tracker.mark_disclosed("pref", [str(x) for x in disclosed_prefs])
        return tracker

    def export_state(self) -> dict:
        return {
            "tools": {
                self._tool_text_by_norm.get(norm, norm): asdict(counter)
                for norm, counter in self._tool_counters.items()
            },
            "prefs": {
                self._pref_text_by_norm.get(norm, norm): asdict(counter)
                for norm, counter in self._pref_counters.items()
            },
            "disclosed_tools": list(self._disclosed_tools_ordered),
            "disclosed_prefs": list(self._disclosed_prefs_ordered),
            "turn_traces": [asdict(t) for t in self.turn_traces],
        }
