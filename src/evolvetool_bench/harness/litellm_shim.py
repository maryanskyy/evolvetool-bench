"""Drop-in synchronous replacement for litellm.completion backed by the Anthropic SDK.

The existing baselines (no_evolution, oneshot, evoskill, creator, etc.) call:

    litellm.completion(model=..., messages=..., tools=..., max_tokens=...)

and consume:

    resp.choices[0].message.content          # str
    resp.choices[0].message.tool_calls       # list[ToolCall] or None
    tc.function.name / tc.function.arguments # str JSON

This shim reproduces that interface using the Anthropic SDK directly.
Requires ANTHROPIC_API_KEY to be set in the environment.

Import pattern in baselines:
    try:
        import litellm
    except ImportError:
        from evolvetool_bench.harness import litellm_shim as litellm
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .llm_client import LLMClient


# ---------------------------------------------------------------------------
# Public wrappers matching litellm.completion / litellm.acompletion return shape
# ---------------------------------------------------------------------------

@dataclass
class _FunctionCall:
    name: str
    arguments: str  # JSON string


@dataclass
class _ToolCall:
    id: str
    type: str
    function: _FunctionCall


@dataclass
class _Message:
    content: str | None
    tool_calls: list[_ToolCall] | None = None
    role: str = "assistant"

    def model_dump(self) -> dict:
        return {"role": self.role, "content": self.content}


@dataclass
class _Choice:
    message: _Message
    finish_reason: str = "end_turn"


@dataclass
class _Usage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class _Response:
    choices: list[_Choice]
    usage: _Usage


# ---------------------------------------------------------------------------
# Model-name normaliser: strip "anthropic/" prefix if present
# ---------------------------------------------------------------------------

def _normalise_model(model: str) -> str:
    return model.removeprefix("anthropic/")


# ---------------------------------------------------------------------------
# Sync wrapper
# ---------------------------------------------------------------------------

def completion(
    model: str,
    messages: list[dict],
    *,
    tools: list[dict] | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.0,
    **_kwargs: Any,
) -> _Response:
    """Blocking completion via the Anthropic API."""
    import asyncio

    async def _run() -> _Response:
        client = LLMClient(
            model=_normalise_model(model),
            max_tokens=max_tokens,
            temperature=temperature,
        )
        # Build tool definitions for Anthropic API format
        anthropic_tools: list[dict] | None = None
        if tools:
            anthropic_tools = []
            for t in tools:
                if t.get("type") == "function":
                    fn = t["function"]
                    anthropic_tools.append({
                        "name": fn["name"],
                        "description": fn.get("description", ""),
                        "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
                    })
                else:
                    anthropic_tools.append(t)

        # Pass messages to the SDK; extract system if first message
        sys_prompt = "You are a helpful assistant."
        msgs = list(messages)
        if msgs and msgs[0].get("role") == "system":
            sys_prompt = msgs.pop(0)["content"]

        def _get(m, key, default=None):
            """Get a field from either a dict or a dataclass-like object."""
            if isinstance(m, dict):
                return m.get(key, default)
            return getattr(m, key, default)

        # Convert "tool" role messages for Anthropic format
        anthropic_msgs: list[dict] = []
        for m in msgs:
            role = _get(m, "role", "")

            if role == "tool":
                # Anthropic expects tool_result as user content block
                anthropic_msgs.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": _get(m, "tool_call_id", ""),
                        "content": _get(m, "content", ""),
                    }],
                })
            elif role == "assistant":
                tool_calls = _get(m, "tool_calls", None)
                if tool_calls:
                    # Convert OpenAI-style tool_calls to Anthropic tool_use blocks
                    content_blocks: list[dict] = []
                    text_content = _get(m, "content", None)
                    if text_content:
                        content_blocks.append({"type": "text", "text": text_content})
                    for tc in tool_calls:
                        tc_id = tc.id if hasattr(tc, "id") else tc.get("id", "")
                        tc_name = tc.function.name if hasattr(tc, "function") else tc["function"]["name"]
                        tc_args = tc.function.arguments if hasattr(tc, "function") else tc["function"]["arguments"]
                        content_blocks.append({
                            "type": "tool_use",
                            "id": tc_id,
                            "name": tc_name,
                            "input": json.loads(tc_args),
                        })
                    anthropic_msgs.append({"role": "assistant", "content": content_blocks})
                else:
                    # Plain assistant text message
                    text = _get(m, "content", "") or ""
                    if isinstance(m, dict):
                        anthropic_msgs.append(m)
                    else:
                        anthropic_msgs.append({"role": "assistant", "content": text})
            else:
                if isinstance(m, dict):
                    anthropic_msgs.append(m)
                else:
                    anthropic_msgs.append({"role": role, "content": _get(m, "content", "")})

        raw = await client.chat(
            anthropic_msgs,
            system=sys_prompt,
            tools=anthropic_tools if anthropic_tools else None,
        )

        # Parse Anthropic response into OpenAI-compatible shape
        resp_raw = raw.raw_response
        text_parts: list[str] = []
        tool_calls: list[_ToolCall] = []
        for i, block in enumerate(resp_raw.content):
            if getattr(block, "type", None) == "text":
                text_parts.append(block.text)
            elif getattr(block, "type", None) == "tool_use":
                tool_calls.append(_ToolCall(
                    id=block.id,
                    type="function",
                    function=_FunctionCall(
                        name=block.name,
                        arguments=json.dumps(block.input),
                    ),
                ))

        content = "\n".join(text_parts) or None
        msg = _Message(
            content=content,
            tool_calls=tool_calls if tool_calls else None,
        )
        return _Response(
            choices=[_Choice(message=msg)],
            usage=_Usage(
                prompt_tokens=raw.input_tokens,
                completion_tokens=raw.output_tokens,
                total_tokens=raw.input_tokens + raw.output_tokens,
            ),
        )

    # Run the async call synchronously
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, _run()).result()
        return loop.run_until_complete(_run())
    except RuntimeError:
        return asyncio.run(_run())
