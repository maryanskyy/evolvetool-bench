#!/usr/bin/env python3
"""Generate paper figures from the canonical manifests.

Reads ``results_canonical/run_manifest.jsonl`` and produces ``fig_comparison``
(ETS / TC / LH per main Sonnet system, with error bars over seeds).

Usage:
    python scripts/make_figures.py --results-dir results_canonical --output paper/kdd_eval2026
"""
from __future__ import annotations

import argparse
import json
import pathlib
import statistics as st
from collections import defaultdict

LABEL = {
    "no-evolution": "No-Evol", "oneshot": "One-Shot", "evoskill": "Strategy-Only",
    "creator-style": "CREATOR", "arise": "Code-Evol",
}
ORDER = ["no-evolution", "oneshot", "evoskill", "creator-style", "arise"]


def load_runs(results_dir: pathlib.Path) -> list[dict]:
    path = results_dir / "run_manifest.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--results-dir", default="results_canonical")
    p.add_argument("--output", default="paper/kdd_eval2026")
    args = p.parse_args(argv)

    runs = load_runs(pathlib.Path(args.results_dir))
    if not runs:
        print(f"No run_manifest in {args.results_dir}; run build_canonical.py first.")
        return 1
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception as exc:
        print(f"matplotlib unavailable ({exc}); skipping figure generation.")
        return 0

    # per-run means (sonnet, main only) -> per-system seed lists
    per_run: dict[tuple, list[dict]] = defaultdict(list)
    for r in runs:
        if r.get("variant") or r["model"] != "sonnet":
            continue
        per_run[(r["system"], r["run_dir"])].append(r)
    by_sys: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for (system, _rd), rows in per_run.items():
        by_sys[system]["ets"].append(st.mean(x["evolvetool_score"] for x in rows))
        by_sys[system]["tc"].append(st.mean(x["task_completion"] for x in rows))
        by_sys[system]["lh"].append(st.mean(x["library_health"] for x in rows))

    systems = [s for s in ORDER if s in by_sys]
    metrics = [("ets", "ETS", 1.0), ("tc", "TC", 100.0), ("lh", "LH", 100.0)]
    x = np.arange(len(systems))
    width = 0.26
    fig, ax = plt.subplots(figsize=(7, 3.2))
    for i, (key, name, scale) in enumerate(metrics):
        means = [st.mean(by_sys[s][key]) * scale for s in systems]
        stds = [(st.pstdev(by_sys[s][key]) if len(by_sys[s][key]) > 1 else 0.0) * scale for s in systems]
        ax.bar(x + i * width, means, width, yerr=stds, capsize=3, label=name)
    ax.set_xticks(x + width)
    ax.set_xticklabels([LABEL.get(s, s) for s in systems], fontsize=8)
    ax.set_ylabel("Score (ETS x100 scale)")
    ax.legend(ncol=3, fontsize=8, loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()

    out = pathlib.Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        plt.savefig(out / f"fig_comparison.{ext}", dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out / 'fig_comparison.pdf'} (+ .png) from {len(systems)} systems")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
