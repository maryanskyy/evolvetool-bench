#!/usr/bin/env python3
"""Strict experimental run: execute baselines over verified-task sessions.

Usage:
    python scripts/run_strict.py [--systems S1,S2] [--seeds 42,1,2] [--pilot]
                                  [--output results_canonical/] [--resume]

The script:
  1. Loads all sessions (data_transform_s1..s5, numerical_s1..s3).
  2. For each (seed, system, session), calls run_session().
  3. Scores each task using fail-closed verification (verify / expected only).
     Tasks with neither verifier are marked as UNVERIFIED and skipped from TC.
  4. Writes per-run JSONL + aggregate JSON into --output.
  5. Supports --resume to skip already-completed (system, session, seed) tuples.

Baselines use Anthropic claude-haiku-4-5. Set ANTHROPIC_API_KEY before running.
  no_evolution, oneshot, creator_style, evoskill, toolmaker
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# CRITICAL: patch sys.modules["litellm"] with our shim BEFORE any
# baseline modules are imported. All baselines do `import litellm` inline, so
# they will pick up our shim automatically.
import evolvetool_bench.harness.litellm_shim as _shim  # noqa: E402
sys.modules["litellm"] = _shim  # type: ignore[assignment]

from evolvetool_bench.domains.data_transform import (  # noqa: E402
    session_1 as dt_s1, session_2 as dt_s2, session_3 as dt_s3,
    session_4 as dt_s4, session_5 as dt_s5,
)
from evolvetool_bench.domains.numerical import (  # noqa: E402
    session_1 as num_s1, session_2 as num_s2, session_3 as num_s3,
)
from evolvetool_bench.harness.runner import run_session  # noqa: E402
from evolvetool_bench.baselines.no_evolution import NoEvolutionSystem  # noqa: E402
from evolvetool_bench.baselines.oneshot_system import OneShotSystem  # noqa: E402
from evolvetool_bench.baselines.creator_style import CREATORStyleSystem as CreatorStyleSystem  # noqa: E402
from evolvetool_bench.baselines.evoskill_system import EvoSkillSystem  # noqa: E402
from evolvetool_bench.baselines.toolmaker_style import ToolMakerStyleSystem as ToolMakerSystem  # noqa: E402


# ──────────────────────────────────────────────────────────────────────────────
# Session registry
# ──────────────────────────────────────────────────────────────────────────────

ALL_SESSIONS = [
    dt_s1.create_session(), dt_s2.create_session(), dt_s3.create_session(),
    dt_s4.create_session(), dt_s5.create_session(),
    num_s1.create_session(), num_s2.create_session(), num_s3.create_session(),
]

# ──────────────────────────────────────────────────────────────────────────────
# System registry
# ──────────────────────────────────────────────────────────────────────────────

_DEFAULT_MODEL = "claude-haiku-4-5"


def make_system(name: str, model: str):
    """Instantiate a named AgentSystem."""
    if name == "no_evolution":
        return NoEvolutionSystem(model=model)
    elif name == "oneshot":
        return OneShotSystem(model=model, synthesis_model=model)
    elif name == "creator":
        return CreatorStyleSystem(model=model, synthesis_model=model)
    elif name == "evoskill":
        return EvoSkillSystem(model=model, synthesis_model=model)
    elif name == "toolmaker":
        return ToolMakerSystem(model=model, synthesis_model=model)
    else:
        raise ValueError(f"Unknown system: {name!r}")


ALL_SYSTEMS = ["no_evolution", "oneshot", "creator", "evoskill", "toolmaker"]

# ──────────────────────────────────────────────────────────────────────────────
# Scoring helpers
# ──────────────────────────────────────────────────────────────────────────────

def score_session_result(session_result, session=None) -> dict:
    """Extract verified-only TC and other metrics from a SessionResult.

    For verified-only TC, we count only non-seed tasks whose Task has a
    verify function or expected value set. We get this from the session
    object passed alongside; if not available we use all non-seed tasks.
    """
    # Build a map of task_id -> is_verified from the session definition
    verified_task_ids: set[str] | None = None
    if session is not None:
        verified_task_ids = {
            t.id for t in session.tasks
            if (t.verify is not None or t.expected is not None)
            and t.task_type.value != "seed"
        }

    verified_pass = 0
    verified_total = 0
    unverified = 0
    tools_created = 0
    reuse_correct = 0
    reuse_incorrect = 0

    for tr in session_result.task_results:
        task_type = tr.task_type.value if hasattr(tr.task_type, 'value') else str(tr.task_type)
        if task_type == "seed":
            continue  # seed tasks not in TC calculation

        is_verified = (
            verified_task_ids is None or tr.task_id in verified_task_ids
        )

        if is_verified:
            verified_total += 1
            if tr.passed:
                verified_pass += 1
        else:
            unverified += 1

        if tr.tool_reused_correctly:
            reuse_correct += 1
        elif tr.tool_reused and not tr.tool_reused_correctly:
            reuse_incorrect += 1

        if tr.tool_created:
            tools_created += 1

    tc = verified_pass / verified_total if verified_total > 0 else 0.0
    return {
        "tc": round(tc, 4),
        "verified_pass": verified_pass,
        "verified_total": verified_total,
        "unverified": unverified,
        "tools_created": tools_created,
        "reuse_correct": reuse_correct,
        "reuse_incorrect": reuse_incorrect,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Main run logic
# ──────────────────────────────────────────────────────────────────────────────

def run_all(
    systems: list[str],
    seeds: list[int],
    output_dir: Path,
    model: str = _DEFAULT_MODEL,
    pilot: bool = False,
    resume: bool = False,
    verbose: bool = True,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    runs_file = output_dir / "run_manifest.jsonl"
    aggregate_file = output_dir / "aggregate.json"

    # Load existing runs for resume
    completed: set[str] = set()
    if resume and runs_file.exists():
        with open(runs_file) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    key = f"{r['system']}/{r['session_id']}/{r['seed']}"
                    completed.add(key)
                except Exception:
                    pass
        print(f"[resume] {len(completed)} runs already completed")

    sessions = ALL_SESSIONS[:1] if pilot else ALL_SESSIONS

    runs_fh = open(runs_file, "a")
    all_results: list[dict] = []

    total_combos = len(systems) * len(seeds) * len(sessions)
    done = 0

    for system_name in systems:
        for seed in seeds:
            import random
            random.seed(seed)

            system = make_system(system_name, model)

            for session in sessions:
                key = f"{system_name}/{session.id}/{seed}"
                if key in completed:
                    print(f"  [skip] {key}")
                    continue

                print(f"\n{'='*60}")
                print(f"  System: {system_name} | Session: {session.id} | Seed: {seed}")
                print(f"  Progress: {done+1}/{total_combos}")
                print(f"{'='*60}")

                t0 = time.time()
                try:
                    system.reset()
                    result = run_session(system, session, verbose=verbose)
                    scores = score_session_result(result, session=session)
                    elapsed = round(time.time() - t0, 1)

                    # Per-tool source preservation. Without this, ./bench_skills/skills.db
                    # is wiped between sessions and tool source is lost — making in-regime
                    # held-out conformance replay impossible. Mirrors run_full_matrix.py
                    # lines 86-108. Backward-compatible: emits to tools/ subdir only.
                    tools_created_meta: list[dict] = []
                    if getattr(result, "tools_created", None):
                        tools_dir = output_dir / "tools" / system_name / session.id / f"seed_{seed}"
                        tools_dir.mkdir(parents=True, exist_ok=True)
                        for t in result.tools_created:
                            with open(tools_dir / f"{t.name}.py", "w") as f:
                                f.write(t.implementation)
                            if getattr(t, "test_suite", None):
                                with open(tools_dir / f"{t.name}_tests.py", "w") as f:
                                    f.write(t.test_suite)
                            meta = {
                                "name": t.name,
                                "system": system_name,
                                "session_id": session.id,
                                "seed": seed,
                                "model": model,
                                "created_at_task": getattr(t, "created_at_task", None),
                                "version": getattr(t, "version", 1),
                                "scores_in_session": {
                                    "tqs": getattr(t, "quality_score", None),
                                    "correctness": getattr(t, "correctness", None),
                                    "robustness": getattr(t, "robustness", None),
                                    "generality": getattr(t, "generality", None),
                                    "code_quality": getattr(t, "code_quality", None),
                                },
                            }
                            with open(tools_dir / f"{t.name}.meta.json", "w") as f:
                                json.dump(meta, f, indent=2)
                            tools_created_meta.append({
                                "name": t.name,
                                "path": str(tools_dir / f"{t.name}.py"),
                                "meta_path": str(tools_dir / f"{t.name}.meta.json"),
                            })

                    run_record = {
                        "system": system_name,
                        "session_id": session.id,
                        "domain": session.domain,
                        "seed": seed,
                        "model": model,
                        "tc": scores["tc"],
                        "verified_pass": scores["verified_pass"],
                        "verified_total": scores["verified_total"],
                        "unverified": scores["unverified"],
                        "tools_created": scores["tools_created"],
                        "reuse_correct": scores["reuse_correct"],
                        "reuse_incorrect": scores["reuse_incorrect"],
                        "total_tasks": len(session.tasks),
                        "elapsed_s": elapsed,
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "tools_preserved": tools_created_meta,
                    }
                    runs_fh.write(json.dumps(run_record) + "\n")
                    runs_fh.flush()
                    all_results.append(run_record)
                    completed.add(key)
                    done += 1

                    print(f"  TC={scores['tc']:.3f} ({scores['verified_pass']}/{scores['verified_total']} verified)"
                          f" | tools_created={scores['tools_created']} | elapsed={elapsed}s")

                except Exception as e:
                    print(f"  [ERROR] {system_name}/{session.id}/{seed}: {e}")
                    traceback.print_exc()
                    # Write error record
                    error_record = {
                        "system": system_name,
                        "session_id": session.id,
                        "domain": session.domain,
                        "seed": seed,
                        "model": model,
                        "tc": 0.0,
                        "error": str(e),
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    }
                    runs_fh.write(json.dumps(error_record) + "\n")
                    runs_fh.flush()
                    done += 1

    runs_fh.close()

    # Write aggregate
    _write_aggregate(output_dir, aggregate_file)
    print(f"\n\nDone. Results in {output_dir}/")


def _write_aggregate(output_dir: Path, aggregate_file: Path) -> None:
    """Read run_manifest.jsonl and compute per-system aggregate metrics."""
    runs_file = output_dir / "run_manifest.jsonl"
    if not runs_file.exists():
        return

    from collections import defaultdict
    by_system: dict[str, list[dict]] = defaultdict(list)
    with open(runs_file) as f:
        for line in f:
            try:
                r = json.loads(line)
                if "error" not in r:
                    by_system[r["system"]].append(r)
            except Exception:
                pass

    agg: dict[str, dict] = {}
    for system, records in by_system.items():
        tcs = [r["tc"] for r in records]
        n = len(records)
        mean_tc = sum(tcs) / n if n else 0.0
        # Per-session TC averaged across seeds
        from collections import defaultdict as dd2
        by_sess: dict = dd2(list)
        for r in records:
            by_sess[r["session_id"]].append(r["tc"])
        per_session = {sid: round(sum(v) / len(v), 4) for sid, v in by_sess.items()}

        tools_created = sum(r.get("tools_created", 0) for r in records)
        reuse_correct = sum(r.get("reuse_correct", 0) for r in records)
        reuse_incorrect = sum(r.get("reuse_incorrect", 0) for r in records)

        agg[system] = {
            "system": system,
            "n_runs": n,
            "mean_tc": round(mean_tc, 4),
            "tc_values": sorted(tcs),
            "per_session_tc": per_session,
            "tools_created": tools_created,
            "reuse_correct": reuse_correct,
            "reuse_incorrect": reuse_incorrect,
        }

    with open(aggregate_file, "w") as f:
        json.dump(agg, f, indent=2)
    print(f"Aggregate written to {aggregate_file}")

    # Print summary table
    print("\n" + "="*60)
    print(f"{'System':<20} {'N runs':>7} {'Mean TC':>8}")
    print("-"*40)
    for sys_name, data in sorted(agg.items(), key=lambda x: -x[1]['mean_tc']):
        print(f"  {sys_name:<18} {data['n_runs']:>7} {data['mean_tc']:>8.3f}")
    print("="*60)


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Run strict EvolveTool-Bench experiment")
    parser.add_argument("--systems", default=",".join(ALL_SYSTEMS),
                        help="Comma-separated system names (default: all)")
    parser.add_argument("--seeds", default="42,1,2",
                        help="Comma-separated random seeds (default: 42,1,2)")
    parser.add_argument("--model", default=_DEFAULT_MODEL,
                        help="Claude model to use (default: claude-haiku-4-5)")
    parser.add_argument("--output", default="results_canonical/",
                        help="Output directory (default: results_canonical/)")
    parser.add_argument("--pilot", action="store_true",
                        help="Pilot mode: only run data_transform_s1")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from existing run_manifest.jsonl")
    parser.add_argument("--verbose", action="store_true",
                        help="Verbose task-by-task output")
    args = parser.parse_args()

    systems = [s.strip() for s in args.systems.split(",")]
    seeds = [int(s.strip()) for s in args.seeds.split(",")]
    output_dir = Path(args.output)

    print("EvolveTool-Bench Strict Run")
    print(f"  Systems: {systems}")
    print(f"  Seeds:   {seeds}")
    print(f"  Model:   {args.model}")
    print(f"  Output:  {output_dir}")
    print(f"  Pilot:   {args.pilot}")
    print(f"  Resume:  {args.resume}")
    print()

    run_all(
        systems=systems,
        seeds=seeds,
        output_dir=output_dir,
        model=args.model,
        pilot=args.pilot,
        resume=args.resume,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
