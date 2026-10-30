from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from .accounting import token_usage, token_summary, model_call
from .media import split_media, model_content
from .storage import write_json

MAX_TOKENS = 16000
RETRY_SLEEP = (2, 4, 8, 16)
PROVIDERS_FILE = Path(__file__).resolve().parents[2] / "config" / "providers.json"
AUTH_MODES = ("x-api-key", "bearer")
SEARCH_MODES = ("dynamic", "direct", "basic", "openrouter", "off")
LOCALIZED_CREDIT_EXHAUSTION = re.compile(
    "(?:\u4f59\u989d|\u9918\u984d)\\s*(?:\u4e0d\u8db3|(?:\u5df2)?(?:\u7528\u5b8c|\u7528\u5c3d|\u8017\u5c3d))"
    "|(?:api\\s*key|\u4ee4\u724c|\u8d26\u6237|\u5e33\u6236)\\s*(?:\u989d\u5ea6|\u984d\u5ea6)\\s*(?:\u4e0d\u8db3|(?:\u5df2)?(?:\u7528\u5b8c|\u7528\u5c3d|\u8017\u5c3d))", re.I)


class AgentError(RuntimeError):
    def __init__(self, message: str, code: str = "agent_error"):
        super().__init__(message)
        self.code = code


class ProviderConfigError(ValueError):
    pass


@dataclass
class Tool:
    name: str
    description: str
    schema: dict
    handler: Callable[[dict], Any]
    strict: bool = False

    def definition(self) -> dict:
        d = {"name": self.name, "description": self.description, "input_schema": self.schema}
        if self.strict:
            d["strict"] = True
        return d


@dataclass
class RunResult:
    result: Any
    turns: int
    usage: dict = field(default_factory=dict)
    token_accounting: dict = field(default_factory=dict)


def _setting(env, *names):
    for name in names:
        value = env.get(name) if name else None
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _flag(value, name):
    if value is None:
        return None
    if re.fullmatch(r"on|true|1", value, re.I):
        return True
    if re.fullmatch(r"off|false|0", value, re.I):
        return False
    raise ProviderConfigError(f"{name} must be on or off")


def canonical_model(model) -> str:
    return re.sub(r"^~", "", str(model or "").split("/")[-1]).replace(".", "-")


def provider_config() -> dict:
    path = Path(os.environ.get("TRINITY_PROVIDERS_FILE") or PROVIDERS_FILE)
    if not path.is_file():
        raise ProviderConfigError(f"Provider table not found: {path}; set TRINITY_PROVIDERS_FILE")
    return json.loads(path.read_text(encoding="utf-8"))


def active_provider_id(env=None) -> str:
    env = os.environ if env is None else env
    return _setting(env, "TRINITY_PROVIDER") or provider_config()["default"]


def _base_url(value, provider_id):
    if not value:
        raise ProviderConfigError(f"Set TRINITY_BASE_URL for the {provider_id} provider")
    url = re.sub(r"/v1$", "", str(value).strip().rstrip("/"))
    if not re.match(r"^https://[^/\s]+", url, re.I) and not re.match(r"^http://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?(/|$)", url, re.I):
        raise ProviderConfigError("The provider base URL must use https")
    return url


def resolve_profile(provider_id=None, env=None) -> dict:
    env = os.environ if env is None else env
    config = provider_config()
    provider_id = provider_id or active_provider_id(env)
    preset = config["providers"].get(provider_id)
    if preset is None:
        raise ProviderConfigError(f"Unknown provider {provider_id}; choose one of {', '.join(config['providers'])}")
    active = provider_id == active_provider_id(env)

    def override(*names):
        return _setting(env, *names) if active else None

    legacy_search = "off" if override("PIPELINE_WEB_SEARCH") == "off" else None
    session = _flag(override("TRINITY_SESSION_AFFINITY"), "TRINITY_SESSION_AFFINITY")
    profile = {"id": provider_id, "label": preset["label"], "baseUrl": _base_url(override("TRINITY_BASE_URL") or preset["baseUrl"], provider_id),
               "auth": (override("TRINITY_AUTH") or preset["auth"]).lower(), "keyEnv": preset["keyEnv"],
               "model": override("TRINITY_MODEL", "PIPELINE_MODEL") or preset["model"],
               "effort": override("TRINITY_EFFORT", "PIPELINE_EFFORT") or config["effort"],
               "apiVersion": override("TRINITY_API_VERSION") or preset["apiVersion"],
               "webSearch": (override("TRINITY_WEB_SEARCH") or legacy_search or preset["webSearch"]).lower(),
               "sessionAffinity": preset["sessionAffinity"] if session is None else session}
    if profile["auth"] not in AUTH_MODES:
        raise ProviderConfigError("TRINITY_AUTH must be x-api-key or bearer")
    if profile["webSearch"] not in SEARCH_MODES:
        raise ProviderConfigError(f"TRINITY_WEB_SEARCH must be one of {', '.join(SEARCH_MODES)}")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", profile["apiVersion"]):
        raise ProviderConfigError("TRINITY_API_VERSION must be a date such as 2023-06-01")
    return profile


def provider_key(profile, env=None):
    env = os.environ if env is None else env
    return _setting(env, profile["keyEnv"], "TRINITY_API_KEY")


def require_key(profile, env=None) -> str:
    key = provider_key(profile, env)
    if not key:
        extra = "" if profile["keyEnv"] == "TRINITY_API_KEY" else " or TRINITY_API_KEY"
        raise ProviderConfigError(f"Set {profile['keyEnv']}{extra} for the {profile['id']} provider")
    return key


def client(profile=None):
    import anthropic
    profile = profile or resolve_profile()
    key = require_key(profile)
    credential = {"auth_token": key} if profile["auth"] == "bearer" else {"api_key": key}

    def key_header(request):
        if request.headers.get("Authorization") == f"Bearer {key}":
            del request.headers["Authorization"]
            request.headers["X-Api-Key"] = key
        return request

    transport = anthropic.DefaultHttpxClient(trust_env=False, **({"auth": key_header} if "api_key" in credential else {}))
    return anthropic.Anthropic(**credential, base_url=profile["baseUrl"], default_headers={"anthropic-version": profile["apiVersion"]},
                               max_retries=0, http_client=transport)


def session_metadata(session_id) -> dict:
    value = list(hashlib.sha256(str(session_id).encode("utf-8")).hexdigest()[:32])
    value[12] = "4"
    value[16] = format((int(value[16], 16) & 3) | 8, "x")
    value = "".join(value)
    user = {"device_id": hashlib.sha256(b"trinity").hexdigest(), "account_uuid": "",
            "session_id": f"{value[:8]}-{value[8:12]}-{value[12:16]}-{value[16:20]}-{value[20:]}"}
    return {"user_id": json.dumps(user, separators=(",", ":"))}


def provider_code(status, detail) -> str:
    detail = str(detail or "")
    if status == 402 or LOCALIZED_CREDIT_EXHAUSTION.search(detail) or re.search(r"insufficient.*(?:balance|credit|quota)|(?:balance|credit|quota).*(?:exhaust|deplet|empty)|billing|payment required", detail, re.I):
        return "provider_quota"
    if status in (401, 403) or re.search(r"authentication_error|permission_error|invalid.{0,12}(?:api.?key|token)", detail, re.I):
        return "provider_auth"
    if status == 429 or re.search(r"rate_limit_error", detail, re.I):
        return "provider_rate_limit"
    if status == 400 and re.search(r"organization has been disabled", detail, re.I):
        return "provider_upstream"
    return "provider_error"


def _type_of(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) or (isinstance(value, float) and value.is_integer()):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def check_args(schema, value, where: str = "arguments") -> list[str]:
    problems: list[str] = []

    def visit(s, v, p):
        if not isinstance(s, dict):
            return
        kinds = s.get("type")
        kinds = kinds if isinstance(kinds, list) else [kinds] if kinds else []
        actual = _type_of(v)
        if kinds and not any(k == actual or (k == "number" and actual == "integer") for k in kinds):
            problems.append(f"{p} must be {' or '.join(kinds)}")
            return
        if "enum" in s and v not in s["enum"]:
            problems.append(f"{p} must be one of {', '.join(map(str, s['enum']))}")
        if actual == "string":
            if len(v.strip()) < s.get("minLength", 0):
                problems.append(f"{p} is too short")
            if "maxLength" in s and len(v) > s["maxLength"]:
                problems.append(f"{p} has {len(v)} characters; maximum is {s['maxLength']}")
            if "pattern" in s and not re.search(s["pattern"], v):
                problems.append(f"{p} must match the pattern {s['pattern']}")
        if actual in ("integer", "number"):
            if "minimum" in s and v < s["minimum"]:
                problems.append(f"{p} must be at least {s['minimum']}")
            if "maximum" in s and v > s["maximum"]:
                problems.append(f"{p} must be at most {s['maximum']}")
        if actual == "array":
            if len(v) < s.get("minItems", 0):
                problems.append(f"{p} needs at least {s['minItems']} item(s)")
            if "maxItems" in s and len(v) > s["maxItems"]:
                problems.append(f"{p} allows at most {s['maxItems']} item(s)")
            for index, item in enumerate(v):
                visit(s.get("items"), item, f"{p}[{index}]")
        if actual == "object":
            properties = s.get("properties", {})
            for name in s.get("required", []):
                if name not in v:
                    problems.append(f"{p}.{name} is required")
            for name, item in v.items():
                if name in properties:
                    visit(properties[name], item, f"{p}.{name}")
                elif s.get("additionalProperties") is False:
                    problems.append(f"{p}.{name} is not allowed")

    visit(schema, value, where)
    return problems


def _public_blocks(content) -> list[dict]:
    return [block.model_dump(exclude_none=True) for block in content if block.type not in ("thinking", "redacted_thinking")]


def _message_blocks(content) -> list[dict]:
    return [block.model_dump(exclude_none=True) for block in content]


def _create(api, **params):
    try:
        import anthropic
    except ImportError:
        anthropic = None
    records = []
    for attempt, sleep in enumerate((*RETRY_SLEEP, None), 1):
        stream = None
        started = datetime.now(timezone.utc).isoformat()
        try:
            with api.messages.stream(**params) as stream:
                response = stream.get_final_message()
            records.append({"attemptId": str(uuid4()), "startedAt": started, "finishedAt": datetime.now(timezone.utc).isoformat(), "failed": False, "requestId": getattr(response, "_request_id", None), "usage": token_usage(response.usage)})
            return response, records
        except Exception as error:
            usage = token_usage(getattr(error, "usage", None))
            try:
                snapshot = getattr(stream, "current_message_snapshot", None)
                if snapshot is not None:
                    usage = token_usage(snapshot.usage)
            except Exception:
                pass
            usage["partial"] = True
            records.append({"attemptId": str(uuid4()), "startedAt": started, "finishedAt": datetime.now(timezone.utc).isoformat(), "failed": True, "requestId": getattr(error, "request_id", None), "usage": token_usage(usage)})
            status = getattr(error, "status_code", None)
            code = provider_code(status, getattr(error, "message", error))
            connection = anthropic is not None and isinstance(error, anthropic.APIConnectionError)
            transient = code not in ("provider_quota", "provider_auth") and (status in (408, 409, 425, 429) or (status or 0) >= 500 or connection or code == "provider_upstream")
            if transient and sleep is not None:
                time.sleep(sleep)
                continue
            failure = AgentError(f"provider {status}: {getattr(error, 'message', error)}", code) if status is not None else error
            failure.attemptRecords = records
            failure.attempts = attempt
            raise failure from (error if failure is not error else None)


def _fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def run_agent(*, key: str, system: str, kickoff: str, tools: list[Tool], checkpoint_dir: Path, max_turns: int = 40,
              max_tokens: int = MAX_TOKENS, api=None, log=print) -> RunResult:
    profile = resolve_profile()
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    path = checkpoint_dir / (key.replace("/", "__") + ".json")
    definitions = [t.definition() for t in tools]
    opening = model_content(kickoff)
    contract = _fingerprint({"system": system, "kickoff": opening, "tools": definitions, "model": canonical_model(profile["model"]), "effort": profile["effort"]})
    state = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    if state is not None and state.get("contract") != contract:
        archive = path.with_name(f"{path.stem}.archived-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}.json")
        os.replace(path, archive)
        log(f"{key}: the saved checkpoint was produced from different inputs; archived as {archive.name} and running again")
        state = None
    if state is None:
        state = {"key": key, "contract": contract, "provider": profile["id"], "model": profile["model"], "effort": profile["effort"], "sessionId": uuid4().hex,
                 "status": "running", "turn": 0, "usage": {"input": 0, "output": 0}, "modelCalls": [],
                 "messages": [{"role": "user", "content": opening}], "result": None, "log": []}
    if state.get("status") == "done":
        return RunResult(state["result"], state["turn"], state["usage"], state.get("tokenAccounting", {}))
    api = api or client(profile)
    by_name = {t.name: t for t in tools}
    messages = [dict(m) for m in state["messages"]]
    if "legacyUsage" not in state:
        recorded = token_summary(state.get("modelCalls", []))
        state["legacyUsage"] = {name: max(0, state.get("usage", {}).get(name, 0) - recorded[name]["known"]) for name in ("input", "output", "cachedInput", "cacheCreationInput")}
    state.setdefault("sessionId", uuid4().hex)

    def save():
        accounting = token_summary(state.get("modelCalls", []))
        if any(state["legacyUsage"].values()):
            accounting["legacyUsage"] = state["legacyUsage"]
            accounting["complete"] = False
            accounting["exactTotal"] = None
        state["tokenAccounting"] = accounting
        state["usage"] = {name: state["legacyUsage"].get(name, 0) + accounting[name]["known"] for name in ("input", "output", "cachedInput", "cacheCreationInput")}
        state["usageIsLowerBound"] = not accounting["complete"]
        write_json(path, state)

    def record_call(attempts, failed):
        call = model_call(attempts, failed, profile["model"])
        call["provider"] = profile["id"]
        state.setdefault("modelCalls", []).append(call)

    def run_tools(calls, truncated):
        results, finished = [], None
        for call in calls:
            name, arguments = call.get("name"), call.get("input")
            tool = by_name.get(name)
            try:
                if tool is None:
                    raise ValueError(f"unknown tool {name}; registered tools: {', '.join(by_name)}")
                if truncated:
                    raise ValueError("the response was truncated at its token ceiling; its tool calls cannot be executed. Resubmit a shorter, complete call.")
                problems = check_args(tool.schema, arguments)
                if problems:
                    raise ValueError("; ".join(problems[:8]))
                value = tool.handler(arguments)
                if isinstance(value, dict) and "finish" in value:
                    if len(calls) != 1:
                        raise ValueError("Submit in a separate turn after reading all tool results")
                    finished = (value["finish"],)
                    output = json.dumps({"ok": True, "accepted": True})
                elif isinstance(value, dict) and "attach" in value:
                    output = [{"type": "text", "text": json.dumps(value.get("output", {"ok": True}), ensure_ascii=False)}, *value["attach"]]
                else:
                    data, attachments = split_media(value if value is not None else {"ok": True})
                    output = [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}, *attachments] if attachments else json.dumps(data, ensure_ascii=False)
                state["log"].append({"turn": state["turn"], "tool": name, "ok": True})
            except Exception as error:
                output = json.dumps({"ok": False, "error": str(error)[:2000]})
                state["log"].append({"turn": state["turn"], "tool": name, "ok": False, "error": str(error)[:300]})
            results.append({"type": "tool_result", "tool_use_id": call.get("id"), "content": output})
        return results, finished

    while True:
        last = state["messages"][-1]
        content = last["content"] if last["role"] == "assistant" and isinstance(last["content"], list) else []
        pending = [block for block in content if isinstance(block, dict) and block.get("type") == "tool_use"]
        if pending:
            results, finished = run_tools(pending, state.get("lastStopReason") == "max_tokens")
            messages.append({"role": "user", "content": results})
            state["messages"].append({"role": "user", "content": results})
            if finished is not None:
                state["status"], state["result"] = "done", finished[0]
                save()
                log(f"{key}: done after {state['turn']} turn(s), {state['usage']['input']} in / {state['usage']['output']} out tokens")
                return RunResult(state["result"], state["turn"], state["usage"], state["tokenAccounting"])
            save()
            continue
        if last["role"] == "assistant" and state.get("lastStopReason") != "pause_turn":
            feedback = ("The response hit its token ceiling and was truncated. Resubmit a shorter, complete tool call."
                        if state.get("lastStopReason") == "max_tokens" else
                        "Only the registered tools finish this task. Continue with the tools; the run ends only when the submit tool accepts your result.")
            messages.append({"role": "user", "content": feedback})
            state["messages"].append({"role": "user", "content": feedback})
            save()
            continue
        if state["turn"] >= max_turns:
            break
        params = dict(model=profile["model"], max_tokens=max_tokens, system=system, thinking={"type": "adaptive"},
                      output_config={"effort": profile["effort"]}, tools=definitions, messages=messages)
        if profile["sessionAffinity"]:
            params["metadata"] = session_metadata(state["sessionId"])
        try:
            response, attempts = _create(api, **params)
        except Exception as error:
            record_call(getattr(error, "attemptRecords", [{"failed": True, "usage": token_usage(getattr(error, "usage", None))}]), True)
            save()
            raise
        record_call(attempts, False)
        state["turn"] += 1
        state["lastStopReason"] = response.stop_reason
        messages.append({"role": "assistant", "content": _message_blocks(response.content)})
        state["messages"].append({"role": "assistant", "content": _public_blocks(response.content)})
        save()
        if response.stop_reason == "refusal":
            state["status"] = "refused"
            save()
            raise AgentError(f"{key}: the model declined the request", "refused")
    state["status"] = "turn_limit"
    save()
    raise AgentError(f"{key} reached its {max_turns}-turn limit without an accepted submission", "budget_exhausted")


def ask_once(*, key: str, system: str, text: str, tool: Tool, checkpoint_dir: Path, attempts: int = 8, extra_tools: list[Tool] | None = None, **kw) -> Any:
    def handler(args):
        value = tool.handler(args)
        return {"finish": value if value is not None else args}
    single = Tool(tool.name, tool.description, tool.schema, handler, tool.strict)
    return run_agent(key=key, system=system, kickoff=text, tools=[*(extra_tools or []), single], checkpoint_dir=checkpoint_dir, max_turns=attempts, **kw).result
