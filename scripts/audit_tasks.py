#!/usr/bin/env python3
"""Audit all benchmark tasks for deterministic verification coverage.

Prints a per-session report and summary table. Exit code 0 if all tasks
have either `expected` or `verify`; exit code 1 otherwise.

Optional checks (via CLI flags):
  --check-capabilities  Every non-seed task must have a non-empty capability_id.
  --check-hidden-tests  Every GAP task must have non-empty hidden_tests.
"""
from __future__ import annotations

import argparse
import importlib
import pathlib
import sys

from evolvetool_bench.types import TaskType

REPO_ROOT = pathlib.Path(__file__).parent.parent
SRC = REPO_ROOT / "src"
sys.path.insert(0, str(SRC))

DOMAIN_SESSIONS = [
    ("data_transform", [1, 2, 3, 4, 5]),
    ("numerical", [1, 2, 3]),
    ("api_orchestration", [1]),
]


def load_session(domain: str, session_num: int):
    """Import session module and return the Session object, or None."""
    mod_path = f"evolvetool_bench.domains.{domain}.session_{session_num}"
    try:
        mod = importlib.import_module(mod_path)
    except ImportError as e:
        print(f"  IMPORT ERROR: {mod_path}: {e}")
        return None

    session_obj = None
    for attr in ["SESSION", "session", f"session_{session_num}"]:
        if hasattr(mod, attr):
            session_obj = getattr(mod, attr)
            break

    if session_obj is None and hasattr(mod, "create_session"):
        session_obj = mod.create_session()

    if session_obj is None:
        print(f"  WARN: no SESSION in {mod_path}")
    return session_obj


def audit_session(domain: str, session_num: int) -> tuple[int, int, int]:
    """Returns (total_tasks, has_verifier, unverified)."""
    session_obj = load_session(domain, session_num)
    if session_obj is None:
        return 0, 0, 0

    tasks = session_obj.tasks
    verified = sum(1 for t in tasks if t.expected is not None or t.verify is not None)
    unverified = len(tasks) - verified
    return len(tasks), verified, unverified


def check_capabilities() -> int:
    """Assert every non-seed task has a non-empty capability_id."""
    all_ok = True
    print("=" * 60)
    print("Capability ID check (non-seed tasks)")
    print("-" * 60)

    for domain, sessions in DOMAIN_SESSIONS:
        for s in sessions:
            label = f"{domain}/session_{s}"
            session_obj = load_session(domain, s)
            if session_obj is None:
                all_ok = False
                continue

            missing = [
                t.id
                for t in session_obj.tasks
                if t.task_type != TaskType.SEED and not (t.capability_id and t.capability_id.strip())
            ]
            if missing:
                all_ok = False
                print(f"  {label}: MISSING capability_id on {', '.join(missing)}")
            else:
                non_seed = sum(1 for t in session_obj.tasks if t.task_type != TaskType.SEED)
                print(f"  {label}: OK ({non_seed} non-seed tasks)")

    print("=" * 60)
    if all_ok:
        print("✓ all non-seed tasks have capability_id")
        return 0
    print("✗ some non-seed tasks lack capability_id")
    return 1


def check_hidden_tests() -> int:
    """Assert every GAP task has non-empty hidden_tests; print per-domain stats."""
    all_ok = True
    print("=" * 60)
    print("Hidden tests check (GAP tasks)")
    print("-" * 60)

    domain_stats: dict[str, dict[str, int]] = {}

    for domain, sessions in DOMAIN_SESSIONS:
        gaps = 0
        hidden = 0
        adversarial = 0
        missing_gaps: list[str] = []

        for s in sessions:
            session_obj = load_session(domain, s)
            if session_obj is None:
                all_ok = False
                continue

            for t in session_obj.tasks:
                if t.task_type == TaskType.GAP:
                    gaps += 1
                    hidden += len(t.hidden_tests)
                    adversarial += len(t.adversarial_tests)
                    if not t.hidden_tests:
                        missing_gaps.append(f"{domain}/session_{s}:{t.id}")
                        all_ok = False

        domain_stats[domain] = {
            "gaps": gaps,
            "hidden": hidden,
            "adversarial": adversarial,
        }
        ratio = hidden / gaps if gaps else 0.0
        print(
            f"  {domain}: gaps={gaps}, hidden_tests={hidden}, "
            f"adversarial_tests={adversarial}, hidden/gap={ratio:.1f}"
        )
        if missing_gaps:
            print(f"    MISSING hidden_tests: {', '.join(missing_gaps)}")

    print("=" * 60)
    if all_ok:
        print("✓ all GAP tasks have hidden_tests")
        return 0
    print("✗ some GAP tasks lack hidden_tests")
    return 1


def strict_report() -> int:
    """Report strict-TC coverage under the fail-closed regime.

    The runner marks any task lacking ``expected``/``verify`` as FAIL (never as a
    lenient pass), so the number of tasks eligible for a *pass* equals the number
    with deterministic verifiers. We print that explicitly. Exit code is always 0
    here: strict mode is a coverage report, not a gate (unverified tasks are
    excluded from strict TC by construction, not silently passed).
    """
    total = verified = 0
    for domain, sessions in DOMAIN_SESSIONS:
        for s in sessions:
            n, v, _u = audit_session(domain, s)
            total += n
            verified += v
    print("=" * 60)
    print("Strict task-completion coverage (fail-closed regime)")
    print("-" * 60)
    print(f"  Task verification coverage: {verified}/{total}")
    print(f"  Tasks included in strict TC: {verified}")
    print(f"  Unverified tasks included in TC: 0")
    if verified < total:
        print(f"  NOTE: {total - verified} unverified tasks are excluded from strict TC")
        print("        and reported as preliminary until deterministic verifiers are added.")
    print("=" * 60)
    return 0


def audit_verification() -> int:
    """Default verifier-coverage report."""
    total_tasks = 0
    total_verified = 0
    total_unverified = 0
    all_ok = True

    print("=" * 60)
    print(f"{'Session':<40} {'Total':>6} {'Verified':>9} {'Unverified':>11}")
    print("-" * 60)

    for domain, sessions in DOMAIN_SESSIONS:
        for s in sessions:
            label = f"{domain}/session_{s}"
            n, v, u = audit_session(domain, s)
            total_tasks += n
            total_verified += v
            total_unverified += u
            if u > 0:
                all_ok = False
            status = "OK" if u == 0 else f"WARN: {u} unverified"
            print(f"  {label:<38} {n:>6} {v:>9} {u:>11}  {status}")

    print("=" * 60)
    print(f"  {'TOTAL':<38} {total_tasks:>6} {total_verified:>9} {total_unverified:>11}")
    print()

    if all_ok:
        print(f"✓ {total_tasks}/{total_tasks} benchmark tasks deterministically verified")
        return 0
    else:
        print(f"✗ {total_unverified}/{total_tasks} tasks lack deterministic verification")
        print("  Tasks without expected or verify will be marked FAIL by the runner.")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit benchmark task definitions.")
    parser.add_argument(
        "--check-capabilities",
        action="store_true",
        help="Verify every non-seed task has a non-empty capability_id.",
    )
    parser.add_argument(
        "--check-hidden-tests",
        action="store_true",
        help="Verify every GAP task has non-empty hidden_tests.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Report strict-TC coverage under the fail-closed regime.",
    )
    args = parser.parse_args()

    exit_code = 0

    if args.check_capabilities:
        exit_code |= check_capabilities()
        print()

    if args.check_hidden_tests:
        exit_code |= check_hidden_tests()
        print()

    if args.strict:
        exit_code |= strict_report()
        print()

    if not (args.check_capabilities or args.check_hidden_tests or args.strict):
        exit_code = audit_verification()

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
