# In-regime conformance pass — strong-accept path for KDD 2026

This walks through producing the missing piece: an **in-regime** measurement of
the verification-vs-conformance gap on the Haiku strict pilot. The current
paper *illustrates* the gap with a separate-pilot trace; the steps below
produce strict-pilot Haiku traces with per-tool held-out conformance, which is
the single change that flips the paper from Accept to Strong Accept on the
external reviewer's rubric (Empirical Support: 5.5 → 7+).

## What's already done

- `scripts/run_strict.py` now preserves per-tool source under
  `<output>/tools/<system>/<session>/seed_<n>/<name>.py` + `.meta.json`.
  This mirrors the working `run_full_matrix.py` block (lines 86–108) so
  conformance replay does not require any LLM calls.
- `scripts/conformance_in_regime.py` walks that tree, runs each tool against
  the held-out hidden + adversarial inputs for the capability it was
  synthesised for, and emits `conformance_manifest.jsonl` plus
  `conformance_aggregate.json`.

Both are pushed to `main` and parse cleanly.

## What you (or Artem) need to do

### Step 1: pilot pass — one session, one system, one seed (~$1, ~5 min)

```bash
cd /Users/alibek/Desktop/Projects/evolvetool-bench
source .venv/bin/activate  # or your env
export ANTHROPIC_API_KEY=...
python scripts/run_strict.py \
    --systems creator \
    --seeds 0 \
    --pilot \
    --output results_inregime_pilot/
```

That runs CREATOR-style on `data_transform_s1` only, with one seed. The pilot
flag drops the run to ~5 minutes. CREATOR is the right system to start with
because it actually synthesises tools (114 in the full Haiku matrix), so
`tools/creator/data_transform_s1/seed_0/` will have several `.py` files to
score.

Expected output:

```
results_inregime_pilot/
├── run_manifest.jsonl            (1 row)
├── aggregate.json
└── tools/creator/data_transform_s1/seed_0/
    ├── decode_abr_format.py
    ├── decode_abr_format_tests.py
    └── decode_abr_format.meta.json
    ...
```

### Step 2: conformance replay — no LLM, ~10 seconds

```bash
python scripts/conformance_in_regime.py --canonical results_inregime_pilot/
```

This writes `results_inregime_pilot/conformance_manifest.jsonl` and
`conformance_aggregate.json`. Each per-tool row in the manifest has:

- `scores_in_session.correctness` — the in-session verifier score
- `conformance.correctness` — the held-out conformance correctness
- `conformance.robustness`, `.generality` — same on held-out inputs
- `n_hidden`, `n_adversarial` — how many held-out tests were run

The headline number per tool is the gap between `scores_in_session.correctness`
and `conformance.correctness`. Tools with `scores_in_session.correctness > 0`
and `conformance.correctness == 0.0` are *silent rot*: they pass their own
in-session tests and fail every held-out input.

The aggregate's `pct_silent_rot` is the fraction of CREATOR's preserved tools
that hit that pattern in-regime.

### Step 3: scale up if pilot looks healthy (optional, ~$30–60, ~few hours)

```bash
# Full strict matrix (~ same scope as Tables 3-4 in the paper but with source preservation)
python scripts/run_strict.py \
    --systems oneshot,creator,toolmaker \
    --seeds 0,1,2 \
    --output results_inregime_full/
python scripts/conformance_in_regime.py --canonical results_inregime_full/
```

This gives in-regime conformance for every preserved tool across the three
tool-creating systems on all 8 verified-subset sessions × 3 seeds. The
EvoSkill/no_evolution rows produce zero tools so are skipped.

## What to put in the paper after step 2

The single concrete change for Strong Accept:

1. Replace §5.3 "Illustrative trace" footnote disclaimer with an
   in-regime sentence: *"Across $N$ tools preserved from the CREATOR-style
   strict pilot at seed 0, $K$ pass session-level verifier calls while
   recording $C{=}0.00$ on the held-out conformance suite — the same silent-rot
   pattern as the design-motivating Sonnet trace, now measured in-regime."*
2. Promote the title back to *"A Verification-vs-Conformance Gap in
   Tool-Evolving Agents"* — now with empirical backing from the strict pilot.
3. Add a small table to §5.3: per-system `pct_silent_rot` from
   `conformance_aggregate.json`.

After step 3 (scale-up), §5.3 also gets a Δ-table: in-session correctness
mean vs held-out correctness mean per system, with paired CI.

## Cost & time summary

| Step              | LLM cost   | Time       | What it buys                                                  |
| ----------------- | ---------- | ---------- | ------------------------------------------------------------- |
| Step 1 (pilot)    | ~$1        | ~5 min     | At least one in-regime trace for §5.3 — flips title back      |
| Step 2 (replay)   | $0         | ~10 s      | conformance_manifest.jsonl + aggregate                        |
| Step 3 (full)     | ~$30–60    | ~few hours | Powered per-system silent-rot rates → §5.3 sub-table, Δ-table |

Step 1+2 is the minimum to push reviewer score Empirical Support from 5.5 to 7.
Step 3 is what makes it a clean main-conference benchmark submission.
