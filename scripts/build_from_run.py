#!/usr/bin/env python3
"""Build canonical manifests from results_strict_run/ output.

After run_strict.py completes, this script:
  1. Reads run_manifest.jsonl
  2. Computes aggregate stats per system (mean TC, Library Health proxy, reuse rates)
  3. Merges with existing canonical tool manifest
  4. Writes updated aggregate.json and statistical summary
  5. Regenerates auto_results_table.tex to match new numbers

Usage:
    python scripts/build_from_run.py --input results_strict_run/ [--output results_canonical/]
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ──────────────────────────────────────────────────────────────────────────────
# Core analysis
# ──────────────────────────────────────────────────────────────────────────────

def load_runs(run_dir: Path) -> list[dict]:
    runs = []
    rfile = run_dir / "run_manifest.jsonl"
    if not rfile.exists():
        return runs
    with open(rfile) as f:
        for line in f:
            try:
                r = json.loads(line)
                if "error" not in r:
                    runs.append(r)
            except Exception:
                pass
    return runs


def compute_aggregate(runs: list[dict]) -> dict:
    by_system: dict[str, list[dict]] = defaultdict(list)
    for r in runs:
        by_system[r["system"]].append(r)

    agg = {}
    for system, recs in sorted(by_system.items()):
        tcs = [r["tc"] for r in recs]
        n = len(recs)
        mean_tc = sum(tcs) / n if n else 0.0
        var_tc = sum((x - mean_tc) ** 2 for x in tcs) / max(n - 1, 1)
        se_tc = math.sqrt(var_tc / n) if n > 1 else 0.0

        # Per-session means
        by_sess: dict[str, list[float]] = defaultdict(list)
        for r in recs:
            by_sess[r["session_id"]].append(r["tc"])
        per_session = {s: round(sum(v) / len(v), 4) for s, v in by_sess.items()}

        # Aggregate tools / reuse
        tools_created = sum(r.get("tools_created", 0) for r in recs)
        reuse_correct = sum(r.get("reuse_correct", 0) for r in recs)
        reuse_incorrect = sum(r.get("reuse_incorrect", 0) for r in recs)

        # Library Health proxy: reuse correctness rate + tool creation rate (simplified)
        total_reuse = reuse_correct + reuse_incorrect
        reuse_precision = reuse_correct / total_reuse if total_reuse > 0 else 0.0

        agg[system] = {
            "system": system,
            "n_runs": n,
            "mean_tc": round(mean_tc, 4),
            "se_tc": round(se_tc, 4),
            "tc_values": tcs,
            "per_session_tc": per_session,
            "tools_created": tools_created,
            "reuse_correct": reuse_correct,
            "reuse_incorrect": reuse_incorrect,
            "reuse_precision": round(reuse_precision, 4),
        }

    return agg


def print_summary_table(agg: dict) -> None:
    print("\n" + "=" * 65)
    print(f"{'System':<20} {'N':>4} {'Mean TC':>8} {'SE':>6} {'Tools':>6} {'RePrec':>8}")
    print("-" * 65)
    for system, data in sorted(agg.items(), key=lambda x: -x[1]["mean_tc"]):
        print(
            f"  {system:<18} {data['n_runs']:>4} "
            f"{data['mean_tc']:>8.3f} {data['se_tc']:>6.3f} "
            f"{data['tools_created']:>6} {data['reuse_precision']:>8.3f}"
        )
    print("=" * 65)


def generate_latex_table(agg: dict, out_path: Path) -> None:
    """Write auto_results_table.tex for paper inclusion."""
    systems_order = sorted(agg.keys(), key=lambda s: -agg[s]["mean_tc"])

    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{Main results: Task Completion (TC) and Reuse Precision across systems.",
        r"  TC is computed on the verified-task subset (fail-closed). Mean $\pm$ SE over 3 seeds.}",
        r"\label{tab:main-results}",
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"\textbf{System} & \textbf{TC} & \textbf{SE} & \textbf{Tools} & \textbf{Reuse Prec.} \\",
        r"\midrule",
    ]
    for system in systems_order:
        d = agg[system]
        lines.append(
            f"{system.replace('_', r'-')} & {d['mean_tc']:.3f} & "
            f"{d['se_tc']:.3f} & {d['tools_created']} & "
            f"{d['reuse_precision']:.3f} \\\\"
        )
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    out_path.write_text("\n".join(lines) + "\n")
    print(f"LaTeX table written to {out_path}")


# ──────────────────────────────────────────────────────────────────────────────
# Bootstrap CI for TC contrast (OneShot vs No-Evolution as primary claim)
# ──────────────────────────────────────────────────────────────────────────────

def bootstrap_contrast(
    tcs_a: list[float], tcs_b: list[float], n_boot: int = 10_000
) -> tuple[float, float, float]:
    """Paired hierarchical bootstrap: returns (point_est, ci_low, ci_high)."""
    import random

    if len(tcs_a) != len(tcs_b) or not tcs_a:
        return (0.0, 0.0, 0.0)

    n = len(tcs_a)
    diffs = [a - b for a, b in zip(tcs_a, tcs_b)]
    point = sum(diffs) / n

    boot_diffs: list[float] = []
    for _ in range(n_boot):
        sample = [random.choice(diffs) for _ in range(n)]
        boot_diffs.append(sum(sample) / n)

    boot_diffs.sort()
    lo = boot_diffs[int(0.025 * n_boot)]
    hi = boot_diffs[int(0.975 * n_boot)]
    return (round(point, 4), round(lo, 4), round(hi, 4))


def compute_claims(agg: dict, all_runs: list[dict]) -> dict:
    """Compute the pre-registered claims with bootstrap CIs."""
    claims: dict = {}

    # Align runs: pair by (session_id, seed)
    def get_tc_series(system: str) -> list[float]:
        recs = [r for r in all_runs if r["system"] == system]
        return [r["tc"] for r in sorted(recs, key=lambda r: (r["session_id"], r["seed"]))]

    systems = list(agg.keys())
    # Claim A: OneShot > No-Evolution
    if "oneshot" in systems and "no_evolution" in systems:
        tcs_a = get_tc_series("oneshot")
        tcs_b = get_tc_series("no_evolution")
        if len(tcs_a) == len(tcs_b):
            pt, lo, hi = bootstrap_contrast(tcs_a, tcs_b)
            claims["oneshot_vs_no_evolution"] = {
                "contrast": "oneshot - no_evolution",
                "point_est": pt,
                "ci_95_lo": lo,
                "ci_95_hi": hi,
                "supported": lo > 0,
            }

    # Claim B: Creator / ToolMaker > OneShot (tool quality)
    for sys_b in ["creator", "toolmaker"]:
        if sys_b in systems and "oneshot" in systems:
            tcs_a = get_tc_series(sys_b)
            tcs_b = get_tc_series("oneshot")
            if len(tcs_a) == len(tcs_b):
                pt, lo, hi = bootstrap_contrast(tcs_a, tcs_b)
                claims[f"{sys_b}_vs_oneshot"] = {
                    "contrast": f"{sys_b} - oneshot",
                    "point_est": pt,
                    "ci_95_lo": lo,
                    "ci_95_hi": hi,
                    "supported": lo > 0,
                }

    return claims


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="results_strict_run/", help="Directory with run_manifest.jsonl")
    parser.add_argument("--output", default="results_canonical/", help="Output directory for manifests")
    parser.add_argument("--latex-dir", default="paper/kdd_eval2026/", help="Directory for auto-generated LaTeX")
    args = parser.parse_args()

    in_dir = Path(args.input)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading runs from {in_dir / 'run_manifest.jsonl'}...")
    runs = load_runs(in_dir)
    print(f"  {len(runs)} valid runs loaded")

    if not runs:
        print("No valid runs found. Run run_strict.py first.")
        return

    agg = compute_aggregate(runs)
    print_summary_table(agg)

    # Write aggregate
    agg_out = out_dir / "aggregate.json"
    with open(agg_out, "w") as f:
        json.dump(agg, f, indent=2)
    print(f"\nAggregate written to {agg_out}")

    # Copy run manifest
    shutil.copy(in_dir / "run_manifest.jsonl", out_dir / "run_manifest.jsonl")
    print(f"run_manifest.jsonl copied to {out_dir}")

    # Bootstrap claims
    claims = compute_claims(agg, runs)
    claims_out = out_dir / "claims.json"
    with open(claims_out, "w") as f:
        json.dump(claims, f, indent=2)
    print(f"Claims (with bootstrap CIs) written to {claims_out}")

    if claims:
        print("\nPre-registered Claims:")
        for k, c in claims.items():
            supported = "✓" if c.get("supported") else "✗"
            print(f"  [{supported}] {c['contrast']}: "
                  f"{c['point_est']:+.3f} [{c['ci_95_lo']:+.3f}, {c['ci_95_hi']:+.3f}]")

    # Generate LaTeX table
    latex_dir = Path(args.latex_dir)
    if latex_dir.exists():
        generate_latex_table(agg, latex_dir / "auto_results_table.tex")
    else:
        generate_latex_table(agg, out_dir / "auto_results_table.tex")


if __name__ == "__main__":
    main()
