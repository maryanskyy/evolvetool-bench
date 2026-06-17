#!/usr/bin/env python3
"""Compute the paper's primary statistical claims with confidence intervals.

Reads ``results_canonical/run_manifest.jsonl`` (session-level rows, one per
seed x session) and produces:

  results_canonical/statistical_report.json   machine-readable CIs / p-values
  paper/kdd_eval2026/auto_stats_table.tex      LaTeX table of LH contrasts

Primary claims (pre-registered):
  A. Library-management protocols improve library health (LH) vs No-Evolution
     and vs Strategy-Only  -> paired hierarchical bootstrap over (seed, session).
  B. Raw reuse vs correct/incorrect reuse diverge -> per-system reuse precision
     with bootstrap CIs.
  C. LH is not a TC proxy -> Pearson/Spearman correlation with bootstrap CI and
     a |r| < 0.25 equivalence read.

All inference is non-parametric bootstrap (10k resamples, fixed seed) so the
report is fully reproducible from the manifest. We deliberately treat
CREATOR-vs-Code-Evol as descriptive (likely underpowered at n=4).

Usage:
    python scripts/stats_report.py --results-dir results_canonical --output paper/kdd_eval2026
"""
from __future__ import annotations

import argparse
import json
import pathlib
from collections import defaultdict

import numpy as np
from scipy import stats

RNG = np.random.default_rng(20260604)
N_BOOT = 10000
MAIN = ["no-evolution", "oneshot", "evoskill", "creator-style", "arise"]
LABEL = {"no-evolution": "No-Evol", "oneshot": "One-Shot", "evoskill": "Strategy-Only",
         "creator-style": "CREATOR-style", "arise": "Code-Evol"}


def load(results_dir: pathlib.Path) -> list[dict]:
    rows = [json.loads(l) for l in (results_dir / "run_manifest.jsonl").read_text().splitlines() if l.strip()]
    return [r for r in rows if r["model"] == "sonnet" and not r["variant"] and r["system"] in MAIN]


def _cell_index(rows: list[dict]) -> dict[str, dict[tuple, float]]:
    """system -> {(seed, session): value}. Returns the row dicts keyed for pairing."""
    idx: dict[str, dict[tuple, dict]] = defaultdict(dict)
    for r in rows:
        idx[r["system"]][(r["seed"], r["session_id"])] = r
    return idx


def paired_hier_bootstrap_diff(idx, sys_a, sys_b, metric):
    """Hierarchical bootstrap (resample seeds, then sessions) of mean(a - b)."""
    common = sorted(set(idx[sys_a]) & set(idx[sys_b]))
    seeds = sorted({k[0] for k in common})
    by_seed = defaultdict(list)
    for (seed, sess) in common:
        by_seed[seed].append((seed, sess))
    diffs = np.array([idx[sys_a][k][metric] - idx[sys_b][k][metric] for k in common])
    obs = float(diffs.mean())
    boot = np.empty(N_BOOT)
    for i in range(N_BOOT):
        rs = RNG.choice(seeds, size=len(seeds), replace=True)
        vals = []
        for s in rs:
            cells = by_seed[s]
            pick = RNG.integers(0, len(cells), size=len(cells))
            for j in pick:
                k = cells[j]
                vals.append(idx[sys_a][k][metric] - idx[sys_b][k][metric])
        boot[i] = np.mean(vals)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    p = 2 * min((boot <= 0).mean(), (boot >= 0).mean())
    return {"mean_diff": obs, "ci95": [float(lo), float(hi)],
            "p_boot": float(min(p, 1.0)), "n_pairs": len(common)}


def bootstrap_mean_ci(values):
    v = np.asarray(values, float)
    boot = np.array([RNG.choice(v, size=len(v), replace=True).mean() for _ in range(N_BOOT)])
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return {"mean": float(v.mean()), "ci95": [float(lo), float(hi)]}


def corr_with_ci(x, y, method):
    x, y = np.asarray(x, float), np.asarray(y, float)
    fn = stats.pearsonr if method == "pearson" else stats.spearmanr
    obs = float(fn(x, y)[0])
    boot = np.empty(N_BOOT)
    n = len(x)
    for i in range(N_BOOT):
        idx = RNG.integers(0, n, size=n)
        boot[i] = fn(x[idx], y[idx])[0]
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return {"r": obs, "ci95": [float(lo), float(hi)], "n": n,
            "equiv_025": bool(abs(lo) < 0.25 and abs(hi) < 0.25)}


def benjamini_hochberg(pvals):
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    prev = 1.0
    for rank, i in enumerate(reversed(order)):
        k = m - rank
        prev = min(prev, p[i] * m / k)
        adj[i] = prev
    return adj.tolist()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", default="results_canonical")
    ap.add_argument("--output", default="paper/kdd_eval2026")
    args = ap.parse_args(argv)

    results_dir = pathlib.Path(args.results_dir)
    rows = load(results_dir)
    idx = _cell_index(rows)

    # --- Claim A: LH contrasts ---
    contrasts = [("arise", "no-evolution"), ("creator-style", "no-evolution"),
                 ("arise", "evoskill"), ("creator-style", "evoskill")]
    lh = {f"{a}_vs_{b}": paired_hier_bootstrap_diff(idx, a, b, "library_health")
          for a, b in contrasts}
    adj = benjamini_hochberg([lh[k]["p_boot"] for k in lh])
    for k, q in zip(lh, adj):
        lh[k]["p_adj_bh"] = float(q)

    # --- Claim B: reuse precision ---
    reuse = {}
    for s in MAIN:
        rr = [r["reuse_rate"] for r in rows if r["system"] == s]
        cr = [r["correct_reuse_rate"] for r in rows if r["system"] == s]
        ir = [r["incorrect_reuse_rate"] for r in rows if r["system"] == s]
        prec = [c / rt if rt > 0 else np.nan for c, rt in zip(cr, rr)]
        prec = [p for p in prec if not np.isnan(p)]
        reuse[s] = {"raw_reuse": bootstrap_mean_ci(rr), "correct_reuse": bootstrap_mean_ci(cr),
                    "incorrect_reuse": bootstrap_mean_ci(ir),
                    "reuse_precision": bootstrap_mean_ci(prec) if prec else None}

    # --- Claim C: does *early* library health predict *later* TC? ---
    # LH_pre = mean of the 4 LH sub-metrics set by gap/variant behaviour
    #          (reuse, 1-redundancy, quality-gate precision, utilization);
    # TC_late = mean pass rate on the compose + regress tasks of the same session.
    # This is the predictive question; a strong correlation would make LH a TC proxy.
    lh_pre, tc_late = [], []
    for r in rows:
        bt = r.get("task_completion_by_type", {})
        if "compose" not in bt or "regress" not in bt:
            continue
        lh_pre.append(np.mean([
            r["reuse_rate"], 1 - r["redundancy_rate"],
            r.get("library_precision", 0.0), r.get("creation_efficiency", 0.0),
        ]))
        tc_late.append(np.mean([bt["compose"], bt["regress"]]))
    corr = {"definition": "LH_pre (reuse, 1-redundancy, precision, utilization) vs "
                          "TC_late (mean of compose+regress pass rate), per session",
            "pearson": corr_with_ci(lh_pre, tc_late, "pearson"),
            "spearman": corr_with_ci(lh_pre, tc_late, "spearman")}

    report = {"n_sessions": len(rows), "n_boot": N_BOOT, "seed": 20260604,
              "claim_A_lh_contrasts": lh, "claim_B_reuse": reuse,
              "claim_C_lh_tc_correlation": corr}
    (results_dir / "statistical_report.json").write_text(json.dumps(report, indent=2))

    # --- LaTeX table for Claim A ---
    out = pathlib.Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    tl = [r"\begin{table}[t]", r"\centering\small",
          r"\caption{Library-health contrasts (Sonnet, $n{=}4$ seeds $\times$ 9 sessions). "
          r"Paired hierarchical bootstrap over (seed, session), 10k resamples; "
          r"BH-adjusted bootstrap $p$. Generated by \texttt{scripts/stats\_report.py}.}",
          r"\label{tab:lh_stats}", r"\begin{tabular}{lccc}", r"\toprule",
          r"\textbf{Contrast (LH)} & \textbf{$\Delta$} & \textbf{95\% CI} & \textbf{$p_{\mathrm{adj}}$} \\",
          r"\midrule"]
    for (a, b) in contrasts:
        d = lh[f"{a}_vs_{b}"]
        sig = "" if d["ci95"][0] <= 0 <= d["ci95"][1] else r"$^{*}$"
        tl.append(f"{LABEL[a]} $-$ {LABEL[b]} & {d['mean_diff']*100:.1f}{sig} & "
                  f"[{d['ci95'][0]*100:.1f}, {d['ci95'][1]*100:.1f}] & {d['p_adj_bh']:.3f} \\\\")
    tl += [r"\bottomrule", r"\end{tabular}",
           r"\\[2pt]\footnotesize $^{*}$95\% CI excludes 0. LH in percentage points.",
           r"\end{table}"]
    (out / "auto_stats_table.tex").write_text("\n".join(tl))

    # console summary
    print(f"n_sessions={len(rows)}")
    print("Claim A (LH contrasts):")
    for k, d in lh.items():
        print(f"  {k:28s} d={d['mean_diff']*100:+.1f}pp CI=[{d['ci95'][0]*100:.1f},{d['ci95'][1]*100:.1f}] p_adj={d['p_adj_bh']:.3f}")
    print("Claim C (LH~TC): "
          f"Pearson r={corr['pearson']['r']:.3f} CI{corr['pearson']['ci95']} equiv0.25={corr['pearson']['equiv_025']}; "
          f"Spearman rho={corr['spearman']['r']:.3f} CI{corr['spearman']['ci95']} equiv0.25={corr['spearman']['equiv_025']}")
    print(f"Wrote statistical_report.json and {out/'auto_stats_table.tex'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
