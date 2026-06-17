"""One-shot tool synthesis baseline.

When a task fails with the current tool library, the agent makes a SINGLE LLM
call to synthesise a new tool, immediately exec()s it, and adds it to the
library — with no sandbox testing, no adversarial probing, and no refinement.

Purpose: isolating the value of ARISE's iterative refinement loop.
If ARISE significantly outperforms this baseline, the iteration matters.
If scores are similar, one-shot synthesis already captures most of the gain.
"""

from __future__ import annotations

import inspect
import json
import re
from typing import Any

from ..harness.runner import AgentSystem
from ..harness.safe_exec import call_with_timeout


class OneShotSystem(AgentSystem):
    """Synthesises tools one-shot (no iteration, no sandbox, no refinement)."""

    def __init__(self, model: str = "gpt-4o-mini", synthesis_model: str = "gpt-4o-mini",
                 max_synthesis_attempts: int = 1):
        self.model = model
        self.synthesis_model = synthesis_model
        # How many one-shot synthesis attempts to allow per task failure.
        # Default is 1 (true one-shot); raise to allow a tiny retry budget.
        self.max_synthesis_attempts = max_synthesis_attempts

        self._tools: dict[str, Any] = {}
        self._tool_defs: list[dict] = []
        self._tool_impls: list[dict] = []

        self._tools_used: list[str] = []
        self._tools_created_this_task: list[dict] = []
        self._llm_calls: int = 0

    # ------------------------------------------------------------------
    # AgentSystem interface
    # ------------------------------------------------------------------

    def setup(self, seed_tools: list[dict]) -> None:
        self._tools = {}
        self._tool_defs = []
        self._tool_impls = []

        for tool_def in seed_tools:
            self._register_tool(tool_def)

    def run_task(self, task_description: str, verify_fn=None) -> dict:
        import litellm

        self._tools_used = []
        self._tools_created_this_task = []
        self._llm_calls = 0
        self._verify_fn = verify_fn

        # Phase 1: attempt the task with the current library
        output, succeeded = self._attempt_task(task_description)

        # Phase 2: if it failed, try one-shot synthesis then retry once
        if not succeeded:
            for _ in range(self.max_synthesis_attempts):
                new_tool = self._synthesise_tool(task_description, output)
                if new_tool:
                    self._tools_created_this_task.append(new_tool)
                    # One retry after synthesis
                    output, succeeded = self._attempt_task(task_description)
                    if succeeded:
                        break
                else:
                    # Synthesis produced nothing usable — stop trying
                    break

        return {
            "output": output,
            "tools_created": list(self._tools_created_this_task),
            "tools_used": list(self._tools_used),
            "llm_calls": self._llm_calls,
        }

    def get_library(self) -> list[dict]:
        return list(self._tool_impls)

    def reset(self) -> None:
        self._tools = {}
        self._tool_defs = []
        self._tool_impls = []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _attempt_task(self, task_description: str) -> tuple[str, bool]:
        """Run the agent loop; return (output, success_bool)."""
        import litellm

        messages: list[dict] = [{"role": "user", "content": task_description}]
        final_output = ""

        for _ in range(5):
            resp = litellm.completion(
                model=self.model,
                messages=messages,
                tools=self._tool_defs if self._tool_defs else None,
                max_tokens=4096,
            )
            self._llm_calls += 1
            msg = resp.choices[0].message

            if not msg.tool_calls:
                final_output = msg.content or ""
                break

            messages.append(msg)
            for tc in msg.tool_calls:
                fn = self._tools.get(tc.function.name)
                self._tools_used.append(tc.function.name)
                if fn is None:
                    tool_result = f"Error: tool '{tc.function.name}' not found"
                else:
                    try:
                        args = json.loads(tc.function.arguments)
                        tool_result = call_with_timeout(fn, args)
                    except Exception as e:
                        tool_result = f"Error: {e}"
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_result,
                })

        verify_fn = getattr(self, "_verify_fn", None)
        if verify_fn is not None:
            try:
                return final_output, bool(verify_fn(final_output))
            except Exception:
                pass
        success = len(final_output.strip()) > 20
        return final_output, success

    def _synthesise_tool(self, task_description: str, failed_output: str) -> dict | None:
        """One LLM call: generate a Python tool function. No testing, no refinement."""
        import litellm

        existing_names = list(self._tools.keys())
        existing_list = ", ".join(existing_names) if existing_names else "none"

        prompt = (
            "You are a tool-synthesis agent. An AI agent failed to complete the following task "
            "using the existing tools and needs a NEW Python helper function.\n\n"
            f"TASK: {task_description}\n\n"
            f"EXISTING TOOLS: {existing_list}\n\n"
            f"FAILED OUTPUT: {failed_output[:600]}\n\n"
            "Write a single Python function that would help solve this task. "
            "The function must:\n"
            "  - Have a clear, descriptive name (snake_case)\n"
            "  - Accept only simple scalar parameters (str, int, float)\n"
            "  - Return a string result\n"
            "  - Use only the Python standard library\n"
            "  - Be self-contained (no imports outside the function body)\n\n"
            "Respond with a JSON object containing exactly these keys:\n"
            "  name           — the function name\n"
            "  description    — one sentence describing what it does\n"
            "  implementation — the complete Python function source code\n\n"
            "Return ONLY the JSON object, no markdown fences."
        )

        try:
            resp = litellm.completion(
                model=self.synthesis_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
            )
            self._llm_calls += 1
            raw = resp.choices[0].message.content or ""

            # Strip accidental markdown fences
            raw = re.sub(r"^```[a-z]*\n?", "", raw.strip())
            raw = re.sub(r"\n?```$", "", raw.strip())

            tool_def = json.loads(raw)
            required = {"name", "description", "implementation"}
            if not required.issubset(tool_def.keys()):
                return None

            # Immediately exec() with no sandbox testing (defining characteristic
            # of this baseline — contrast with ARISE's iterative validation)
            self._register_tool(tool_def)
            return {
                "name": tool_def["name"],
                "implementation": tool_def["implementation"],
                "test_suite": "",
            }
        except Exception:
            # Synthesis or exec failure — non-fatal, just return None
            return None

    def _register_tool(self, tool_def: dict) -> None:
        """exec() implementation and add to the live tool registry."""
        name = tool_def["name"]
        impl = tool_def["implementation"].strip()

        ns: dict = {}
        exec(impl, ns)  # noqa: S102
        fn = ns.get(name)
        if fn is None:
            # Try to find any callable defined in the snippet
            callables = {k: v for k, v in ns.items() if callable(v) and not k.startswith("_")}
            if not callables:
                raise ValueError(f"No callable named '{name}' found in implementation")
            name, fn = next(iter(callables.items()))

        sig = inspect.signature(fn)
        params = {
            "type": "object",
            "properties": {p: {"type": "string"} for p in sig.parameters},
            "required": list(sig.parameters.keys()),
        }

        self._tools[name] = fn
        self._tool_defs.append({
            "type": "function",
            "function": {
                "name": name,
                "description": tool_def.get("description", ""),
                "parameters": params,
            },
        })
        self._tool_impls.append({
            "name": name,
            "implementation": tool_def["implementation"],
            "test_suite": tool_def.get("test_suite", ""),
        })
