"""No-evolution baseline — agent uses only seed tools, never creates new ones."""

from __future__ import annotations

import json
from typing import Any

from ..harness.runner import AgentSystem
from ..harness.safe_exec import call_with_timeout


class NoEvolutionSystem(AgentSystem):
    """Agent with seed tools only. Cannot create new tools."""

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self._tools: dict[str, Any] = {}
        self._tool_defs: list[dict] = []
        self._tools_used: list[str] = []
        self._llm_calls = 0

    def setup(self, seed_tools: list[dict]) -> None:
        self._tools = {}
        self._tool_defs = []
        for tool_def in seed_tools:
            name = tool_def["name"]
            impl = tool_def["implementation"].strip()
            ns: dict = {}
            exec(impl, ns)
            self._tools[name] = ns[name]
            # Build JSON schema (simplified)
            import inspect
            sig = inspect.signature(ns[name])
            params = {
                "type": "object",
                "properties": {p: {"type": "string"} for p in sig.parameters},
                "required": list(sig.parameters.keys()),
            }
            self._tool_defs.append({
                "type": "function",
                "function": {"name": name, "description": tool_def.get("description", ""), "parameters": params},
            })

    def run_task(self, task_description: str, verify_fn=None) -> dict:
        import litellm
        self._tools_used = []
        self._llm_calls = 0

        messages = [{"role": "user", "content": task_description}]
        for _ in range(5):
            resp = litellm.completion(
                model=self.model, messages=messages,
                tools=self._tool_defs if self._tool_defs else None,
                max_tokens=4096,
            )
            self._llm_calls += 1
            msg = resp.choices[0].message
            if not msg.tool_calls:
                return {
                    "output": msg.content or "",
                    "tools_created": [],
                    "tools_used": self._tools_used,
                    "llm_calls": self._llm_calls,
                }
            messages.append(msg)
            for tc in msg.tool_calls:
                fn = self._tools.get(tc.function.name)
                self._tools_used.append(tc.function.name)
                if fn is None:
                    result = f"Error: tool '{tc.function.name}' not found"
                else:
                    try:
                        args = json.loads(tc.function.arguments)
                        result = call_with_timeout(fn, args)
                    except Exception as e:
                        result = f"Error: {e}"
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
        return {
            "output": msg.content or "",
            "tools_created": [],
            "tools_used": self._tools_used,
            "llm_calls": self._llm_calls,
        }

    def get_library(self) -> list[dict]:
        return [{"name": n, "implementation": "", "test_suite": ""} for n in self._tools]
