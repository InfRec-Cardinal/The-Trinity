                                                                                                 

                                                                                                        
                                                                                                     
                                                                                                   
                                                                                          
                                                                                
   
import asyncio
import json
import os
import time
import uuid
from typing import Any, AsyncGenerator, Mapping, Sequence

from autogen_core import CancellationToken, FunctionCall
from autogen_core.models import (AssistantMessage, ChatCompletionClient, CreateResult, FunctionExecutionResultMessage,
                                 LLMMessage, ModelCapabilities, ModelFamily, ModelInfo, RequestUsage, SystemMessage,
                                 UserMessage)
from autogen_core.tools import Tool, ToolSchema

HERE = os.path.dirname(os.path.abspath(__file__))
H0_CALL = os.path.join(os.path.dirname(HERE), "h0", "h0_call.mjs")
NODE = os.environ.get("H0_NODE", "node")
USAGE_LIMIT_WORDS = ("usage_limit", "usage limit", "spend limit", "weekly limit", "429", "quota", "auth")


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    return "\n".join(c if isinstance(c, str) else "[image omitted]" for c in content)


def _schema(tool: Tool | ToolSchema) -> dict:
    s = tool.schema if hasattr(tool, "schema") else tool
    return {"name": s["name"], "description": s.get("description", ""), "parameters": s.get("parameters", {})}


def to_h0_turns(messages: Sequence[LLMMessage]) -> tuple[str, list]:
    pass                                                              
    system, turns = "", []
    for m in messages:
        if isinstance(m, SystemMessage):
            system += (("\n\n" if system else "") + m.content)
        elif isinstance(m, UserMessage):
            body = _text(m.content)
            if m.source and m.source != "user":
                body = f"[message from {m.source}]\n{body}"
            turns.append({"role": "user", "text": [{"type": "text", "text": body}]})
        elif isinstance(m, AssistantMessage):
            if isinstance(m.content, str):
                turns.append({"role": "assistant", "content": [{"type": "tool_use", "id": f"msg_{uuid.uuid4().hex[:12]}",
                              "name": "submit_action", "input": {"kind": "message", "text": m.content, "tool": "", "arguments_json": ""}}]})
            else:
                for fc in m.content:
                    turns.append({"role": "assistant", "content": [{"type": "tool_use", "id": fc.id, "name": "submit_action",
                                  "input": {"kind": "tool_call", "text": "", "tool": fc.name, "arguments_json": fc.arguments}}]})
        elif isinstance(m, FunctionExecutionResultMessage):
            turns.append({"role": "tool", "results": [{"id": r.call_id, "output": r.content} for r in m.content]})
    return system, turns


class H0ChatCompletionClient(ChatCompletionClient):
    pass                                                              

    def __init__(self, call_log: str | None = None, meter_log: str | None = None, max_retries: int = 20):
        self._call_log = os.path.abspath(call_log or os.environ.get("H0_CALL_LOG")) if (call_log or os.environ.get("H0_CALL_LOG")) else None
        self._meter_log = os.path.abspath(meter_log or os.environ.get("H0_METER_LOG")) if (meter_log or os.environ.get("H0_METER_LOG")) else None
        self._max_retries = max_retries
        self._total = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self._last = RequestUsage(prompt_tokens=0, completion_tokens=0)

    async def _call_node(self, payload: dict) -> dict:
        proc = await asyncio.create_subprocess_exec(NODE, H0_CALL, stdin=asyncio.subprocess.PIPE,
                                                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, _ = await proc.communicate(json.dumps(payload).encode())
        try:
            return json.loads(out.decode() or "{}")
        except json.JSONDecodeError:
            return {"error": f"h0_call returned invalid output (exit {proc.returncode})"}

    async def create(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = [],
                     tool_choice: Any = "auto", json_output: Any = None, extra_create_args: Mapping[str, Any] = {},
                     cancellation_token: CancellationToken | None = None) -> CreateResult:
        system, turns = to_h0_turns(messages)
        payload = {"roleSystem": system, "tools": [_schema(t) for t in tools], "turns": turns, "meterLog": self._meter_log}
        res, tries, t0 = None, 0, time.time()
        while True:
            res = await self._call_node(payload)
            if "error" not in res:
                break
            err = res["error"]
            if any(w in err.lower() for w in USAGE_LIMIT_WORDS):
                                                                                                               
                limit_waits = getattr(self, "_limit_waits", 0) + 1
                self._limit_waits = limit_waits
                if limit_waits > 48:
                    raise RuntimeError(f"H0 usage limit persisted for 4 h: {err}")
                if self._call_log:
                    with open(self._call_log, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "limit_wait": err[:300]}) + "\n")
                await asyncio.sleep(300)
                continue
            self._limit_waits = 0
            tries += 1
            if tries >= self._max_retries:
                raise RuntimeError(f"H0 call failed after {tries} tries: {err}")
            await asyncio.sleep(min(60, 5 * tries))
        a, u = res["args"], res.get("usage") or {}
        usage = RequestUsage(prompt_tokens=int(u.get("input", 0)) + int(u.get("cachedInput", 0)) + int(u.get("cacheCreationInput", 0)),
                             completion_tokens=int(u.get("output", 0)))
        self._last = usage
        self._total = RequestUsage(self._total.prompt_tokens + usage.prompt_tokens, self._total.completion_tokens + usage.completion_tokens)
        if a.get("kind") == "tool_call" and a.get("tool"):
            content: Any = [FunctionCall(id=f"call_{uuid.uuid4().hex[:16]}", name=a["tool"], arguments=a.get("arguments_json") or "{}")]
            finish = "function_calls"
        else:
            content, finish = a.get("text", ""), "stop"
        if self._call_log:
            with open(self._call_log, "a", encoding="utf-8") as f:
                f.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "secs": round(time.time() - t0, 1),
                                    "role_prompt_head": system[:60], "turns": len(turns), "tools": [t["name"] for t in payload["tools"]],
                                    "action": a, "usage": u, "retries": tries}) + "\n")
        return CreateResult(finish_reason=finish, content=content, usage=usage, cached=False)

    def create_stream(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = [], tool_choice: Any = "auto",
                      json_output: Any = None, extra_create_args: Mapping[str, Any] = {},
                      cancellation_token: CancellationToken | None = None) -> AsyncGenerator[str | CreateResult, None]:
        async def gen():
            yield await self.create(messages, tools=tools, tool_choice=tool_choice, json_output=json_output,
                                    extra_create_args=extra_create_args, cancellation_token=cancellation_token)
        return gen()

    async def close(self) -> None:
        return None

    def actual_usage(self) -> RequestUsage:
        return self._last

    def total_usage(self) -> RequestUsage:
        return self._total

    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        return sum(len(_text(getattr(m, "content", "")) if not isinstance(getattr(m, "content", ""), list) or
                       all(isinstance(x, str) for x in m.content) else str(m.content)) for m in messages) // 4

    def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        return max(0, 1_000_000 - self.count_tokens(messages, tools=tools))

    @property
    def capabilities(self) -> ModelCapabilities:                          
        return {"vision": False, "function_calling": True, "json_output": True}                              

    @property
    def model_info(self) -> ModelInfo:
        return {"vision": False, "function_calling": True, "json_output": True, "family": ModelFamily.UNKNOWN,
                "structured_output": True}
