"""Anthropic LLM client for EvolveTool-Bench.

Requires ANTHROPIC_API_KEY to be set in the environment.
Compatible models: claude-haiku-4-5, claude-sonnet-4-6, etc.

Usage:
    from evolvetool_bench.harness.llm_client import LLMClient
    client = LLMClient(model="claude-haiku-4-5")
    response = await client.complete("user prompt here")
    # response.text, response.input_tokens, response.output_tokens
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from anthropic import AsyncAnthropic, APIError, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    raw_response: Any = field(default=None, repr=False)


@dataclass
class LLMClient:
    """Simple async Anthropic client with automatic retry."""

    model: str = "claude-haiku-4-5"
    max_retries: int = 3
    temperature: float = 0.0
    max_tokens: int = 4096

    def __post_init__(self) -> None:
        self._client: AsyncAnthropic | None = None

    def _ensure_client(self) -> AsyncAnthropic:
        if self._client is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "ANTHROPIC_API_KEY is not set. "
                    "Export your Anthropic API key before running experiments."
                )
            self._client = AsyncAnthropic(api_key=api_key, max_retries=0)
        return self._client

    async def complete(
        self,
        prompt: str,
        *,
        system: str = "You are a helpful assistant.",
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        """Single-turn completion, returning the assistant's text."""
        return await self._call_with_retry(
            messages=[{"role": "user", "content": prompt}],
            system=system,
            tools=tools,
        )

    async def chat(
        self,
        messages: list[dict],
        *,
        system: str = "You are a helpful assistant.",
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        """Multi-turn completion."""
        return await self._call_with_retry(messages=messages, system=system, tools=tools)

    async def _call_with_retry(
        self,
        messages: list[dict],
        *,
        system: str,
        tools: list[dict] | None,
    ) -> LLMResponse:
        client = self._ensure_client()

        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=2, min=2, max=20),
            retry=retry_if_exception_type((APIError, RateLimitError)),
            reraise=True,
        )
        async def _do() -> LLMResponse:
            kwargs: dict[str, Any] = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "system": system,
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools

            resp = await client.messages.create(**kwargs)
            text = "".join(
                b.text for b in resp.content if getattr(b, "type", None) == "text"
            )
            return LLMResponse(
                text=text,
                input_tokens=resp.usage.input_tokens,
                output_tokens=resp.usage.output_tokens,
                raw_response=resp,
            )

        return await _do()
