#!/usr/bin/env python3
"""Generate the LaTeX results table from the canonical manifests.

Reads ``results_canonical/run_manifest.jsonl`` (produced by
``build_canonical.py``), groups by (system, model), and writes a results table
with mean$\\pm$std ETS/TC/TQS/Reuse/LH that matches the paper's headline table.

Usage:
    python scripts/make_tables.py --results-dir results_canonical --output paper/kdd_eval2026
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import statistics as st
from collections import defaultdict

LABEL = {
    "no-evolution": "No-Evol", "oneshot": "One-Shot", "evoskill": "Strategy-Only",
    "creator-style": "CREATOR-style", "toolcoder-style": "ToolCoder-style",
    "toolmaker-style": "ToolMaker-style", "arise": "Code-Evol",
    "arise-v2": "Code-Evol (sem.\\,Q)",
}
MODEL = {"sonnet": "Sonnet", "haiku": "Haiku", "gpt4o": "GPT-4o"}
SYS_ORDER = ["no-evolution", "oneshot", "evoskill", "creator-style",
             "toolcoder-style", "toolmaker-style", "arise"]
MODEL_ORDER = ["sonnet", "haiku"]


def load_runs(results_dir: pathlib.Path) -> list[dict]:
    path = results_dir / "run_manifest.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _ms(vals: list[float]) -> tuple[float, float]:
    if not vals:
        return 0.0, 0.0
    return st.mean(vals), (st.pstdev(vals) if len(vals) > 1 else 0.0)


def _pm(mean: float, std: float, n: int, pct: bool) -> str:
    scale = 100 if pct else 1
    fmt = ".1f" if pct else ".3f"
    if n > 1:
        return f"{mean*scale:{fmt}}$\\pm${std*scale:{fmt}}"
    return f"{mean*scale:{fmt}}"


def make_table(runs: list[dict]) -> str:
    # collapse session rows -> per-run (run_dir) means, then group by (system, model)
    per_run: dict[tuple, list[dict]] = defaultdict(list)
    for r in runs:
        if r.get("variant"):
            continue
        per_run[(r["system"], r["model"], r["run_dir"])].append(r)
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for (system, model, _rd), rows in per_run.items():
        grouped[(system, model)].append({
            "ets": st.mean(x["evolvetool_score"] for x in rows),
            "tc": st.mean(x["task_completion"] for x in rows),
            "tqs": st.mean(x["mean_tool_quality"] for x in rows),
            "reuse": st.mean(x["reuse_rate"] for x in rows),
            "lh": st.mean(x["library_health"] for x in rows),
            "tools": sum(x["tools_created"] for x in rows),
        })

    lines = [r"\begin{table*}[t]", r"\centering\small",
             r"\begin{tabular}{llccccccc}", r"\toprule",
             r"\textbf{System} & \textbf{Model} & $n$ & \textbf{ETS}$\uparrow$ & "
             r"\textbf{TC (\%)} & \textbf{Tools} & \textbf{TQS} & \textbf{Reuse (\%)} & \textbf{LH (\%)} \\",
             r"\midrule"]
    for model in MODEL_ORDER:
        # best ETS in this model block for bolding
        block = [(s, grouped[(s, model)]) for s in SYS_ORDER if (s, model) in grouped]
        if not block:
            continue
        best = max(block, key=lambda kv: _ms([r["ets"] for r in kv[1]])[0])[0]
        for system, recs in block:
            n = len(recs)
            ets_m, ets_s = _ms([r["ets"] for r in recs])
            tc_m, tc_s = _ms([r["tc"] for r in recs])
            tqs_m, _ = _ms([r["tqs"] for r in recs])
            reuse_m, reuse_s = _ms([r["reuse"] for r in recs])
            lh_m, lh_s = _ms([r["lh"] for r in recs])
            tools = sum(r["tools"] for r in recs) / n
            ets_cell = _pm(ets_m, ets_s, n, False)
            if system == best:
                ets_cell = r"\textbf{" + ets_cell + "}"
            tqs_cell = f"{tqs_m:.3f}" if tqs_m > 0 else "---"
            lines.append(
                f"{LABEL.get(system, system)} & {MODEL.get(model, model)} & {n} & {ets_cell} & "
                f"{_pm(tc_m, tc_s, n, True)} & {tools:.0f} & "
                f"{tqs_cell} & {_pm(reuse_m, reuse_s, n, True)} & "
                f"{_pm(lh_m, lh_s, n, True)} \\\\")
        lines.append(r"\midrule")
    lines[-1] = r"\bottomrule"
    lines += [r"\end{tabular}",
              r"\caption{Headline results regenerated from \texttt{results\_canonical/run\_manifest.jsonl} "
              r"by \texttt{scripts/make\_tables.py}. ETS uses the safety-free composite.}",
              r"\label{tab:results_auto}", r"\end{table*}"]
    return "\n".join(lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--results-dir", default="results_canonical")
    p.add_argument("--output", default="paper/kdd_eval2026")
    args = p.parse_args(argv)
    runs = load_runs(pathlib.Path(args.results_dir))
    if not runs:
        print(f"No run_manifest found in {args.results_dir}; run build_canonical.py first.")
        return 1
    out = pathlib.Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    (out / "auto_results_table.tex").write_text(make_table(runs))
    print(f"Wrote {out / 'auto_results_table.tex'} from {len(runs)} session rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
