"""Tool Quality Evaluator — scores each synthesized tool on 4 axes."""

from __future__ import annotations

import ast
import re
import subprocess
import sys
import textwrap
from typing import Any

from ..types import ToolRecord


def evaluate_tool(tool: ToolRecord, hidden_tests: list[dict], adversarial_tests: list[dict]) -> ToolRecord:
    """Evaluate a tool on correctness, robustness, generality, and code quality.

    Mutates and returns the tool with quality scores filled in.
    """
    tool.correctness = _eval_correctness(tool, hidden_tests)
    tool.robustness = _eval_robustness(tool, adversarial_tests)
    tool.generality = _eval_generality(tool, hidden_tests)
    tool.code_quality = _eval_code_quality(tool)
    return tool


def _run_tool(implementation: str, fn_name: str, kwargs: dict, timeout: int = 10) -> tuple[Any, str | None]:
    """Run a tool in a subprocess and return (result, error)."""
    code = textwrap.dedent(f"""
import json, sys
{implementation}

try:
    result = {fn_name}(**{repr(kwargs)})
    print(json.dumps({{"result": result, "error": None}}))
except Exception as e:
    print(json.dumps({{"result": None, "error": str(e)}}))
""")
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=timeout,
        )
        if proc.returncode != 0:
            return None, proc.stderr[:500]
        import json
        data = json.loads(proc.stdout.strip().split("\n")[-1])
        return data["result"], data["error"]
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except Exception as e:
        return None, str(e)


def _get_fn_name(implementation: str) -> str:
    """Extract the first function name from implementation."""
    match = re.search(r'def (\w+)\s*\(', implementation)
    return match.group(1) if match else "unknown"


def _eval_correctness(tool: ToolRecord, hidden_tests: list[dict]) -> float:
    """Run hidden unit tests — proportion that pass."""
    if not hidden_tests:
        return float("nan")  # not_applicable — no tests provided
    fn_name = _get_fn_name(tool.implementation)
    passed = 0
    for test in hidden_tests:
        result, error = _run_tool(tool.implementation, fn_name, test["input"])
        if error is None and test.get("verify"):
            # verify is a string expression: "result == 42"
            try:
                if eval(test["verify"], {"result": result}):
                    passed += 1
            except Exception:
                pass
        elif error is None and "expected" in test:
            if result == test["expected"]:
                passed += 1
    return passed / len(hidden_tests)


def _eval_robustness(tool: ToolRecord, adversarial_tests: list[dict]) -> float:
    """Run adversarial edge cases — proportion that don't crash."""
    if not adversarial_tests:
        return float("nan")  # not_applicable — no tests provided
    fn_name = _get_fn_name(tool.implementation)
    survived = 0
    for test in adversarial_tests:
        result, error = _run_tool(tool.implementation, fn_name, test["input"])
        # Robustness = tool handles gracefully (no crash, returns error dict or raises cleanly)
        if error is None:
            survived += 1
        elif "timeout" not in (error or ""):
            # Raised an exception but didn't crash/hang — partial credit
            survived += 0.5
    return survived / len(adversarial_tests)


def _eval_generality(tool: ToolRecord, hidden_tests: list[dict]) -> float:
    """Run held-out inputs from same distribution — tests parameterization."""
    # Uses the same hidden tests but checks if tool handles varied inputs
    # (vs correctness which checks exact outputs)
    if not hidden_tests:
        return float("nan")  # not_applicable — no tests provided
    fn_name = _get_fn_name(tool.implementation)
    worked = 0
    for test in hidden_tests:
        result, error = _run_tool(tool.implementation, fn_name, test["input"])
        if error is None and result is not None:
            worked += 1
    return worked / len(hidden_tests)


def _eval_code_quality(tool: ToolRecord) -> float:
    """Automated code quality checks (surface + semantic).

    This metric was previously ``surface-only'' (docstring, type hints, length, etc.)
    and saturated at 0.88--0.94 across systems, failing to discriminate. The v2 version
    keeps the original six surface checks but adds three semantic checks based on
    radon's static analysis: cyclomatic complexity, maintainability index, and
    presence of meaningful control flow.
    """
    score = 0.0
    checks = 0
    code = tool.implementation

    # ── Surface checks (kept for backward comparison) ──────────────

    # Has docstring
    checks += 1
    if '"""' in code or "'''" in code:
        score += 1

    # Has type hints in function signature
    checks += 1
    first_line = code.split("\n")[0] if code else ""
    if "->" in first_line and ":" in first_line:
        score += 1

    # Handles exceptions
    checks += 1
    if "try:" in code and "except" in code:
        score += 1

    # No hardcoded values (magic numbers > 2 digits outside of known constants)
    checks += 1
    magic_numbers = re.findall(r'(?<!=)\b\d{3,}\b', code)
    suspicious = [n for n in magic_numbers if int(n) not in {100, 200, 404, 500, 1000}]
    if len(suspicious) <= 2:
        score += 1

    # Reasonable length (< 100 lines)
    checks += 1
    if len(code.split("\n")) < 100:
        score += 1

    # Valid Python (parses without errors)
    checks += 1
    try:
        ast.parse(code)
        score += 1
    except SyntaxError:
        pass

    # ── Semantic checks (added in v2 to address reviewer L7 saturation concern) ──

    # Cyclomatic complexity sits in a sensible band: ≥ 2 (some branching present;
    # complexity 1 = straight-line code) and ≤ 20 (not pathologically complex).
    # Penalises both extremes.
    checks += 1
    complexities = _radon_complexities(code)
    if complexities:
        peak = max(complexities)
        if 2 <= peak <= 20:
            score += 1
        # else: complexity 1 = identity-like, complexity >20 = unmaintainable

    # Maintainability Index ≥ 20 (radon's threshold for "moderate" maintainability)
    checks += 1
    mi = _radon_mi(code)
    if mi is not None and mi >= 20:
        score += 1

    # Non-trivial control flow: at least one branching or looping node (if/for/while/try).
    # Catches degenerate "return None" or "return arg" stubs that satisfy other checks.
    checks += 1
    if _has_meaningful_control_flow(code):
        score += 1

    return score / checks if checks > 0 else 0.0


def _radon_complexities(code: str) -> list[int]:
    """Return cyclomatic complexity for each function in code, or [] on failure."""
    try:
        from radon.complexity import cc_visit
        return [c.complexity for c in cc_visit(code)]
    except Exception:
        return []


def _radon_mi(code: str) -> float | None:
    """Return radon maintainability index, or None on failure."""
    try:
        from radon.metrics import mi_visit
        return mi_visit(code, True)
    except Exception:
        return None


def _has_meaningful_control_flow(code: str) -> bool:
    """True if the function has at least one real branch or loop.

    Counts: if/for/while/comprehensions/BoolOp. Does NOT count: try/except alone
    (a wrapper isn't 'meaningful logic') or With statements (context managers).
    A `return constant` / `return arg` / `return f(arg)` / `try: return arg except: ...`
    stub has zero of these nodes and should not earn semantic credit.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.ListComp,
                              ast.DictComp, ast.SetComp, ast.GeneratorExp, ast.BoolOp)):
            return True
    return False


def detect_redundancy(tools: list[ToolRecord], test_inputs: list[dict]) -> float:
    """Detect functionally duplicate tools by comparing outputs on shared inputs.

    Returns redundancy rate (0.0 = no duplicates, 1.0 = all duplicates).
    """
    if len(tools) <= 1 or not test_inputs:
        return 0.0

    # Run each tool on each test input
    outputs: dict[str, list[Any]] = {}
    for tool in tools:
        fn_name = _get_fn_name(tool.implementation)
        results = []
        for test in test_inputs[:5]:  # limit to 5 for performance
            result, _ = _run_tool(tool.implementation, fn_name, test["input"])
            results.append(result)
        outputs[tool.name] = results

    # Count pairs with identical outputs
    names = list(outputs.keys())
    duplicates = 0
    pairs = 0
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            pairs += 1
            if outputs[names[i]] == outputs[names[j]]:
                duplicates += 1

    return duplicates / pairs if pairs > 0 else 0.0
