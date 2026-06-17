"""Safe tool execution with timeout.

Prevents synthesised tools from hanging the experiment due to infinite loops,
network calls, or heavy computation.
"""
from __future__ import annotations

import concurrent.futures
import threading
from typing import Any, Callable

_TOOL_TIMEOUT_S = 5.0  # max seconds per tool call


def call_with_timeout(
    fn: Callable, args: dict[str, Any], timeout: float = _TOOL_TIMEOUT_S
) -> str:
    """Call fn(**args) with a timeout. Returns the result as str or an error message."""
    result_holder: list[Any] = [None]
    exc_holder: list[Any] = [None]

    def _target():
        try:
            result_holder[0] = str(fn(**args))
        except Exception as e:
            exc_holder[0] = e

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        return f"Error: tool execution timed out after {timeout}s"
    if exc_holder[0] is not None:
        return f"Error: {exc_holder[0]}"
    return result_holder[0] or ""
