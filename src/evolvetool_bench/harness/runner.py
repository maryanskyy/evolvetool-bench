"""Session runner — executes a session against an agent system and collects results."""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from typing import Any

from ..types import Session, SessionResult, Task, TaskResult, ToolRecord


class AgentSystem(ABC):
    """Interface that all baselines must implement."""

    @abstractmethod
    def setup(self, seed_tools: list[dict]) -> None:
        """Initialize with seed tools."""

    @abstractmethod
    def run_task(self, task_description: str, verify_fn=None) -> dict:
        """Run a single task.

        Args:
            task_description: natural-language task to solve.
            verify_fn: optional callable(output: str) -> bool that returns True
                if the output is correct.  Baselines MAY use this as a more
                reliable success signal than their default heuristic.

        Returns:
            {
                "output": str,         # agent's final answer
                "tools_created": [...], # list of {name, implementation, test_suite}
                "tools_used": [...],    # list of tool names invoked
                "llm_calls": int,
            }
        """

    @abstractmethod
    def get_library(self) -> list[dict]:
        """Return current tool library: [{name, implementation, test_suite}, ...]"""

    def reset(self) -> None:
        """Reset state between sessions (optional)."""
        pass


def run_session(system: AgentSystem, session: Session, verbose: bool = True) -> SessionResult:
    """Execute a full session and return diagnostic results."""
    result = SessionResult(session_id=session.id)

    # Setup with seed tools
    system.setup(session.seed_tools)
    if verbose:
        print(f"\n=== Session: {session.name} ===")
        print(f"Tasks: {len(session.tasks)} | Seed tools: {len(session.seed_tools)}\n")

    # Track which tools exist before each task (for reuse detection)
    tools_before: set[str] = {t["name"] for t in session.seed_tools}

    for i, task in enumerate(session.tasks, 1):
        if verbose:
            print(f"[{i}/{len(session.tasks)}] {task.task_type.value.upper():12s} | {task.description[:60]}...")

        start = time.time()
        # Build a verifier callable for the baseline to use as success signal
        def _make_verify_fn(t: Task):
            if t.verify is not None:
                return t.verify
            if t.expected is not None:
                exp = t.expected
                def _check(out: str) -> bool:
                    if isinstance(exp, str):
                        return exp.lower() in out.lower()
                    try:
                        parsed = json.loads(out) if isinstance(out, str) else out
                        return parsed == exp
                    except Exception:
                        return False
                return _check
            return None

        verify_fn = _make_verify_fn(task)
        try:
            agent_result = system.run_task(task.description, verify_fn=verify_fn)
        except TypeError:
            # Baseline doesn't accept verify_fn — call without it
            agent_result = system.run_task(task.description)
        except Exception as e:
            agent_result = {"output": f"Error: {e}", "tools_created": [], "tools_used": [], "llm_calls": 1}
        duration = (time.time() - start) * 1000

        # Determine pass/fail
        passed = False
        partial = False
        output = agent_result.get("output", "")

        if task.verify:
            try:
                passed = task.verify(output)
            except Exception:
                passed = False
        elif task.expected is not None:
            if isinstance(task.expected, str):
                passed = task.expected.lower() in output.lower()
            elif isinstance(task.expected, list):
                # Try exact JSON match first
                try:
                    parsed = json.loads(output) if isinstance(output, str) else output
                    if parsed == task.expected:
                        passed = True
                except (json.JSONDecodeError, TypeError):
                    pass

                # Fallback: check if key values from expected appear in output
                if not passed and isinstance(task.expected, list) and task.expected:
                    # Extract all string values from expected dicts
                    key_values = set()
                    for item in task.expected:
                        if isinstance(item, dict):
                            for v in item.values():
                                key_values.add(str(v))
                        else:
                            key_values.add(str(item))

                    # Pass if most key values appear in output
                    found = sum(1 for v in key_values if v in str(output))
                    ratio = found / len(key_values) if key_values else 0
                    if ratio >= 0.8:
                        passed = True
                    elif ratio >= 0.5:
                        partial = True
            elif isinstance(task.expected, dict):
                try:
                    parsed = json.loads(output) if isinstance(output, str) else output
                    if parsed == task.expected:
                        passed = True
                except (json.JSONDecodeError, TypeError):
                    pass
                if not passed:
                    key_values = set(str(v) for v in task.expected.values())
                    found = sum(1 for v in key_values if v in str(output))
                    ratio = found / len(key_values) if key_values else 0
                    passed = ratio >= 0.8
        else:
            # No verifier and no expected output — task is unverified, mark failed
            passed = False

        # Track tool creation
        tools_created_names = []
        for tc in agent_result.get("tools_created", []):
            tool_record = ToolRecord(
                name=tc["name"],
                implementation=tc.get("implementation", ""),
                test_suite=tc.get("test_suite", ""),
                created_at_task=task.id,
                capability_id=task.capability_id,
                source_task_id=task.id,
            )
            result.tools_created.append(tool_record)
            tools_created_names.append(tc["name"])

        # Detect reuse
        tools_used = agent_result.get("tools_used", [])
        tool_reused = False
        if task.task_type in (TaskType.VARIANT, TaskType.REGRESS):
            # Check if any tool used was from before (not newly created)
            tool_reused = any(t in tools_before for t in tools_used if t not in tools_created_names)

        task_result = TaskResult(
            task_id=task.id,
            task_type=task.task_type,
            passed=passed,
            partial=partial,
            tool_created=tools_created_names[0] if tools_created_names else None,
            tools_used=tools_used,
            tool_reused=tool_reused,
            tool_reused_correctly=tool_reused and passed,
            llm_calls=agent_result.get("llm_calls", 1),
            duration_ms=duration,
            agent_output=str(output)[:500],
        )
        result.task_results.append(task_result)

        # Update tool tracking
        tools_before.update(tools_created_names)

        if verbose:
            status = "PASS" if passed else ("PARTIAL" if partial else "FAIL")
            reuse_tag = " [REUSED]" if tool_reused else ""
            create_tag = f" [CREATED: {', '.join(tools_created_names)}]" if tools_created_names else ""
            print(f"             {'✓' if passed else '✗'} {status}{create_tag}{reuse_tag}")

    if verbose:
        print(f"\n=== Results ===")
        summary = result.summary()
        for key, value in summary.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.3f}")
            elif isinstance(value, dict):
                print(f"  {key}:")
                for k, v in value.items():
                    print(f"    {k}: {v:.3f}" if isinstance(v, float) else f"    {k}: {v}")
            else:
                print(f"  {key}: {value}")

    return result


# Import TaskType for use in runner
from ..types import TaskType
