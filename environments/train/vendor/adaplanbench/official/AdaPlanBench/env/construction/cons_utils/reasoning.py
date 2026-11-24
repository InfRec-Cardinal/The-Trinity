from __future__ import annotations

import json
import os
from typing import Any, Dict, Mapping, Optional


REASONING_EFFORT_ENV = "CONSTRUCTION_REASONING_EFFORT_BY_MODEL_JSON"


def normalize_reasoning_effort_map(mapping: Optional[Mapping[str, Any]]) -> Dict[str, str]:
    pass                                                                     
    normalized: Dict[str, str] = {}
    if not mapping:
        return normalized
    for raw_key, raw_value in mapping.items():
        key = str(raw_key or "").strip().casefold()
        value = str(raw_value or "").strip()
        if not key or not value:
            continue
        normalized[key] = value
    return normalized


def set_reasoning_effort_env(mapping: Optional[Mapping[str, Any]]) -> None:
    pass                                                                           
    normalized = normalize_reasoning_effort_map(mapping)
    if normalized:
        os.environ[REASONING_EFFORT_ENV] = json.dumps(normalized, ensure_ascii=True, sort_keys=True)
    else:
        os.environ.pop(REASONING_EFFORT_ENV, None)


def load_reasoning_effort_map_from_env() -> Dict[str, str]:
    raw = os.environ.get(REASONING_EFFORT_ENV)
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return normalize_reasoning_effort_map(parsed)


def resolve_reasoning_effort(
    *,
    model_name: Optional[str],
    model_id: Optional[str] = None,
) -> Optional[str]:
    pass                                                                      
    mapping = load_reasoning_effort_map_from_env()
    if not mapping:
        return None
    for raw_key in (model_name, model_id):
        key = str(raw_key or "").strip().casefold()
        if key and key in mapping:
            return mapping[key]
    return None


def _normalized_base_url(base_url: str) -> str:
    return str(base_url or "").strip().lower()


def is_openrouter_base_url(base_url: str) -> bool:
    return "openrouter.ai" in _normalized_base_url(base_url)


def is_openai_official_base_url(base_url: str, provider: Optional[str] = None) -> bool:
    if str(provider or "").strip().lower() == "openai":
        return True
    return "api.openai.com" in _normalized_base_url(base_url)


def supports_reasoning_effort_control(base_url: str, provider: Optional[str] = None) -> bool:
    pass                                                               
    return is_openrouter_base_url(base_url) or is_openai_official_base_url(base_url, provider)


def resolve_request_reasoning_effort(
    *,
    reasoning_effort: Optional[str] = None,
    model_name: Optional[str] = None,
    model_id: Optional[str] = None,
) -> Optional[str]:
    pass                                                                       
    explicit = str(reasoning_effort or "").strip()
    if explicit:
        return explicit
    return resolve_reasoning_effort(model_name=model_name, model_id=model_id)


def apply_reasoning_to_chat_payload(
    payload: Dict[str, Any],
    *,
    base_url: str,
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    model_id: Optional[str] = None,
    reasoning_effort: Optional[str] = None,
) -> None:
    pass                                                                              

                                                 
                                                                        
       
    if not supports_reasoning_effort_control(base_url, provider):
        return
    effort = resolve_request_reasoning_effort(
        reasoning_effort=reasoning_effort,
        model_name=model_name,
        model_id=model_id,
    )
    if not effort:
        return
    if is_openai_official_base_url(base_url, provider):
        payload["reasoning_effort"] = effort
        return
    if is_openrouter_base_url(base_url):
        payload["reasoning"] = {"effort": effort}


def build_reasoning_payload(
    *,
    base_url: str,
    model_name: Optional[str],
    model_id: Optional[str] = None,
    provider: Optional[str] = None,
    reasoning_effort: Optional[str] = None,
) -> Optional[Dict[str, str]]:
    pass                                                                                

                                                                
       
    if not is_openrouter_base_url(base_url):
        return None
    effort = resolve_request_reasoning_effort(
        reasoning_effort=reasoning_effort,
        model_name=model_name,
        model_id=model_id,
    )
    if not effort:
        return None
    return {"effort": effort}
