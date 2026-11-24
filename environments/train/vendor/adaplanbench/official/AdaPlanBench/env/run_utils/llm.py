from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from env.construction.cons_utils.reasoning import apply_reasoning_to_chat_payload

try:
    import yaml
except Exception as exc:                    
    yaml = None
    _yaml_import_error = exc
else:
    _yaml_import_error = None

try:
    from dotenv import load_dotenv
except Exception:                    
    load_dotenv = None


DEFAULT_ENV_DOTENV = Path(__file__).resolve().parents[1] / ".env"


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    base_url: str
    api_key_env: str
    name: str
    model_id: str


class _SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:                          
        return "{" + key + "}"


def format_prompt(prompt_obj: Any, mapping: Dict[str, Any]) -> str:
    casted = {k: str(v) for k, v in mapping.items()}
    if callable(prompt_obj):
        return str(prompt_obj(**casted))
    if isinstance(prompt_obj, str):
        return prompt_obj.format_map(_SafeFormatDict(casted))
    raise ValueError("Prompt must be str or callable")


def load_dotenv_if_present(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return
    if load_dotenv is not None:
        load_dotenv(dotenv_path, override=False)
        return
    text = dotenv_path.read_text(encoding="utf-8")
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip("'\"")
        os.environ.setdefault(key, val)


def _load_yaml_text(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            raise ValueError(f"Invalid YAML structure in {path}")
        return data
    return _load_model_metadata_minimal(text, path)


def _load_model_metadata_minimal(text: str, path: Path) -> Dict[str, Any]:
    def _strip_inline_comment(value: str) -> str:
        return value.split("#", 1)[0].strip()

    providers = []
    current_provider: Optional[Dict[str, Any]] = None
    in_models = False

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if stripped == "providers:":
            continue

        if indent == 2 and stripped.startswith("- name:"):
            name = _strip_inline_comment(stripped.split(":", 1)[1])
            current_provider = {"name": name, "models": []}
            providers.append(current_provider)
            in_models = False
            continue

        if current_provider is None:
            continue

        if indent == 4 and stripped.startswith("base_url:"):
            current_provider["base_url"] = _strip_inline_comment(stripped.split(":", 1)[1])
            continue
        if indent == 4 and stripped.startswith("api_key_env:"):
            current_provider["api_key_env"] = _strip_inline_comment(stripped.split(":", 1)[1])
            continue
        if indent == 4 and stripped.startswith("models:"):
            in_models = True
            continue

        if in_models and indent == 6 and stripped.startswith("- name:"):
            model_name = _strip_inline_comment(stripped.split(":", 1)[1])
            current_provider["models"].append({"name": model_name})
            continue

        if in_models and indent == 8 and stripped.startswith("id:"):
            if not current_provider["models"]:
                raise ValueError(f"Invalid model metadata around id line in {path}")
            current_provider["models"][-1]["id"] = _strip_inline_comment(stripped.split(":", 1)[1])

    if not providers:
        raise ValueError(f"No providers found in {path}")

    return {"providers": providers}


def load_model_config(model_name: str, metadata_path: Path) -> ModelConfig:
    payload = _load_yaml_text(metadata_path)
    providers = payload.get("providers") or []

    matches = []
    for provider in providers:
        provider_name = provider.get("name")
        base_url = provider.get("base_url")
        api_key_env = provider.get("api_key_env") or ""
        for model in provider.get("models") or []:
            if model.get("name") != model_name:
                continue
            matches.append(
                ModelConfig(
                    provider=str(provider_name),
                    base_url=str(base_url),
                    api_key_env=str(api_key_env),
                    name=str(model.get("name")),
                    model_id=str(model.get("id")),
                )
            )

    if not matches:
        raise ValueError(f"Model name not found in metadata: {model_name!r}")
    if len(matches) > 1:
        raise ValueError(f"Model name is ambiguous in metadata: {model_name!r}")
    return matches[0]


def resolve_api_key(api_key_env: str) -> Optional[str]:
    if not api_key_env or api_key_env.upper() == "EMPTY":
        return None
    key = os.environ.get(api_key_env)
    if key:
        return key
    load_dotenv_if_present(DEFAULT_ENV_DOTENV)
    return os.environ.get(api_key_env)


def is_gpt5_model(name: Optional[str], model_id: Optional[str]) -> bool:
    for val in (name, model_id):
        low = str(val).lower() if val else ""
        if low.startswith("gpt-5") or "/gpt-5" in low:
            return True
    return False


def use_max_completion_tokens(name: Optional[str], model_id: Optional[str]) -> bool:
    for val in (name, model_id):
        if val and str(val).lower().startswith("gpt-5"):
            return True
    return False


def openai_chat_request(
    *,
    provider: Optional[str] = None,
    base_url: str,
    api_key: Optional[str],
    model_id: str,
    model_name: Optional[str],
    reasoning_effort: Optional[str] = None,
    prompt: Optional[str] = None,
    messages: Optional[Sequence[Dict[str, str]]] = None,
    temperature: float = 0.0,
    max_tokens: Optional[int] = None,
    timeout_s: int = 120,
    max_retries: int = 2,
    retry_backoff_s: float = 2.0,
) -> str:
    if provider == "cheng":
        try:
            from env.run_utils.cheng_gateway import chat_request as cheng_chat_request
        except ImportError as exc:
            raise RuntimeError(
                "Provider 'cheng' requires env/run_utils/cheng_gateway.py. "
                "Contact the repository maintainer for this file."
            ) from exc
        return cheng_chat_request(
            base_url=base_url,
            api_key=api_key,
            model_id=model_id,
            model_name=model_name,
            reasoning_effort=reasoning_effort,
            prompt=prompt,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_s=timeout_s,
            max_retries=max_retries,
            retry_backoff_s=retry_backoff_s,
        )

    if provider == "vertexai":
        from env.run_utils.vertex_gateway import chat_request as vertex_chat_request
        return vertex_chat_request(
            base_url=base_url,
            api_key=api_key,
            model_id=model_id,
            model_name=model_name,
            reasoning_effort=reasoning_effort,
            prompt=prompt,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_s=timeout_s,
            max_retries=max_retries,
            retry_backoff_s=retry_backoff_s,
        )

    if prompt is None and messages is None:
        raise ValueError("Either prompt or messages must be provided")

    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        url = base + "/chat/completions"
    else:
        url = base + "/v1/chat/completions"

    payload: Dict[str, Any] = {"model": model_id}
    if messages is not None:
        payload["messages"] = list(messages)
    else:
        payload["messages"] = [{"role": "user", "content": str(prompt or "")}]

    token_param_name = "max_tokens"
    if max_tokens is not None and int(max_tokens) > 0:
        if use_max_completion_tokens(model_name, model_id):
            token_param_name = "max_completion_tokens"
            payload[token_param_name] = int(max_tokens)
        else:
            payload[token_param_name] = int(max_tokens)

    if not is_gpt5_model(model_name, model_id):
        payload["temperature"] = float(temperature)
    apply_reasoning_to_chat_payload(
        payload,
        base_url=base_url,
        provider=provider,
        model_name=model_name,
        model_id=model_id,
        reasoning_effort=reasoning_effort,
    )

    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = urllib.request.Request(url, data=data, headers=headers, method="POST")

    last_exc: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout_s) as response:
                raw = response.read().decode("utf-8")
            parsed = json.loads(raw)
            try:
                return str(parsed["choices"][0]["message"]["content"])
            except Exception:
                return str(parsed)
        except urllib.error.HTTPError as exc:                                        
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            message = f"HTTP {exc.code}: {exc.reason}"
            if body:
                body_one_line = " ".join(body.strip().split())
                if len(body_one_line) > 1200:
                    body_one_line = body_one_line[:1200] + "...(truncated)"
                message = f"{message}; response={body_one_line}"
            last_exc = RuntimeError(message)
            if attempt < max_retries:
                time.sleep(retry_backoff_s * (attempt + 1))
                continue
            break
        except Exception as exc:                                        
            last_exc = exc
            if attempt < max_retries:
                time.sleep(retry_backoff_s * (attempt + 1))
                continue
            break

    raise RuntimeError(
        "Failed to reach LLM endpoint "
        f"at {url} after {max_retries + 1} attempts. "
        f"model_name={model_name} model_id={model_id} "
        f"temperature_sent={'no' if is_gpt5_model(model_name, model_id) else 'yes'} "
        f"{token_param_name}={payload.get(token_param_name)}. "
        f"Error: {last_exc}"
    )
