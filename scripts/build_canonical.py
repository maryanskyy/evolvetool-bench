#!/usr/bin/env python3
"""Build canonical result manifests from the preserved per-seed runs.

Ingests ``results_full/`` (one directory per system-model-seed run, each with
nine ``s*.json`` session summaries, an ``aggregate.json``, and a ``tools/``
tree of preserved tool source + meta) and emits the canonical artifacts the
paper's auditability story depends on:

  results_canonical/run_manifest.jsonl   one row per *session run*
  results_canonical/tool_manifest.jsonl  one row per *preserved tool*
  results_canonical/aggregate.json       per-(system, model) means used in tables

ETS is recomputed under the safety-free composite directly from components
(ETS = 0.30*TC + 0.20*TQS + 0.10*max(0, 1-RC) + 0.40*LH, RC = LLM calls /
(tasks*10)), so the manifests are self-consistent with the paper without
relying on the older stored ``evolvetool_score``.

NOTE ON GRANULARITY: the original runs persisted session-level summaries, not
per-task traces, so ``run_manifest`` rows are session-level (with per-type
completion). Per-task trace logging is a planned harness enhancement; the
schema here documents what is actually reproducible from disk today.

Usage:
    python scripts/build_canonical.py --source results_full --output results_canonical
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import importlib
import json
import os
import pathlib
import statistics as st
import sys
from collections import defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

DOMAIN_SESSIONS = [
    ("data_transform", [1, 2, 3, 4, 5]),
    ("numerical", [1, 2, 3]),
    ("api_orchestration", [1]),
]

TASKS_PER_SESSION = 11
W_TC, W_TQS, W_RC, W_LH = 0.30, 0.20, 0.10, 0.40


def safety_free_ets(tc: float, tqs: float, llm_calls: float, lh: float,
                    n_tasks: int = TASKS_PER_SESSION) -> float:
    rc = llm_calls / max(n_tasks * 10, 1)
    return W_TC * tc + W_TQS * tqs + W_RC * max(0.0, 1 - rc) + W_LH * lh


def _seed_from_dirname(d: str) -> int:
    for part in d.split("_"):
        if part.startswith("seed") and part[4:].isdigit():
            return int(part[4:])
    return 0


def build(source: str, output: str) -> dict:
    os.makedirs(output, exist_ok=True)
    run_rows: list[dict] = []
    tool_rows: list[dict] = []

    for d in sorted(os.listdir(source)):
        run_dir = os.path.join(source, d)
        agg_path = os.path.join(run_dir, "aggregate.json")
        if not os.path.isfile(agg_path):
            continue
        meta = json.load(open(agg_path))
        system, model = meta.get("system", "unknown"), meta.get("model", "unknown")
        seed = _seed_from_dirname(d)
        is_variant = ("improved" in d) or ("_v2" in d)

        for sf in sorted(glob.glob(os.path.join(run_dir, "s*.json"))):
            s = json.load(open(sf))
            if "task_completion" not in s or "library_health" not in s:
                continue
            ets = safety_free_ets(
                s["task_completion"], s.get("mean_tool_quality", 0.0),
                s.get("total_llm_calls", 0), s["library_health"],
            )
            run_rows.append({
                "run_dir": d,
                "system": system,
                "model": model,
                "seed": seed,
                "variant": is_variant,
                "session_id": s.get("session_id", os.path.basename(sf)[:-5]),
                "task_completion": s["task_completion"],
                "task_completion_by_type": s.get("task_completion_by_type", {}),
                "mean_tool_quality": s.get("mean_tool_quality", 0.0),
                "reuse_rate": s.get("reuse_rate", 0.0),
                "correct_reuse_rate": s.get("correct_reuse_rate", 0.0),
                "incorrect_reuse_rate": s.get("incorrect_reuse_rate", 0.0),
                "redundancy_rate": s.get("redundancy_rate", 0.0),
                "library_precision": s.get("library_precision", 0.0),
                "creation_efficiency": s.get("creation_efficiency", 0.0),
                "composition_success": s.get("composition_success", 0.0),
                "regression_rate": s.get("regression_rate", 0.0),
                "library_health": s["library_health"],
                "tools_created": s.get("tools_created", 0),
                "total_llm_calls": s.get("total_llm_calls", 0),
                "evolvetool_score": ets,
            })

        for meta_path in sorted(glob.glob(os.path.join(run_dir, "tools", "*", "*.meta.json"))):
            if "meta_v3" in meta_path:
                continue
            tmeta = json.load(open(meta_path))
            src_path = meta_path.replace(".meta.json", ".py")
            src_hash = None
            if os.path.exists(src_path):
                src_hash = hashlib.sha256(open(src_path, "rb").read()).hexdigest()[:16]
            v3_path = meta_path.replace(".meta.json", ".meta_v3.json")
            v3 = json.load(open(v3_path)).get("scores_v3") if os.path.exists(v3_path) else None
            tool_rows.append({
                "run_dir": d,
                "system": system,
                "model": model,
                "seed": seed,
                "session_id": os.path.basename(os.path.dirname(meta_path)),
                "name": tmeta.get("name"),
                "created_at_task": tmeta.get("created_at_task"),
                "source_hash": src_hash,
                "scores_self": tmeta.get("scores"),
                "scores_capability_aligned": v3,
            })

    # Per-(system, model) aggregates over seed runs, restricted to main (non-variant) runs.
    by_run: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for r in run_rows:
        if r["variant"]:
            continue
        by_run[(r["system"], r["model"], r["run_dir"])].append(r)

    run_means: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for (system, model, _run), rows in by_run.items():
        run_means[(system, model)].append({
            "ets": st.mean(x["evolvetool_score"] for x in rows),
            "tc": st.mean(x["task_completion"] for x in rows),
            "tqs": st.mean(x["mean_tool_quality"] for x in rows),
            "reuse": st.mean(x["reuse_rate"] for x in rows),
            "lh": st.mean(x["library_health"] for x in rows),
            "tools": sum(x["tools_created"] for x in rows),
        })

    aggregate = {}
    for (system, model), runs in sorted(run_means.items()):
        n = len(runs)

        def ms(key):
            vals = [r[key] for r in runs]
            return {"mean": st.mean(vals), "std": (st.pstdev(vals) if n > 1 else 0.0)}

        aggregate[f"{system}/{model}"] = {
            "system": system, "model": model, "n_seeds": n,
            "ets": ms("ets"), "task_completion": ms("tc"),
            "mean_tool_quality": ms("tqs"), "reuse_rate": ms("reuse"),
            "library_health": ms("lh"),
            "tools_total": sum(r["tools"] for r in runs) / n,
        }

    with open(os.path.join(output, "run_manifest.jsonl"), "w") as f:
        for r in run_rows:
            f.write(json.dumps(r) + "\n")
    with open(os.path.join(output, "tool_manifest.jsonl"), "w") as f:
        for r in tool_rows:
            f.write(json.dumps(r) + "\n")
    with open(os.path.join(output, "aggregate.json"), "w") as f:
        json.dump({"_schema": "safety-free ETS; means over n_seeds main runs", "systems": aggregate}, f, indent=2)

    return {"runs": len(run_rows), "tools": len(tool_rows), "systems": len(aggregate)}


def build_task_manifests(output: str) -> dict:
    """Emit hidden_test_manifest.jsonl and audit_report.json from session defs."""
    from evolvetool_bench.types import TaskType

    hidden_rows = []
    total = verified = nonseed = nonseed_with_cap = gaps = gaps_with_hidden = 0
    for domain, sessions in DOMAIN_SESSIONS:
        for snum in sessions:
            mod = importlib.import_module(
                f"evolvetool_bench.domains.{domain}.session_{snum}")
            sess = mod.create_session()
            for t in sess.tasks:
                total += 1
                if t.expected is not None or t.verify is not None:
                    verified += 1
                if t.task_type != TaskType.SEED:
                    nonseed += 1
                    if t.capability_id and t.capability_id.strip():
                        nonseed_with_cap += 1
                if t.task_type == TaskType.GAP:
                    gaps += 1
                    if t.hidden_tests:
                        gaps_with_hidden += 1
                    hidden_rows.append({
                        "domain": domain, "session": f"session_{snum}",
                        "capability_id": t.capability_id, "gap_task": t.id,
                        "n_hidden_tests": len(t.hidden_tests or []),
                        "n_adversarial_tests": len(t.adversarial_tests or []),
                        "has_deterministic_verifier": t.expected is not None or t.verify is not None,
                    })

    with open(os.path.join(output, "hidden_test_manifest.jsonl"), "w") as f:
        for r in hidden_rows:
            f.write(json.dumps(r) + "\n")

    audit = {
        "verifier_coverage": {"verified": verified, "total": total,
                              "fraction": round(verified / total, 4) if total else 0.0},
        "capability_coverage": {"non_seed_with_capability_id": nonseed_with_cap,
                                "non_seed_total": nonseed,
                                "all_covered": nonseed_with_cap == nonseed},
        "hidden_test_coverage": {"gaps_with_hidden_tests": gaps_with_hidden,
                                 "gap_total": gaps,
                                 "all_covered": gaps_with_hidden == gaps},
        "strict_tc_policy": "fail-closed: unverified tasks marked FAIL, never lenient-pass",
    }
    with open(os.path.join(output, "audit_report.json"), "w") as f:
        json.dump(audit, f, indent=2)
    return {"hidden_rows": len(hidden_rows), "verifier_coverage": f"{verified}/{total}"}


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source", default="results_full")
    p.add_argument("--output", default="results_canonical")
    args = p.parse_args(argv)
    stats = build(args.source, args.output)
    tstats = build_task_manifests(args.output)
    stats.update(tstats)
    print(f"Wrote canonical manifests to {args.output}/: "
          f"{stats['runs']} session runs, {stats['tools']} tools, "
          f"{stats['systems']} (system,model) aggregates, "
          f"{stats['hidden_rows']} hidden-test rows, "
          f"verifier coverage {stats['verifier_coverage']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
