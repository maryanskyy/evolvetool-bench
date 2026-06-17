"""Re-evaluate all preserved tools against the EXPANDED v3 hidden+adversarial
test suites. Writes v3 score files alongside the original meta.json.

Output: for each preserved tool at
  results_full/<config>/tools/<session>/<name>.py
we write
  results_full/<config>/tools/<session>/<name>.meta_v3.json
with the new C/R/G/Q/TQS values under the expanded suite, plus old vs new diff.

Also produces a config-level summary at
  results_full/<config>/aggregate_v3.json
with mean per-dim scores under both v1 and v3 tests for sensitivity analysis.
"""

from __future__ import annotations

import json
import os
import glob
import sys
from collections import defaultdict

sys.path.insert(0, "src")

from evolvetool_bench.types import ToolRecord
from evolvetool_bench.evaluation.tool_quality import evaluate_tool

from evolvetool_bench.domains.data_transform.session_1 import create_session as dt1
from evolvetool_bench.domains.data_transform.session_2 import create_session as dt2
from evolvetool_bench.domains.data_transform.session_3 import create_session as dt3
from evolvetool_bench.domains.data_transform.session_4 import create_session as dt4
from evolvetool_bench.domains.data_transform.session_5 import create_session as dt5
from evolvetool_bench.domains.api_orchestration.session_1 import create_session as api1
from evolvetool_bench.domains.numerical.session_1 import create_session as num1
from evolvetool_bench.domains.numerical.session_2 import create_session as num2
from evolvetool_bench.domains.numerical.session_3 import create_session as num3


# Map session_id -> Session object, used to look up hidden+adversarial tests
SESSION_FACTORIES = [dt1, dt2, dt3, dt4, dt5, api1, num1, num2, num3]
SESSIONS_BY_ID: dict[str, "Session"] = {}
for factory in SESSION_FACTORIES:
    s = factory()
    SESSIONS_BY_ID[s.id] = s


def _resolve_capability_tasks(session, task) -> list:
    """Return the task(s) that DEFINE the capability a tool implements.

    Capability tests live on the gap task that introduces a capability. A tool
    may be created at a gap task (its own tests apply), or at a variant/regress
    task (``reuses_task``), an adversarial task (``breaks_task``), or a compose
    task (``composes_tasks``). We follow those linkages to the task(s) carrying
    the hidden/adversarial tests so each tool is scored ONLY against the tests
    for its own capability -- not the union of every gap task in the session.
    """
    if task is None:
        return []
    # A task that carries its own tests defines a capability directly.
    if task.hidden_tests or task.adversarial_tests:
        return [task]
    by_id = {t.id: t for t in session.tasks}
    refs: list[str] = []
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


def _tests_for_tool(session_id: str, created_at_task: str) -> tuple[list[dict], list[dict]]:
    """Return (hidden, adversarial) tests for the SPECIFIC capability of one tool.

    Replaces the previous behaviour of pooling every gap task's tests and
    applying them to every preserved tool, which incorrectly scored a tool for
    capability A against the hidden tests for capability B.
    """
    s = SESSIONS_BY_ID.get(session_id)
    if not s:
        return [], []
    # ``created_at_task`` is stored as the task id (e.g. "gap_1", "adversarial_2").
    task = next((t for t in s.tasks if t.id == created_at_task), None)
    if task is None:
        return [], []
    hidden, adversarial = [], []
    for cap in _resolve_capability_tasks(s, task):
        hidden.extend(cap.hidden_tests or [])
        adversarial.extend(cap.adversarial_tests or [])
    return hidden, adversarial


def reeval_tool(meta_path: str) -> dict | None:
    """Re-evaluate a single preserved tool with the expanded session tests."""
    with open(meta_path) as f:
        meta = json.load(f)
    source_path = meta_path.replace(".meta.json", ".py")
    if not os.path.exists(source_path):
        return None
    source = open(source_path).read()
    session_id = os.path.basename(os.path.dirname(meta_path))

    # Build a ToolRecord and evaluate it ONLY against the tests for its own
    # capability (resolved from created_at_task via the session linkages).
    created_at_task = meta.get("created_at_task", "")
    hidden, adversarial = _tests_for_tool(session_id, created_at_task)
    if not hidden and not adversarial:
        return None

    tool = ToolRecord(
        name=meta["name"],
        implementation=source,
        test_suite="",
        created_at_task=created_at_task,
        source_task_id=created_at_task,
        version=meta.get("version", 1),
    )
    evaluate_tool(tool, hidden_tests=hidden, adversarial_tests=adversarial)

    new_scores = {
        "tqs": tool.quality_score,
        "correctness": tool.correctness,
        "robustness": tool.robustness,
        "generality": tool.generality,
        "code_quality": tool.code_quality,
    }
    out_meta = {
        "name": meta["name"],
        "created_at_task": meta.get("created_at_task", ""),
        "session_id": session_id,
        "scores_v1": meta["scores"],
        "scores_v3": new_scores,
        "n_hidden_v3": len(hidden),
        "n_adversarial_v3": len(adversarial),
    }
    out_path = meta_path.replace(".meta.json", ".meta_v3.json")
    with open(out_path, "w") as f:
        json.dump(out_meta, f, indent=2)
    return out_meta


def reeval_config(config_dir: str) -> dict | None:
    tools_root = os.path.join(config_dir, "tools")
    if not os.path.isdir(tools_root):
        return None
    print(f"\n=== {config_dir} ===")

    results = []
    for meta_path in sorted(glob.glob(os.path.join(tools_root, "*", "*.meta.json"))):
        # Skip the meta_v3 files we already wrote
        if "meta_v3" in meta_path:
            continue
        try:
            r = reeval_tool(meta_path)
            if r:
                results.append(r)
                v1, v3 = r["scores_v1"], r["scores_v3"]
                print(f"  {r['name'][:30]:30s} "
                      f"C: {v1['correctness']:.2f}->{v3['correctness']:.2f}  "
                      f"R: {v1['robustness']:.2f}->{v3['robustness']:.2f}  "
                      f"G: {v1['generality']:.2f}->{v3['generality']:.2f}  "
                      f"TQS: {v1['tqs']:.2f}->{v3['tqs']:.2f}")
        except Exception as e:
            print(f"  ERROR on {meta_path}: {e}")

    if not results:
        return None

    def _mean(key: str, version: str = "scores_v3") -> float:
        return sum(r[version][key] for r in results) / len(results)

    summary = {
        "config": os.path.basename(config_dir),
        "n_tools": len(results),
        "v1": {k: _mean(k, "scores_v1") for k in
                ["correctness", "robustness", "generality", "code_quality", "tqs"]},
        "v3": {k: _mean(k, "scores_v3") for k in
                ["correctness", "robustness", "generality", "code_quality", "tqs"]},
    }
    out_path = os.path.join(config_dir, "aggregate_v3.json")
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    return summary


def main() -> None:
    summaries = []
    for d in sorted(os.listdir("results_full")):
        config_dir = os.path.join("results_full", d)
        s = reeval_config(config_dir)
        if s:
            summaries.append(s)

    print("\n" + "=" * 80)
    print(f"{'config':30s} {'n':>3s}  v1 TQS  v3 TQS   ΔTQS   v1 C   v3 C    ΔC")
    print("=" * 80)
    for s in summaries:
        d_tqs = s["v3"]["tqs"] - s["v1"]["tqs"]
        d_c = s["v3"]["correctness"] - s["v1"]["correctness"]
        print(f"{s['config']:30s} {s['n_tools']:>3d}  "
              f"{s['v1']['tqs']:.3f}   {s['v3']['tqs']:.3f}   "
              f"{d_tqs:+.3f}   {s['v1']['correctness']:.2f}   "
              f"{s['v3']['correctness']:.2f}   {d_c:+.2f}")


if __name__ == "__main__":
    main()
