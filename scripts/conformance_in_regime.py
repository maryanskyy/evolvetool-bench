#!/usr/bin/env python3
"""In-regime conformance replay for the strict-pilot harness.

After `run_strict.py --preserve-tools` (now default) has dumped per-tool source
to `<output>/tools/<system>/<session>/seed_<seed>/<name>.py`, this script walks
that tree and re-evaluates each preserved tool against the held-out conformance
suite (hidden + adversarial tests) tied to the capability the tool was
synthesised for. It emits a per-tool conformance record and an aggregate.

Outputs (written under --canonical):
  - tools/<system>/<session>/seed_<seed>/<name>.meta_conformance.json  (per tool)
  - conformance_manifest.jsonl                                          (one row/tool)
  - conformance_aggregate.json                                          (per-system)

Usage:
    python scripts/conformance_in_regime.py --canonical results_canonical/

Re-runnable, idempotent, no LLM calls — just executes the preserved tool
sources against the session's hidden/adversarial test inputs.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from evolvetool_bench.types import ToolRecord  # noqa: E402
from evolvetool_bench.evaluation.tool_quality import evaluate_tool  # noqa: E402

from evolvetool_bench.domains.data_transform import (  # noqa: E402
    session_1 as dt_s1, session_2 as dt_s2, session_3 as dt_s3,
    session_4 as dt_s4, session_5 as dt_s5,
)
from evolvetool_bench.domains.numerical import (  # noqa: E402
    session_1 as num_s1, session_2 as num_s2, session_3 as num_s3,
)

SESSION_FACTORIES = [
    dt_s1.create_session, dt_s2.create_session, dt_s3.create_session,
    dt_s4.create_session, dt_s5.create_session,
    num_s1.create_session, num_s2.create_session, num_s3.create_session,
]
SESSIONS_BY_ID = {f().id: f() for f in SESSION_FACTORIES}


def _resolve_capability_tasks(session, task):
    """Return the task(s) that define the capability a tool implements.

    Capability tests live on the gap task that introduces a capability. We
    follow reuses_task / breaks_task / composes_tasks linkages so each tool is
    scored only against the tests for its own capability.
    """
    if task is None:
        return []
    if task.hidden_tests or task.adversarial_tests:
        return [task]
    by_id = {t.id: t for t in session.tasks}
    refs = []
    if getattr(task, "reuses_task", None):
        refs.append(task.reuses_task)
    if getattr(task, "breaks_task", None):
        refs.append(task.breaks_task)
    if getattr(task, "composes_tasks", None):
        refs.extend(task.composes_tasks)
    resolved, seen = [], set()
    for ref in refs:
        cap = by_id.get(ref)
        if cap is not None and cap.id not in seen and (cap.hidden_tests or cap.adversarial_tests):
            resolved.append(cap)
            seen.add(cap.id)
    return resolved


def _tests_for_tool(session_id: str, created_at_task: str):
    s = SESSIONS_BY_ID.get(session_id)
    if not s or not created_at_task:
        return [], []
    task = next((t for t in s.tasks if t.id == created_at_task), None)
    if task is None:
        return [], []
    hidden, adversarial = [], []
    for cap in _resolve_capability_tasks(s, task):
        hidden.extend(cap.hidden_tests or [])
        adversarial.extend(cap.adversarial_tests or [])
    return hidden, adversarial


def reeval_one(meta_path: Path) -> dict | None:
    with open(meta_path) as f:
        meta = json.load(f)
    source_path = meta_path.with_suffix("").with_suffix(".py")
    if not source_path.exists():
        return None
    source = source_path.read_text()

    session_id = meta.get("session_id")
    created_at_task = meta.get("created_at_task") or ""
    hidden, adversarial = _tests_for_tool(session_id, created_at_task)

    out = {
        "name": meta["name"],
        "system": meta.get("system"),
        "session_id": session_id,
        "seed": meta.get("seed"),
        "model": meta.get("model"),
        "created_at_task": created_at_task,
        "scores_in_session": meta.get("scores_in_session", {}),
        "n_hidden": len(hidden),
        "n_adversarial": len(adversarial),
    }
    if not hidden and not adversarial:
        out["conformance"] = None
        out["note"] = "no_capability_tests_resolved"
    else:
        tool = ToolRecord(
            name=meta["name"],
            implementation=source,
            test_suite="",
            created_at_task=created_at_task,
            source_task_id=created_at_task,
            version=meta.get("version", 1),
        )
        evaluate_tool(tool, hidden_tests=hidden, adversarial_tests=adversarial)
        out["conformance"] = {
            "tqs": tool.quality_score,
            "correctness": tool.correctness,
            "robustness": tool.robustness,
            "generality": tool.generality,
            "code_quality": tool.code_quality,
        }

    out_path = meta_path.with_name(meta_path.name.replace(".meta.json", ".meta_conformance.json"))
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    return out


def walk_strict_tools(canonical_dir: Path) -> list[Path]:
    """Return every <name>.meta.json under tools/<system>/<session>/seed_<n>/."""
    pattern = str(canonical_dir / "tools" / "*" / "*" / "*" / "*.meta.json")
    paths = []
    for p in sorted(glob.glob(pattern)):
        if "meta_conformance" in p or "meta_v3" in p:
            continue
        paths.append(Path(p))
    return paths


def main():
    parser = argparse.ArgumentParser(description="In-regime conformance replay against preserved strict-pilot tools")
    parser.add_argument("--canonical", default="results_canonical/",
                        help="Strict-pilot output directory (default: results_canonical/)")
    args = parser.parse_args()

    canonical = Path(args.canonical)
    metas = walk_strict_tools(canonical)
    if not metas:
        print(f"No preserved tools found under {canonical}/tools/. "
              "Did you run scripts/run_strict.py with the source-preservation patch?")
        return

    print(f"Replaying conformance for {len(metas)} preserved tools...")
    manifest_path = canonical / "conformance_manifest.jsonl"
    aggregate: dict[str, dict] = defaultdict(lambda: {
        "n_tools": 0, "n_scored": 0,
        "sum_correctness": 0.0, "sum_robustness": 0.0, "sum_generality": 0.0,
        "n_zero_correctness": 0,
    })

    with open(manifest_path, "w") as out:
        for meta_path in metas:
            try:
                rec = reeval_one(meta_path)
                if rec is None:
                    continue
                out.write(json.dumps(rec) + "\n")
                out.flush()
                sys_name = rec.get("system") or "unknown"
                a = aggregate[sys_name]
                a["n_tools"] += 1
                if rec.get("conformance"):
                    c = rec["conformance"]
                    a["n_scored"] += 1
                    a["sum_correctness"] += c.get("correctness", 0.0) or 0.0
                    a["sum_robustness"] += c.get("robustness", 0.0) or 0.0
                    a["sum_generality"] += c.get("generality", 0.0) or 0.0
                    if (c.get("correctness") or 0.0) == 0.0:
                        a["n_zero_correctness"] += 1
            except Exception as e:
                print(f"  [error] {meta_path}: {e}")

    summary = {}
    for sys_name, a in aggregate.items():
        n = a["n_scored"] or 1
        summary[sys_name] = {
            "n_tools_preserved": a["n_tools"],
            "n_tools_with_capability_tests": a["n_scored"],
            "mean_held_out_correctness": round(a["sum_correctness"] / n, 4),
            "mean_held_out_robustness": round(a["sum_robustness"] / n, 4),
            "mean_held_out_generality": round(a["sum_generality"] / n, 4),
            "n_tools_with_zero_correctness": a["n_zero_correctness"],
            "pct_silent_rot": round(100 * a["n_zero_correctness"] / n, 1),
        }

    agg_path = canonical / "conformance_aggregate.json"
    with open(agg_path, "w") as f:
        json.dump(summary, f, indent=2)

    print("\nDone. Conformance signals per system:")
    print(f"  {'system':<18} {'tools':>6} {'scored':>7} {'mean C':>8} {'silent-rot %':>14}")
    print("  " + "-" * 60)
    for sys_name, s in sorted(summary.items()):
        print(f"  {sys_name:<18} {s['n_tools_preserved']:>6} {s['n_tools_with_capability_tests']:>7} "
              f"{s['mean_held_out_correctness']:>8.3f} {s['pct_silent_rot']:>13.1f}%")
    print(f"\nManifest: {manifest_path}\nAggregate: {agg_path}")


if __name__ == "__main__":
    main()
