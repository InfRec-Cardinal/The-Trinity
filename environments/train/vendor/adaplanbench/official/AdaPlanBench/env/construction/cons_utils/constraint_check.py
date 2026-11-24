from __future__ import annotations

import inspect
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from env.construction import prompts as prompts_module


class _SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:                          
        return "{" + key + "}"


def format_list(items: Sequence[str]) -> str:
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    if not cleaned:
        return "None"
    return "\n".join(f"{idx + 1}. {value}" for idx, value in enumerate(cleaned))


def strip_think(text: str) -> str:
    if not text:
        return text
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    return cleaned.replace("<think>", "").replace("</think>", "")


def extract_after_final_answer(text: str) -> str:
    if not text:
        return ""
    idx = text.lower().find("<answer_start>")
    if idx == -1:
        return text
    return text[idx + len("<answer_start>") :]


def extract_filter_numbers(text: str) -> Tuple[List[int], List[int]]:
    pass                                                               
    cleaned = strip_think(extract_after_final_answer(text))
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
            else:
                pref_nums.append(num)
    return _dedupe_ints(tool_nums), _dedupe_ints(pref_nums)


def filter_by_numbers(items: Sequence[str], numbers: Sequence[int]) -> List[str]:
    pass                                                                        
    to_remove = {n for n in numbers if isinstance(n, int) and n > 0}
    if not to_remove:
        return list(items)
    return [item for idx, item in enumerate(items, start=1) if idx not in to_remove]


def select_by_numbers(items: Sequence[str], numbers: Sequence[int]) -> List[str]:
    to_select = {n for n in numbers if isinstance(n, int) and n > 0}
    if not to_select:
        return []
    return [item for idx, item in enumerate(items, start=1) if idx in to_select]


def build_check_cons_prompt(
    used_tools: Sequence[str],
    used_prefs: Sequence[str],
    *,
    resample: bool,
    planned_solution: Optional[str],
    query: Optional[str],
) -> str:
    prompt_obj = getattr(prompts_module, "check_cons_prefs_prompt", None)
    if prompt_obj is None:
        raise ValueError("Missing check_cons_prefs_prompt in prompts.py")
    tools_text = format_list(used_tools)
    prefs_text = format_list(used_prefs)
    rule_text = ""
    if resample:
        rule_text = build_resample_check_rule(planned_solution or "", query or "")
    if callable(prompt_obj):
        return str(
            prompt_obj(
                banned_tools_to_check=tools_text,
                user_prefs_to_check=prefs_text,
                BANNED_TOOLS_TO_CHECK=tools_text,
                USER_PREFS_TO_CHECK=prefs_text,
                resample_check_rule=rule_text,
                RESAMPLE_CHECK_RULE=rule_text,
            )
        )
    if isinstance(prompt_obj, str):
        mapping = _SafeFormatDict(
            {
                "banned_tools_to_check": tools_text,
                "user_prefs_to_check": prefs_text,
                "BANNED_TOOLS_TO_CHECK": tools_text,
                "USER_PREFS_TO_CHECK": prefs_text,
                "resample_check_rule": rule_text,
                "RESAMPLE_CHECK_RULE": rule_text,
            }
        )
        return prompt_obj.format_map(mapping)
    raise ValueError("check_cons_prefs_prompt must be a str or callable")


def build_resample_check_rule(planned_solution: str, query: str) -> str:
    prompt_obj = getattr(prompts_module, "resample_check_rule", None)
    if prompt_obj is None:
        raise ValueError("Missing resample_check_rule in prompts.py")
    planned_solution_text = str(planned_solution or "").strip()
    query_text = str(query or "").strip()
    if callable(prompt_obj):
        return str(
            prompt_obj(
                query=query_text,
                Query=query_text,
                planned_solution=planned_solution_text,
                PLANNED_SOLUTION=planned_solution_text,
            )
        )
    if isinstance(prompt_obj, str):
        mapping = _SafeFormatDict(
            {
                "query": query_text,
                "Query": query_text,
                "planned_solution": planned_solution_text,
                "PLANNED_SOLUTION": planned_solution_text,
            }
        )
        return prompt_obj.format_map(mapping)
    raise ValueError("resample_check_rule must be a str or callable")


def filter_constraints(
    *,
    tools: Sequence[str],
    prefs: Sequence[str],
    query: str,
    planned_solution: str,
    resample: bool,
    check_model: Any,
    openai_chat_request: Callable[..., Any],
    resolve_api_key: Callable[[str], Optional[str]],
    temperature: float,
    timeout_s: int,
    max_retries: int,
    retry_backoff_s: float,
    request_context: Optional[Dict[str, Any]] = None,
) -> Tuple[List[str], List[str], str, Dict[str, Any]]:
    pass                                                              

                                                                      
                                 
       
    tools_list = list(tools)
    prefs_list = list(prefs)
    if not tools_list and not prefs_list:
        tracking = _build_tracking(
            tools_before=tools_list,
            prefs_before=prefs_list,
            tool_nums=[],
            pref_nums=[],
        )
        return tools_list, prefs_list, "SKIPPED: empty tools/prefs pool", tracking

    prompt = build_check_cons_prompt(
        tools_list,
        prefs_list,
        resample=resample,
        planned_solution=planned_solution,
        query=query,
    )
    raw_output = _call_check_request(
        openai_chat_request=openai_chat_request,
        resolve_api_key=resolve_api_key,
        check_model=check_model,
        prompt=prompt,
        temperature=temperature,
        timeout_s=timeout_s,
        max_retries=max_retries,
        retry_backoff_s=retry_backoff_s,
        request_context=request_context,
    )
    tool_nums, pref_nums = extract_filter_numbers(raw_output)
    filtered_tools = filter_by_numbers(tools_list, tool_nums)
    filtered_prefs = filter_by_numbers(prefs_list, pref_nums)
    tracking = _build_tracking(
        tools_before=tools_list,
        prefs_before=prefs_list,
        tool_nums=tool_nums,
        pref_nums=pref_nums,
    )
    return filtered_tools, filtered_prefs, raw_output, tracking


def _call_check_request(
    *,
    openai_chat_request: Callable[..., Any],
    resolve_api_key: Callable[[str], Optional[str]],
    check_model: Any,
    prompt: str,
    temperature: float,
    timeout_s: int,
    max_retries: int,
    retry_backoff_s: float,
    request_context: Optional[Dict[str, Any]],
) -> str:
    kwargs: Dict[str, Any] = {
        "base_url": getattr(check_model, "base_url"),
        "api_key": resolve_api_key(getattr(check_model, "api_key_env", "")),
        "model_id": getattr(check_model, "model_id"),
        "model_name": getattr(check_model, "name", None),
        "prompt": prompt,
        "temperature": temperature,
        "timeout_s": timeout_s,
        "max_retries": max_retries,
        "retry_backoff_s": retry_backoff_s,
    }
    optional_kwargs = {
        "n": 1,
        "request_context": request_context,
        "api_key_env": getattr(check_model, "api_key_env", None),
        "provider": getattr(check_model, "provider", None),
    }
    try:
        signature = inspect.signature(openai_chat_request)
    except (TypeError, ValueError):
        signature = None
    for key, value in optional_kwargs.items():
        if value is None:
            continue
        if signature is None or key in signature.parameters:
            kwargs[key] = value
    raw_output = openai_chat_request(**kwargs)
    if isinstance(raw_output, list):
        return str(raw_output[0] if raw_output else "")
    return str(raw_output)


def _build_tracking(
    *,
    tools_before: Sequence[str],
    prefs_before: Sequence[str],
    tool_nums: Sequence[int],
    pref_nums: Sequence[int],
) -> Dict[str, Any]:
    removed_tools = select_by_numbers(tools_before, tool_nums)
    removed_prefs = select_by_numbers(prefs_before, pref_nums)
    filtered_tools = filter_by_numbers(tools_before, tool_nums)
    filtered_prefs = filter_by_numbers(prefs_before, pref_nums)
    return {
        "tools": {
            "before_check": list(tools_before),
            "filtered_out_numbers": list(tool_nums),
            "filtered_out_items": removed_tools,
            "after_check": filtered_tools,
            "counts": {
                "before_check": len(tools_before),
                "filtered_out": len(removed_tools),
                "after_check": len(filtered_tools),
            },
        },
        "prefs": {
            "before_check": list(prefs_before),
            "filtered_out_numbers": list(pref_nums),
            "filtered_out_items": removed_prefs,
            "after_check": filtered_prefs,
            "counts": {
                "before_check": len(prefs_before),
                "filtered_out": len(removed_prefs),
                "after_check": len(filtered_prefs),
            },
        },
    }


def _dedupe_ints(items: Sequence[int]) -> List[int]:
    seen = set()
    out: List[int] = []
    for item in items:
        value = int(item)
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out
