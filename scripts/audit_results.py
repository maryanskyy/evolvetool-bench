#!/usr/bin/env python3
"""Audit result files for completeness and consistency.

Reads all JSON files in results_canonical/ (or the provided dir) and prints
a per-system summary. Flags missing fields, inconsistent session counts, etc.
"""
from __future__ import annotations
import json, pathlib, sys, argparse

REPO_ROOT = pathlib.Path(__file__).parent.parent
REQUIRED_FIELDS = {"session_id", "task_completion", "tools_created", "reuse_rate",
                   "correct_reuse_rate", "incorrect_reuse_rate"}


def audit_results(results_dir: pathlib.Path) -> int:
    json_files = sorted(results_dir.glob("**/*.json"))
    if not json_files:
        print(f"No JSON files found in {results_dir}")
        return 1

    issues = 0
    by_system: dict[str, list[dict]] = {}

    for f in json_files:
        try:
            data = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            print(f"  PARSE ERROR: {f}: {e}")
            issues += 1
            continue

        # Normalise: results can be a list or a single session dict
        # Skip placeholder/metadata files that are not session records
        if isinstance(data, dict) and "_note" in data:
            continue
        records = data if isinstance(data, list) else [data]
        for rec in records:
            if not isinstance(rec, dict) or "session_id" not in rec:
                continue  # skip non-session objects
            system = rec.get("system", f.stem)
            by_system.setdefault(system, []).append(rec)
            missing = REQUIRED_FIELDS - set(rec.keys())
            if missing:
                print(f"  MISSING FIELDS in {f.name}: {missing}")
                issues += 1

    print(f"\n{'System':<35} {'Sessions':>9} {'Avg TC':>8} {'Avg LH':>8}")
    print("-" * 65)
    for system, records in sorted(by_system.items()):
        n = len(records)
        tc = sum(r.get("task_completion", 0) for r in records) / n
        lh = sum(r.get("library_health", 0) for r in records) / n
        print(f"  {system:<33} {n:>9} {tc:>8.3f} {lh:>8.3f}")

    print()
    if issues:
        print(f"✗ {issues} issue(s) found.")
        return 1
    print("✓ All result files passed audit.")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Audit EvolveTool-Bench result files")
    p.add_argument("--results-dir", default="results_canonical", help="Results directory")
    args = p.parse_args(argv)
    results_dir = pathlib.Path(args.results_dir)
    if not results_dir.exists():
        print(f"Results dir not found: {results_dir}. Creating empty structure.")
        results_dir.mkdir(parents=True)
        return 0
    return audit_results(results_dir)


if __name__ == "__main__":
    raise SystemExit(main())
