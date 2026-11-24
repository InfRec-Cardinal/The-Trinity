from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from .. import run_prompts
from ..llm import ModelConfig, format_prompt, openai_chat_request, resolve_api_key
from .BaseJudger import BaseJudger


@dataclass
class ParsedEnvViolation:
    violation: bool | None
    constraint_numbers_1based: List[int]
    parse_ok: bool
    raw: str
    final_section: str
    raw_marked_items: List[str] = field(default_factory=list)


@dataclass
class ParsedPrefsViolation:
    violation: bool | None
    constraint_numbers_1based: List[int]
    parse_ok: bool
    raw: str
    final_section: str
    raw_marked_items: List[str] = field(default_factory=list)


@dataclass
class ParsedRubrics:
    scores_by_rubric: Dict[str, int]
    reasons_by_rubric: Dict[str, str]
    parse_ok: bool
    raw: str
    final_section: str


class HousingJudger(BaseJudger):
    _RUBRIC_ORDER = (
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
    _RUBRIC_NAME_ALIASES = {
        "tool-use feasibility": "Tool-use feasibility",
        "tool use feasibility": "Tool-use feasibility",
        "feasibility": "Tool-use feasibility",
        "physical plausibility": "Physical plausibility",
        "physical possibility": "Physical plausibility",
        "logical step ordering": "Logical step ordering",
        "effectiveness": "Effectiveness",
        "concreteness": "Concreteness",
        "safety": "Safety",
        "consequence awareness": "Consequence awareness",
        "autonomy": "Autonomy",
        "creativity": "Creativity",
    }

    def __init__(self, args, gen_model: ModelConfig):
        self.args = args
        self.gen_model = gen_model
        self.gen_api_key = resolve_api_key(gen_model.api_key_env)

        self._judge_api_keys: Dict[str, Optional[str]] = {}

        self.last_feedback_prompt: Optional[str] = None
        self.last_feedback_raw: Optional[str] = None

    def judge_env_constraints_one_model(
        self,
        *,
        query: str,
        plan: str,
        banned_tools: str,
        judge_model: ModelConfig,
    ) -> Dict:
        prompt = format_prompt(
            run_prompts.judge_by_env_cons_prompt,
            {
                "query": query,
                "Query": query,
                "plan": plan,
                "Plan": plan,
                "banned_tools": banned_tools,
                "BANNED_TOOLS": banned_tools,
            },
        )
        return self._call_and_parse_one_model(
            judge_model=judge_model,
            prompt=prompt,
            parse_kind="env",
        )

    def judge_user_prefs_one_model(
        self,
        *,
        query: str,
        plan: str,
        user_prefs: str,
        judge_model: ModelConfig,
    ) -> Dict:
        prompt = format_prompt(
            run_prompts.judge_by_user_prefs_prompt,
            {
                "query": query,
                "Query": query,
                "plan": plan,
                "Plan": plan,
                "user_prefs": user_prefs,
                "USER_PREFS": user_prefs,
            },
        )
        return self._call_and_parse_one_model(
            judge_model=judge_model,
            prompt=prompt,
            parse_kind="prefs",
        )

    def judge_rubrics_one_model(
        self,
        *,
        query: str,
        plan: str,
        judge_model: ModelConfig,
    ) -> Dict:
        prompt = format_prompt(
            run_prompts.judge_by_rubrics_prompt,
            {
                "query": query,
                "Query": query,
                "plan": plan,
                "Plan": plan,
            },
        )
        return self._call_and_parse_one_model(
            judge_model=judge_model,
            prompt=prompt,
            parse_kind="rubrics",
        )

    def generate_user_feedback(
        self,
        *,
        query: str,
        plan: str,
        judge_feedback: str,
        memory: str,
        refine_rubrics: str,
        tools_placeholder: str,
        prefs_placeholder: str,
    ) -> str:
        prompt = format_prompt(
            run_prompts.gen_user_feedback_prompt,
            {
                "query": query,
                "Query": query,
                "plan": plan,
                "Plan": plan,
                "judge_feedback": judge_feedback,
                "Judge_feedback": judge_feedback,
                "memory": memory,
                "Memory": memory,
                "refine_rubrics": refine_rubrics,
                "tools_placeholder": tools_placeholder,
                "prefs_placeholder": prefs_placeholder,
            },
        )

        raw = openai_chat_request(
            provider=self.gen_model.provider,
            base_url=self.gen_model.base_url,
            api_key=self.gen_api_key,
            model_id=self.gen_model.model_id,
            model_name=self.gen_model.name,
            prompt=prompt,
            temperature=float(self.args.gen_temperature),
            max_tokens=int(self.args.gen_max_tokens),
            timeout_s=int(self.args.llm_timeout_s),
            max_retries=int(self.args.llm_max_retries),
            retry_backoff_s=float(self.args.llm_retry_backoff_s),
        )
        self.last_feedback_prompt = prompt
        self.last_feedback_raw = raw

                                                                        
                                                                                          
        cleaned = str(raw or "").strip()
        if not cleaned:
            cleaned = "Please regenerate the plan."
        format_suffix = str(run_prompts.agent_response_format or "").strip()
        if not format_suffix:
            return cleaned
        return cleaned + "\n\n" + format_suffix

    def _call_and_parse_one_model(
        self,
        *,
        judge_model: ModelConfig,
        prompt: str,
        parse_kind: str,
    ) -> Dict:
        try:
            raw = openai_chat_request(
                provider=judge_model.provider,
                base_url=judge_model.base_url,
                api_key=self._resolve_judge_api_key(judge_model),
                model_id=judge_model.model_id,
                model_name=judge_model.name,
                reasoning_effort=self._resolve_judge_reasoning_effort(judge_model),
                prompt=prompt,
                temperature=float(self.args.judge_temperature),
                max_tokens=int(self.args.judge_max_tokens),
                timeout_s=int(self.args.llm_timeout_s),
                max_retries=int(self.args.llm_max_retries),
                retry_backoff_s=float(self.args.llm_retry_backoff_s),
            )
        except Exception as exc:
            return {
                "status": "error",
                "prompt": prompt,
                "raw_response": None,
                "parsed_result": None,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }

        if parse_kind in {"env", "prefs"}:
            parsed = self._parse_env_or_prefs(raw=raw, kind=parse_kind)
        elif parse_kind == "rubrics":
            parsed = self._parse_rubrics(raw=raw)
        else:
            raise ValueError(f"Unknown parse_kind: {parse_kind}")

        if not parsed.parse_ok:
            return {
                "status": "error",
                "prompt": prompt,
                "raw_response": raw,
                "parsed_result": asdict(parsed),
                "error_type": "parse_error",
                "error_message": f"Could not parse {parse_kind} judge output.",
            }

        return {
            "status": "success",
            "prompt": prompt,
            "raw_response": raw,
            "parsed_result": asdict(parsed),
            "error_type": None,
            "error_message": None,
        }

    def _resolve_judge_api_key(self, judge_model: ModelConfig) -> Optional[str]:
        cached = self._judge_api_keys.get(judge_model.name)
        if judge_model.name in self._judge_api_keys:
            return cached
        api_key = resolve_api_key(judge_model.api_key_env)
        self._judge_api_keys[judge_model.name] = api_key
        return api_key

    def _resolve_judge_reasoning_effort(self, judge_model: ModelConfig) -> Optional[str]:
        per_model = getattr(self.args, "judge_reasoning_effort_by_model", None) or {}
        if isinstance(per_model, dict):
            for raw_key in (judge_model.name, judge_model.model_id):
                key = str(raw_key or "").strip().casefold()
                if key and key in per_model:
                    return str(per_model[key]).strip() or None
        return self.args.judge_reasoning_effort

    def _extract_final_answer(self, text: str) -> str:
        raw = str(text or "")
        idx = raw.lower().find("<answer_start>")
        if idx == -1:
            return raw
        return raw[idx + len("<answer_start>") :]

    def _parse_yes_no(self, text: str) -> bool | None:
        m = re.search(r"\*\*\s*(YES|NO)\s*\*\*", text, flags=re.IGNORECASE)
        if not m:
            return None
        return m.group(1).strip().upper() == "YES"

    def _parse_constraint_numbers_1based(self, text: str) -> List[int]:
        nums = [int(m) for m in re.findall(r"##\s*(\d+)\s*##", text)]
        seen = set()
        out: List[int] = []
        for n in nums:
            if n <= 0 or n in seen:
                continue
            seen.add(n)
            out.append(n)
        return out

    def _parse_marked_items(self, text: str) -> List[str]:
        items = [x.strip() for x in re.findall(r"##\s*([^#]+?)\s*##", text) if x.strip()]
        seen = set()
        out: List[str] = []
        for item in items:
            key = item.casefold()
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
        return out

    def _parse_parenthetical_items_after_number_markers(self, text: str) -> List[str]:
        items = [x.strip() for x in re.findall(r"##\s*\d+\s*##\s*\((.*?)\)", text) if x.strip()]
        seen = set()
        out: List[str] = []
        for item in items:
            key = item.casefold()
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
        return out

    def _parse_rubric_reasons(self, text: str) -> Dict[str, str]:
        reasons: Dict[str, str] = {}
        for line in text.splitlines():
            m = re.search(r"For\s+##(.*?)##\s*:\s*(.*)", line)
            if not m:
                continue
            rubric = m.group(1).strip()
            reason = m.group(2).strip()
            if rubric and reason and rubric not in reasons:
                reasons[rubric] = reason
        return reasons

    def _canonicalize_rubric_name(self, name: str, *, index_1based: Optional[int] = None) -> Optional[str]:
        text = str(name or "").strip()
        if text:
            canon = self._RUBRIC_NAME_ALIASES.get(text.casefold())
            if canon:
                return canon
        if index_1based is not None and 1 <= int(index_1based) <= len(self._RUBRIC_ORDER):
            return self._RUBRIC_ORDER[int(index_1based) - 1]
        return None

    def _split_rubric_blocks(self, text: str) -> List[tuple[int, str]]:
        blocks: List[tuple[int, str]] = []
        pattern = re.compile(r"(?ms)^\s*(\d+)\.\s*(.*?)(?=^\s*\d+\.\s|\Z)")
        for m in pattern.finditer(text):
            idx = int(m.group(1))
            body = str(m.group(2) or "").strip()
            if not body:
                continue
            blocks.append((idx, body))
        return blocks

    def _parse_env_or_prefs(self, *, raw: str, kind: str) -> ParsedEnvViolation | ParsedPrefsViolation:
        text = str(raw or "")
        idx = text.lower().find("<answer_start>")
        final_found = idx != -1
        final_section = text[idx + len("<answer_start>") :] if final_found else text

        violation = self._parse_yes_no(final_section)
        numbers = self._parse_constraint_numbers_1based(final_section)
        marked_items = self._parse_parenthetical_items_after_number_markers(final_section)
        if not marked_items:
            marked_items = self._parse_marked_items(final_section)

        parse_ok = False
        if final_found and violation is not None:
            if violation is False:
                parse_ok = True
            else:
                parse_ok = bool(numbers or marked_items)

        if kind == "env":
            if not parse_ok and violation is None:
                return ParsedEnvViolation(
                    violation=None,
                    constraint_numbers_1based=[],
                    parse_ok=False,
                    raw=text,
                    final_section=final_section,
                    raw_marked_items=marked_items,
                )
            return ParsedEnvViolation(
                violation=violation,
                constraint_numbers_1based=numbers,
                parse_ok=parse_ok,
                raw=text,
                final_section=final_section,
                raw_marked_items=marked_items,
            )

        if not parse_ok and violation is None:
            return ParsedPrefsViolation(
                violation=None,
                constraint_numbers_1based=[],
                parse_ok=False,
                raw=text,
                final_section=final_section,
                raw_marked_items=marked_items,
            )
        return ParsedPrefsViolation(
            violation=violation,
            constraint_numbers_1based=numbers,
            parse_ok=parse_ok,
            raw=text,
            final_section=final_section,
            raw_marked_items=marked_items,
        )

    def _parse_rubrics(self, *, raw: str) -> ParsedRubrics:
        text = str(raw or "")
        idx = text.lower().find("<answer_start>")
        final_found = idx != -1
        final_section = text[idx + len("<answer_start>") :] if final_found else text
        scores_by_rubric: Dict[str, int] = {}
        reasons_by_rubric: Dict[str, str] = {}

        for block_index, block_text in self._split_rubric_blocks(final_section):
            name_match = re.search(r"\*\*(.*?)\*\*", block_text, flags=re.DOTALL)
            raw_name = name_match.group(1).strip() if name_match else ""
            canon_name = self._canonicalize_rubric_name(raw_name, index_1based=block_index)
            score_match = re.search(r"##\s*([1-5])\s*##", block_text)
            if canon_name is None or score_match is None:
                continue
            score = int(score_match.group(1))
            scores_by_rubric[canon_name] = score
            tail = block_text[score_match.end() :]
            reason_match = re.search(r"\((.*?)\)", tail, flags=re.DOTALL)
            if reason_match:
                reason = str(reason_match.group(1) or "").strip()
                if reason:
                    reasons_by_rubric[canon_name] = reason

        parse_ok = final_found and all(name in scores_by_rubric for name in self._RUBRIC_ORDER)
        return ParsedRubrics(
            scores_by_rubric=scores_by_rubric,
            reasons_by_rubric=reasons_by_rubric,
            parse_ok=parse_ok,
            raw=text,
            final_section=final_section,
        )
