"""CREATOR-style baseline (Qian et al., EMNLP Findings 2023, arXiv:2305.14318).

A faithful reimplementation of CREATOR's three-stage protocol adapted to our
session-based benchmark:

  1. CREATION:  given a task, the LLM authors a Python function with documentation
                (utility, args, returns).
  2. DECISION:  given the task + the authored tool, the LLM writes a small code
                block that calls the tool and prints the answer.
  3. RECTIFICATION: if execution fails OR the answer doesn't match the expected
                format, show the LLM the error trace and ask for a rewrite. May
                produce a whole new tool. Iterates up to 3 times.

Distinct from One-Shot (no validation), Code-Evol (auto-tests + sandbox + LLM
judge), and ToolMaker-style (structured-error feedback with diagnose/rewrite split).
CREATOR's distinguishing feature is the create/use separation: the tool is
authored independently of the call-site code, and the rectification loop can
revise either.

Prompts lifted from the CREATOR repo (qiancheng0/CREATOR, Creation/prompt_lib/)
and lightly edited to remove dataset-specific framing.
"""

from __future__ import annotations

import inspect
import json
import re
import subprocess
import sys
import textwrap
from typing import Any

from ..harness.runner import AgentSystem
from ..harness.safe_exec import call_with_timeout


_MAX_RECTIFICATION_ROUNDS = 3
_SANDBOX_TIMEOUT_SEC = 30


class CREATORStyleSystem(AgentSystem):
    """CREATOR-protocol baseline: create → decide → rectify."""

    def __init__(self, model: str = "gpt-4o-mini", synthesis_model: str = "gpt-4o-mini",
                 max_rectification: int = _MAX_RECTIFICATION_ROUNDS):
        self.model = model
        self.synthesis_model = synthesis_model
        self.max_rectification = max_rectification

        self._tools: dict[str, Any] = {}
        self._tool_defs: list[dict] = []
        self._tool_impls: list[dict] = []

        self._tools_used: list[str] = []
        self._tools_created_this_task: list[dict] = []
        self._llm_calls: int = 0

    # ── AgentSystem interface ──────────────────────────────────────

    def setup(self, seed_tools: list[dict]) -> None:
        self._tools = {}
        self._tool_defs = []
        self._tool_impls = []
        for tool_def in seed_tools:
            self._register_tool(tool_def)

    def run_task(self, task_description: str, verify_fn=None) -> dict:
        self._tools_used = []
        self._tools_created_this_task = []
        self._llm_calls = 0

        # First try the task with the current library (seed + previously created tools)
        output, succeeded = self._attempt_task(task_description, verify_fn=verify_fn)

        # If the agent didn't succeed, switch into the CREATOR protocol:
        # create → decide → rectify
        if not succeeded:
            output, succeeded = self._creator_protocol(task_description, output)

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

    # ── CREATOR protocol ───────────────────────────────────────────

    def _creator_protocol(self, task: str, prior_output: str) -> tuple[str, bool]:
        """Three-stage CREATOR: create tool → decide call site → rectify until ok."""
        # Stage 1: CREATION
        tool = self._call_creation(task, prior_output)
        if tool is None:
            return prior_output, False

        # Stage 2: DECISION
        call_code = self._call_decision(task, tool["implementation"])
        if call_code is None:
            return prior_output, False

        # Compose full script: tool definition + call site
        script = tool["implementation"] + "\n\n" + call_code
        rectification_attempts = 0

        while True:
            exec_result = self._run_script(script)
            if exec_result["ok"]:
                # Got a successful execution — extract printed output
                # Register the tool in the persistent library
                self._register_tool({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "implementation": tool["implementation"],
                    "test_suite": "",
                })
                self._tools_created_this_task.append({
                    "name": tool["name"],
                    "implementation": tool["implementation"],
                    "test_suite": "",
                })
                return exec_result["stdout"], len(exec_result["stdout"].strip()) > 20

            if rectification_attempts >= self.max_rectification:
                # Give up; keep the tool around only if the agent committed
                # something potentially useful. CREATOR commits anyway because
                # rectification can succeed later under reuse.
                return prior_output, False

            # Stage 3: RECTIFICATION
            rectified = self._call_rectification(task, script, exec_result["error"])
            if rectified is None:
                return prior_output, False
            script = rectified
            rectification_attempts += 1

            # Re-extract tool source from rectified script (everything up to the
            # last `def ` block's end). This is a heuristic that mirrors how
            # CREATOR's rectification often rewrites the tool entirely.
            new_tool_src = self._extract_tool_def(script, tool["name"])
            if new_tool_src:
                tool["implementation"] = new_tool_src

    # ── LLM call helpers (adapted from CREATOR's published prompts) ──

    def _call_creation(self, task: str, prior_output: str) -> dict | None:
        """CREATION stage: LLM authors a Python tool with documentation."""
        import litellm

        prompt = textwrap.dedent(f"""
        You are asked to use python code to create a tool that is helpful in solving the problem.
        You should create a tool with documentation stating the utility, input, and output clearly.
        You can leverage other python standard library packages in your tool.

        ### Problem
        {task}

        ### Prior attempt (without this tool)
        {prior_output[:600] if prior_output else "(none)"}

        ### Response

        Author a single Python function in a ```python ... ``` block. The function should:
          - have a clear, descriptive snake_case name
          - take simple scalar parameters (str, int, float) if possible
          - return a value (string, int, list, or dict) that can be printed
          - include a docstring with: Utility, Args, Returns
          - use only the Python standard library
          - be self-contained (any imports go inside the function body)

        Respond with ONLY a Python code block. No JSON, no markdown commentary.
        """).strip()

        try:
            resp = litellm.completion(
                model=self.synthesis_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
            )
            self._llm_calls += 1
            raw = resp.choices[0].message.content or ""
            code = self._extract_code_block(raw)
            if not code or "def " not in code:
                return None
            name = self._extract_fn_name(code)
            if not name:
                return None
            return {
                "name": name,
                "description": f"Tool authored by CREATOR-style for task: {task[:80]}",
                "implementation": code.strip(),
            }
        except Exception:
            return None

    def _call_decision(self, task: str, tool_impl: str) -> str | None:
        """DECISION stage: LLM writes the call site that invokes the tool."""
        import litellm

        prompt = textwrap.dedent(f"""
        You are asked to use the given tool to solve the problem.
        Read the tool's documentation carefully and understand how and when to use it.
        In your response, call the tool to solve the problem and finally print the answer.

        ### Problem
        {task}

        ### Tool
        ```python
        {tool_impl}
        ```

        ### Response

        Write a small Python code block (no function definitions; the tool is already defined above)
        that calls the tool with arguments derived from the problem, computes the answer, and prints
        it. Use `print(...)` so the output appears on stdout. Wrap in ```python ... ```.
        """).strip()

        try:
            resp = litellm.completion(
                model=self.synthesis_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
            )
            self._llm_calls += 1
            raw = resp.choices[0].message.content or ""
            return self._extract_code_block(raw)
        except Exception:
            return None

    def _call_rectification(self, task: str, original_script: str, error_info: str) -> str | None:
        """RECTIFICATION stage: LLM rewrites the script given the execution error."""
        import litellm

        prompt = textwrap.dedent(f"""
        ### Instruction
        Your original code met an error when executing. Please rectify your code.
        Generate the whole new piece of code (tool definition + call site), not a snippet.
        Wrap your code in ```python ... ``` as a single block.
        Pay attention to the conditions in the question. Your goal is to answer the question
        correctly, not just to execute successfully.
        If necessary, you can also generate a whole new tool.

        ### Problem
        {task}

        ### Original Code
        ```python
        {original_script}
        ```

        ### Error Information
        {error_info[:2000]}

        ### Rectified Code
        """).strip()

        try:
            resp = litellm.completion(
                model=self.synthesis_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
            )
            self._llm_calls += 1
            raw = resp.choices[0].message.content or ""
            return self._extract_code_block(raw)
        except Exception:
            return None

    # ── Script execution in sandbox ────────────────────────────────

    def _run_script(self, script: str) -> dict:
        """Run a script in a subprocess. Returns {ok, stdout, error}."""
        try:
            p = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True, text=True, timeout=_SANDBOX_TIMEOUT_SEC,
            )
            ok = (p.returncode == 0) and bool((p.stdout or "").strip())
            return {
                "ok": ok,
                "stdout": p.stdout or "",
                "error": (p.stderr or "") if not ok else "",
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "stdout": "", "error": f"timeout after {_SANDBOX_TIMEOUT_SEC}s"}
        except Exception as e:
            return {"ok": False, "stdout": "", "error": f"sandbox error: {e}"}

    # ── Tool registration (same convention as other baselines) ────

    def _register_tool(self, tool_def: dict) -> None:
        name = tool_def["name"]
        impl = tool_def["implementation"].strip()

        ns: dict = {}
        exec(impl, ns)  # noqa: S102
        fn = ns.get(name)
        if fn is None:
            callables = {k: v for k, v in ns.items() if callable(v) and not k.startswith("_")}
            if not callables:
                raise ValueError(f"No callable named '{name}' in implementation")
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
            "test_suite": "",
        })

    # ── Agent loop ─────────────────────────────────────────────────

    def _attempt_task(self, task_description: str, verify_fn=None) -> tuple[str, bool]:
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

        # Prefer the external verifier (faster, deterministic); fall back to LLM judge.
        if verify_fn is not None:
            try:
                return final_output, bool(verify_fn(final_output))
            except Exception:
                pass
        judge_score = self._judge_output(task_description, final_output)
        return final_output, judge_score >= 0.5

    def _judge_output(self, task: str, output: str) -> float:
        """LLM-as-judge: did the agent actually solve the task?"""
        import litellm

        if len(output.strip()) < 10:
            return 0.0
        prompt = (
            "You are evaluating whether an AI agent successfully completed a task.\n\n"
            f"TASK: {task[:1500]}\n\n"
            f"AGENT OUTPUT: {output[:1500]}\n\n"
            "Did the agent produce a CORRECT, CONCRETE answer to the task? "
            "Not just an explanation of how to solve it, but the actual result?\n\n"
            "Score 0.0 if the agent said it cannot do it, gave instructions instead of a result, "
            "or produced an incorrect answer.\n"
            "Score 0.5 if the agent produced a partial or approximately correct answer.\n"
            "Score 1.0 if the agent produced the complete correct answer.\n\n"
            "Return ONLY a number: 0.0, 0.5, or 1.0"
        )
        try:
            resp = litellm.completion(
                model=self.synthesis_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
            )
            self._llm_calls += 1
            text = (resp.choices[0].message.content or "").strip()
            m = re.search(r"(\d+\.?\d*)", text)
            if m:
                return max(0.0, min(1.0, float(m.group(1))))
        except Exception:
            pass
        return 0.5

    # ── Code-extraction utilities ──────────────────────────────────

    @staticmethod
    def _extract_code_block(text: str) -> str:
        """Pull a ```python ... ``` block out of LLM output."""
        m = re.search(r"```(?:python)?\s*\n(.*?)\n```", text, flags=re.DOTALL)
        if m:
            return m.group(1).strip()
        # Fallback: strip leading/trailing fences if any
        s = re.sub(r"^```[a-zA-Z]*\n?", "", text.strip())
        s = re.sub(r"\n?```$", "", s.strip())
        return s.strip()

    @staticmethod
    def _extract_fn_name(code: str) -> str | None:
        m = re.search(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", code)
        return m.group(1) if m else None

    @staticmethod
    def _extract_tool_def(script: str, fn_name: str) -> str | None:
        """Pull the named function definition out of a script (if present)."""
        # Match `def <name>(...)` up through the next blank line at column 0.
        pattern = re.compile(
            rf"^(def\s+{re.escape(fn_name)}\s*\(.*?)(?=^\S|\Z)",
            flags=re.MULTILINE | re.DOTALL,
        )
        m = pattern.search(script)
        return m.group(1).rstrip() if m else None
