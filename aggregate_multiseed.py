"""Aggregate multi-seed results into mean ± std tables and tex-ready output.

Designed to be run AFTER all phase 1 and phase 2 runs complete. Reads every
aggregate.json under results_full/, groups by (system, model), and emits:

  - results_table.tex          — the main results table with ±std for multi-seed configs
  - ets_robustness_table.tex   — Table 2 (weight schemes) with updated numbers
  - results_summary.csv        — flat CSV for sanity checking

Usage:
  python aggregate_multiseed.py
"""

from __future__ import annotations

import json
import os
import glob
import statistics as st
import re
from collections import defaultdict


CONFIG_LABEL = {
    "no-evolution": "No-Evol",
    "oneshot": "One-Shot",
    "evoskill": "Strategy-Only",
    "arise": "Code-Evol",
    "arise-v2": "Code-Evol (sem.\\,Q)",  # LaTeX-rendered in tables
    "toolmaker-style": "ToolMaker-style",
    "creator-style": "CREATOR-style",
    "toolcoder-style": "ToolCoder-style",
    "human-oracle": "Oracle",
}

# Matplotlib doesn't process LaTeX-style escapes — use plain-text labels for the figure
FIG_LABEL = {
    **CONFIG_LABEL,
    "arise-v2": "Code-Evol (sem.Q)",
}

MODEL_LABEL = {
    "sonnet": "Sonnet",
    "haiku": "Haiku",
    "gpt4o": "GPT-4o",
}

# Display order
SYSTEM_ORDER = ["no-evolution", "oneshot", "evoskill", "creator-style", "toolcoder-style", "toolmaker-style", "arise", "arise-v2"]
MODEL_ORDER = ["sonnet", "haiku", "gpt4o"]


def group_seeds(results_dir: str = "results_full") -> dict:
    """Group aggregate.jsons by (system, model). Multi-seed = multiple entries.

    Runs whose directory name ends in `_v2` are kept in a separate group with the
    system name suffixed `-v2` (e.g., `arise_sonnet_v2` → ('arise-v2', 'sonnet')).
    This separates runs that use the semantic Q metric + tool preservation from
    the original surface-Q runs, since averaging them would be invalid.
    """
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for d in sorted(os.listdir(results_dir)):
        agg = os.path.join(results_dir, d, "aggregate.json")
        if not os.path.exists(agg):
            continue
        with open(agg) as f:
            data = json.load(f)
        system = data["system"]
        model = data["model"]
        # Skip early "improved" runs (not in the paper)
        if "improved" in d:
            continue
        # Separate v2/preserved-tool runs into their own group so they aren't
        # mixed with surface-Q (no-preservation) runs. We use `_v2` anywhere in
        # the directory name as the marker (so e.g. arise_sonnet_v2,
        # arise_sonnet_v2_seed1, arise_sonnet_v2_seed2 all belong together).
        if "_v2" in d:
            system = f"{system}-v2"
        # Recompute ETS under the safety-free composite (ETS = 0.30*TC + 0.20*TQS
        # + 0.10*(1-RC) + 0.40*LH). The stored avg_evolvetool_score used the old
        # formula (0.25/0.20/0.10/0.30 + 0.15*safety). Because safety was a
        # constant 1.0 and the RC term is unchanged, the exact transform is:
        #   new = old - 0.15*safety + 0.05*TC + 0.10*LH   (safety == 1.0)
        old_ets = data.get("avg_evolvetool_score", 0.0)
        tc = data.get("avg_task_completion", 0.0)
        lh = data.get("avg_library_health", 0.0)
        data["avg_evolvetool_score"] = old_ets - 0.15 + 0.05 * tc + 0.10 * lh
        grouped[(system, model)].append(data)
    return grouped


def stats(values: list[float]) -> tuple[float, float]:
    """Return (mean, sample-std). Std is 0 for n<2."""
    if not values:
        return 0.0, 0.0
    m = st.mean(values)
    s = st.pstdev(values) if len(values) > 1 else 0.0
    return m, s


def fmt_pm(mean: float, std: float, n: int, pct: bool = True) -> str:
    if pct:
        if n > 1:
            return f"{mean*100:.1f}$\\pm${std*100:.1f}"
        return f"{mean*100:.1f}"
    if n > 1:
        return f"{mean:.3f}$\\pm${std:.3f}"
    return f"{mean:.3f}"


def write_results_table(grouped: dict, out_path: str) -> None:
    """Main results table (Table 3 in the paper) with mean±std for multi-seed configs."""
    lines = []
    lines.append("\\begin{table*}[t]")
    lines.append("\\centering\\small")
    lines.append("\\begin{tabular}{llccccccc}")
    lines.append("\\toprule")
    lines.append("\\textbf{System} & \\textbf{Model} & $n$ & \\textbf{ETS}$\\uparrow$ & \\textbf{TC (\\%)} & \\textbf{Tools} & \\textbf{TQS} & \\textbf{Reuse (\\%)} & \\textbf{LH (\\%)} \\\\")
    lines.append("\\midrule")

    sec_break_after_models = {"sonnet": True, "haiku": True, "gpt4o": False}

    for model in MODEL_ORDER:
        for sys_name in SYSTEM_ORDER:
            runs = grouped.get((sys_name, model), [])
            if not runs:
                continue
            n = len(runs)
            ets_m, ets_s = stats([r["avg_evolvetool_score"] for r in runs])
            tc_m, tc_s = stats([r["avg_task_completion"] for r in runs])
            tools_m = sum(r["total_tools"] for r in runs) / n  # mean over seeds
            tqs_m, tqs_s = stats([r["avg_tool_quality"] for r in runs])
            reuse_m, reuse_s = stats([r["avg_reuse_rate"] for r in runs])
            lh_m, lh_s = stats([r["avg_library_health"] for r in runs])

            sys_lbl = CONFIG_LABEL.get(sys_name, sys_name)
            mdl_lbl = MODEL_LABEL.get(model, model)

            # Bold the highest ETS in this model
            row = [
                sys_lbl, mdl_lbl, str(n),
                fmt_pm(ets_m, ets_s, n, pct=False),
                fmt_pm(tc_m, tc_s, n, pct=True),
                f"{tools_m:.1f}" if (tools_m % 1) else f"{int(tools_m)}",
                f"{tqs_m:.3f}" if tqs_m > 0 else "---",
                fmt_pm(reuse_m, reuse_s, n, pct=True),
                fmt_pm(lh_m, lh_s, n, pct=True),
            ]
            lines.append(" & ".join(row) + " \\\\")
        # Section break between models
        if sec_break_after_models.get(model):
            lines.append("\\midrule")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\caption{Full results across systems, models, and seeds. $n$ is the seed count. "
                  "Multi-seed runs report mean$\\pm$std; single-seed runs report point estimates.}")
    lines.append("\\label{tab:results}")
    lines.append("\\end{table*}")

    with open(out_path, "w") as f:
        f.write("\n".join(lines))


def write_summary_csv(grouped: dict, out_path: str) -> None:
    lines = ["system,model,seed_count,ETS,TC,Tools,TQS,Reuse,LH"]
    for (sys_name, model), runs in sorted(grouped.items()):
        for r in runs:
            lines.append(",".join([
                sys_name, model,
                str(len(runs)),
                f"{r['avg_evolvetool_score']:.4f}",
                f"{r['avg_task_completion']:.4f}",
                str(r["total_tools"]),
                f"{r['avg_tool_quality']:.4f}",
                f"{r['avg_reuse_rate']:.4f}",
                f"{r['avg_library_health']:.4f}",
            ]))
    with open(out_path, "w") as f:
        f.write("\n".join(lines))


def write_comparison_figure(grouped: dict, out_path: str) -> None:
    """Bar chart with error bars across (system, model) combinations.

    For clarity, only include systems with multi-seed (n>=4) coverage on Sonnet,
    plus the Haiku reference rows. Single-seed variants (ToolMaker-style,
    Code-Evol sem.Q, ToolCoder-style) appear in the full table but not the figure.
    """
    import matplotlib.pyplot as plt
    import numpy as np

    INCLUDE_IN_FIG = {("no-evolution","sonnet"), ("oneshot","sonnet"),
                      ("evoskill","sonnet"), ("creator-style","sonnet"),
                      ("arise","sonnet"),
                      ("no-evolution","haiku"), ("arise","haiku")}

    entries = []
    for model in ["sonnet", "haiku"]:
        for sys_name in SYSTEM_ORDER:
            runs = grouped.get((sys_name, model), [])
            if not runs:
                continue
            if (sys_name, model) not in INCLUDE_IN_FIG:
                continue
            tc_m, tc_s = stats([r["avg_task_completion"] for r in runs])
            tqs_m, tqs_s = stats([r["avg_tool_quality"] for r in runs])
            reuse_m, reuse_s = stats([r["avg_reuse_rate"] for r in runs])
            lh_m, lh_s = stats([r["avg_library_health"] for r in runs])
            label = f"{FIG_LABEL.get(sys_name, sys_name)}\n({MODEL_LABEL.get(model, model)}, n={len(runs)})"
            entries.append({
                "label": label,
                "TC": (tc_m * 100, tc_s * 100),
                "TQS": (tqs_m * 100, tqs_s * 100),
                "Reuse": (reuse_m * 100, reuse_s * 100),
                "LH": (lh_m * 100, lh_s * 100),
            })

    if not entries:
        return

    metrics = ["TC", "TQS", "Reuse", "LH"]
    colors = ["#60a5fa", "#86efac", "#fbbf24", "#c084fc"]

    fig, ax = plt.subplots(figsize=(9, 4))
    x = np.arange(len(entries))
    width = 0.2

    for i, m in enumerate(metrics):
        means = [e[m][0] for e in entries]
        stds = [e[m][1] for e in entries]
        ax.bar(x + i * width, means, width, yerr=stds, capsize=2,
               label=m, color=colors[i], edgecolor="white", linewidth=0.5)

    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels([e["label"] for e in entries], fontsize=6.5)
    ax.set_ylabel("Score (%)", fontsize=10)
    ax.set_ylim(0, 100)
    ax.legend(fontsize=8, ncol=4, loc="upper left")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.savefig(out_path.replace(".pdf", ".png"), dpi=300, bbox_inches="tight")
    plt.close()


def main():
    grouped = group_seeds()
    print(f"Loaded {sum(len(v) for v in grouped.values())} aggregate files across "
          f"{len(grouped)} (system,model) combos")
    for k, v in sorted(grouped.items()):
        print(f"  {k}: n={len(v)}")

    # Canonical output dir for the KDD Eval 2026 submission.
    os.makedirs("paper/kdd_eval2026", exist_ok=True)
    write_results_table(grouped, "paper/kdd_eval2026/auto_results_table.tex")
    write_summary_csv(grouped, "paper/kdd_eval2026/auto_results_summary.csv")
    try:
        write_comparison_figure(grouped, "paper/kdd_eval2026/fig_comparison.pdf")
    except Exception as exc:  # matplotlib may be unavailable in some envs
        print(f"  (skipped figure: {exc})")
    print("\nGenerated:")
    print("  paper/kdd_eval2026/auto_results_table.tex")
    print("  paper/kdd_eval2026/auto_results_summary.csv")


if __name__ == "__main__":
    main()
