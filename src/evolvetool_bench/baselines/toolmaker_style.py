"""ToolMaker-style baseline (Wölflein et al., 2025, arXiv:2502.11705).

A faithful adaptation of ToolMaker's closed-loop self-correction protocol to our
session-based benchmark. ToolMaker's core innovation is structured-error feedback:
when a synthesized tool's tests fail, the agent is shown the *exact* stack trace
and asked to (a) diagnose, (b) plan a fix, (c) emit revised code. The cycle
repeats up to N times.

This is distinct from our Code-Evol (ARISE) baseline in two ways:
  1. The error signal is *test execution output* (stdout/stderr from running the
     auto-tests), not an LLM-judge score on the full trajectory.
  2. Diagnosis and code-emission are split into two LLM calls per iteration with
     a "summary of previous problems" carried forward — matching ToolMaker's
     diagnose() and rewrite_function() task split.

Note: we do not literally port ToolMaker (their repo is OpenAI-only, Docker-
based, and expects a GitHub repo as input). What we adapt is the *protocol*.
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


_MAX_ITERATIONS = 3
_SANDBOX_TIMEOUT_SEC = 30


class ToolMakerStyleSystem(AgentSystem):
    """ToolMaker-protocol baseline: structured-error closed-loop self-correction."""

    def __init__(self, model: str = "gpt-4o-mini", synthesis_model: str = "gpt-4o-mini",
                 max_iterations: int = _MAX_ITERATIONS):
        self.model = model
        self.synthesis_model = synthesis_model
        self.max_iterations = max_iterations

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
        self._verify_fn = verify_fn

        output, succeeded = self._attempt_task(task_description)

        if not succeeded:
            new_tool = self._synthesize_with_self_correction(task_description, output)
            if new_tool:
                self._tools_created_this_task.append(new_tool)
                output, succeeded = self._attempt_task(task_description)

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

    # ── Closed-loop self-correction (ToolMaker's distinguishing feature) ──

    def _synthesize_with_self_correction(self, task: str, failed_output: str) -> dict | None:
        """Synthesize a tool + tests, run, diagnose-and-fix on failure, iterate."""
        # Round 0: initial synthesis (code + auto-tests)
        synth = self._call_synthesize(task, failed_output, prior_summaries=[])
        if synth is None:
            return None

        problem_summaries: list[str] = []

        for attempt in range(self.max_iterations):
            test_result = self._run_tests(synth["implementation"], synth["test_suite"])
            if test_result["all_passed"]:
                # Promote
                self._register_tool({
                    "name": synth["name"],
                    "description": synth.get("description", ""),
                    "implementation": synth["implementation"],
                    "test_suite": synth["test_suite"],
                })
                return {
                    "name": synth["name"],
                    "implementation": synth["implementation"],
                    "test_suite": synth["test_suite"],
                }

            # Diagnose-and-fix loop
            problem_summaries.append(test_result["summary"])
            diagnosis = self._call_diagnose(
                task=task,
                code=synth["implementation"],
                test_output=test_result["output"],
                prior_summaries=problem_summaries,
            )
            if diagnosis is None:
                break

            revised = self._call_rewrite(
                task=task,
                previous_code=synth["implementation"],
                diagnosis=diagnosis,
            )
            if revised is None:
                break
            synth["implementation"] = revised["implementation"]
            if "test_suite" in revised and revised["test_suite"]:
                synth["test_suite"] = revised["test_suite"]

        # Out of iterations — drop the tool (matches ToolMaker: if all attempts fail,
        # the tool is not committed). This is stricter than our Code-Evol baseline,
        # which keeps "testing-status" tools even after refinement failure.
        return None

    # ── LLM call helpers ────────────────────────────────────────────

    def _call_synthesize(self, task: str, failed_output: str, prior_summaries: list[str]) -> dict | None:
        """Initial synthesis: produce {name, description, implementation, test_suite}."""
        import litellm

        prompt = textwrap.dedent(f"""
        You are a diligent software-engineer AI implementing a tool that another agent
        needs in order to complete the following task.

        TASK: {task}

        The agent's first attempt without this tool produced:
        FAILED OUTPUT: {failed_output[:600]}

        Write a single Python function that solves this task. Then write 3-5 unit tests
        that exercise the function on representative inputs and edge cases. The tests
        should be runnable as a standalone script: each test prints "PASS" or "FAIL: <reason>".

        Constraints:
          - Function takes only simple scalar parameters (str, int, float).
          - Returns a string.
          - Uses only the Python standard library.
          - When catching exceptions, output `traceback.format_exc()` to stderr so
            that diagnostic information is preserved for later inspection.

        Respond with a JSON object containing exactly these keys:
          name           — function name (snake_case)
          description    — one sentence describing what it does
          implementation — the full Python function source code (no markdown fences)
          test_suite     — a Python script that imports the function and runs 3-5 tests,
                           each printing "PASS" or "FAIL: <details>"

        Return ONLY the JSON object, no markdown.
        """).strip()

        try:
            resp = litellm.completion(
                model=self.synthesis_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
            )
            self._llm_calls += 1
            raw = self._strip_fences(resp.choices[0].message.content or "")
            obj = json.loads(raw)
            if {"name", "implementation", "test_suite"}.issubset(obj.keys()):
                return obj
        except Exception:
            return None
        return None

    def _call_diagnose(self, task: str, code: str, test_output: str,
                       prior_summaries: list[str]) -> str | None:
        """Diagnose-and-plan call (ToolMaker tasks/diagnose.py adapted)."""
        import litellm

        summaries_str = "\n".join(
            f"<summary number={i}>{s}</summary>" for i, s in enumerate(prior_summaries)
        ) or "<none>"

        prompt = textwrap.dedent(f"""
        Your initial code implementation did not work. This is attempt {len(prior_summaries)}
        to fix the problem.

        Previous problems and your attempts to fix them:
        <summaries>
        {summaries_str}
        </summaries>

        Current version of the code (most recent attempt):
        ```python
        {code}
        ```

        TASK the function must accomplish: {task}

        Upon running the auto-tests on this updated function, the following output was produced:
        <test_output>
        {test_output[:4000]}
        </test_output>

        As a diligent software-engineer AI, your task is now to (a) diagnose the root cause
        of the test failures and (b) formulate a plan to fix the function. Focus on:
          - What assumption in the current implementation is wrong?
          - What input regime is the test exercising that the implementation fails on?
          - How would you change the implementation?

        Respond with a single paragraph containing the diagnosis followed by the plan.
        Avoid restating the test output verbatim.
        """).strip()

        try:
            resp = litellm.completion(
                model=self.synthesis_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
            )
            self._llm_calls += 1
            return (resp.choices[0].message.content or "").strip()
        except Exception:
            return None

    def _call_rewrite(self, task: str, previous_code: str, diagnosis: str) -> dict | None:
        """Rewrite-with-plan call (ToolMaker tasks/rewrite_function.py adapted)."""
        import litellm

        prompt = textwrap.dedent(f"""
        You previously diagnosed an issue with your function implementation. Now you need
        to write the updated implementation according to the plan.

        TASK: {task}

        Previous implementation:
        ```python
        {previous_code}
        ```

        Your diagnosis and plan:
        {diagnosis}

        Implement the revised function. Keep the same function name and signature unless
        the diagnosis explicitly calls for changing it.

        Respond with a JSON object containing exactly these keys:
          implementation — the full revised Python function source code
          test_suite     — the (possibly revised) auto-test script. If you keep the prior
                           tests, return them unchanged; if you add new edge cases, include them.

        Return ONLY the JSON object, no markdown.
        """).strip()

        try:
            resp = litellm.completion(
                model=self.synthesis_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
            )
            self._llm_calls += 1
            raw = self._strip_fences(resp.choices[0].message.content or "")
            obj = json.loads(raw)
            if "implementation" in obj:
                return obj
        except Exception:
            return None
        return None

    # ── Test execution in subprocess sandbox ────────────────────────

    def _run_tests(self, implementation: str, test_suite: str) -> dict:
        """Run auto-tests in a subprocess. Returns pass/fail counts and stdout/stderr."""
        if not test_suite.strip():
            return {"all_passed": False, "passed": 0, "failed": 1,
                    "output": "no test suite provided", "summary": "no tests to run"}

        script = implementation + "\n\n" + test_suite
        try:
            p = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True, text=True, timeout=_SANDBOX_TIMEOUT_SEC,
            )
            output = (p.stdout or "") + "\n--- stderr ---\n" + (p.stderr or "")
            passed = output.count("PASS")
            failed = output.count("FAIL")
            crashed = (p.returncode != 0) and (failed == 0)
            all_passed = (failed == 0) and (not crashed) and (passed > 0)
            summary = self._summarize_failures(output, passed, failed, crashed)
            return {"all_passed": all_passed, "passed": passed, "failed": failed,
                    "output": output, "summary": summary}
        except subprocess.TimeoutExpired:
            return {"all_passed": False, "passed": 0, "failed": 1,
                    "output": f"timeout after {_SANDBOX_TIMEOUT_SEC}s",
                    "summary": "tests timed out"}
        except Exception as e:
            return {"all_passed": False, "passed": 0, "failed": 1,
                    "output": f"sandbox error: {e}", "summary": f"sandbox raised: {e}"}

    @staticmethod
    def _summarize_failures(output: str, passed: int, failed: int, crashed: bool) -> str:
        if crashed:
            tail = "\n".join(output.splitlines()[-6:])
            return f"crashed before tests completed; tail:\n{tail}"
        fail_lines = [ln for ln in output.splitlines() if "FAIL" in ln]
        body = "; ".join(fail_lines[:5]) or "no FAIL lines but mismatch"
        return f"{passed} passed, {failed} failed. {body}"

    # ── Tool registration (same convention as OneShotSystem) ────────

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
            "test_suite": tool_def.get("test_suite", ""),
        })

    def _attempt_task(self, task_description: str) -> tuple[str, bool]:
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

        # Prefer external verifier if available; otherwise use LLM judge.
        verify_fn = getattr(self, "_verify_fn", None)
        if verify_fn is not None:
            try:
                return final_output, bool(verify_fn(final_output))
            except Exception:
                pass
        judge_score = self._judge_output(task_description, final_output)
        return final_output, judge_score >= 0.5

    def _judge_output(self, task: str, output: str) -> float:
        import litellm

        if len(output.strip()) < 10:
            return 0.0
        prompt = (
            "You are evaluating whether an AI agent successfully completed a task.\n\n"
            f"TASK: {task[:1500]}\n\n"
            f"AGENT OUTPUT: {output[:1500]}\n\n"
            "Did the agent produce a CORRECT, CONCRETE answer to the task? "
            "Score 0.0 if it said it cannot do it, gave instructions, or produced incorrect output.\n"
            "Score 0.5 if it produced a partial/approximate answer.\n"
            "Score 1.0 if it produced the complete correct answer.\n\n"
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

    @staticmethod
    def _strip_fences(s: str) -> str:
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s.strip())
        s = re.sub(r"\n?```$", "", s.strip())
        return s
