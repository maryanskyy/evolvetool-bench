# EvolveTool-Bench

**A diagnostic framework for evaluating evolving LLM-generated tool libraries as auditable software artifacts.**

EvolveTool-Bench evaluates agents that create and accumulate tools at runtime. The benchmark does not only ask whether the agent solved the immediate task; it also asks what happened to the persistent tool library the agent left behind.

## What the benchmark diagnoses

| Question | Metric / artifact |
|----------|-------------------|
| Did the agent solve the task? | Verified task completion (TC) |
| Was the task actually verified? | Verifier coverage and unverified-task accounting |
| Did the agent create reusable artifacts? | Tools created and artifact summaries |
| Did reuse help or hurt? | Correct reuse vs. incorrect reuse |
| Is the library accumulating duplicates? | Redundancy diagnostics |
| Are created tools used later? | Utilization |
| Can tools be chained across tasks? | Composition success |
| Did library growth break earlier behavior? | Regression probes |
| Can the run be inspected? | Audit traces and summary manifests |

The contribution is a diagnostic methodology and a set of reusable evaluation practices, not a leaderboard.

## Current evidence status

The full benchmark design contains **3 domains, 9 sessions, and 99 tasks**. The current strict submission analysis is intentionally narrower: it covers the deterministically verified subset, currently **8 sessions and 51 verified task decisions per system pass**. The API-orchestration session remains part of the benchmark design, but it is excluded from the main strict TC denominator until its deterministic verifiers are complete.

Unverified tasks are not credited as successes. In the strict analysis, they are reported separately and excluded from task-completion claims. This is a measurement-validity choice: it is better to report a smaller verified result than to inflate TC with plausible but unchecked outputs.

## Key finding from the strict pilot

The strict verified-subset pilot does **not** establish task-completion superiority for any tool-creation protocol. That is the point of the pivot: task completion alone is not a sufficient trustworthiness metric for tool-evolving agents.

The benchmark remains useful because it exposes artifact-level behavior that TC does not show: how many tools were created, whether they were reused, whether reuse coincided with success or failure, and whether the run can be audited from summary manifests and, in future full releases, per-task traces.

## Strict pilot table

| System | TC | SE | Tools created | Reuse precision |
|--------|----|----|---------------|-----------------|
| One-Shot | 0.358 | 0.077 | 114 | 0.333 |
| No-Evolution | 0.337 | 0.064 | 0 | 0.333 |
| EvoSkill-style | 0.332 | 0.062 | 0 | 0.250 |
| ToolMaker-style | 0.292 | 0.054 | 18 | 0.375 |
| CREATOR-style | 0.287 | 0.048 | 111 | 0.333 |

Means and standard errors are over 24 session rows per system (3 seeds x 8 verified-subset sessions) using Claude Haiku 4.5.

## Benchmark structure

Each session contains 11 tasks with known dependency relationships:

| Task type | What it diagnoses |
|-----------|------------------|
| Seed (x3) | Can the agent use provided tools? |
| Gap (x2) | Can it create a missing capability? |
| Variant (x2) | Does it reuse or duplicate? |
| Compose (x1) | Can it chain self-created tools? |
| Regress (x1) | Did library growth break prior behavior? |
| Adversarial (x2) | Does the tool handle edge cases? |

## Reusable evaluation practices

EvolveTool-Bench is intended less as a fixed leaderboard than as a set of reusable evaluation practices. We recommend that future benchmarks for tool-evolving agents:

1. separate task success from generated-artifact behavior;
2. report verifier coverage and exclude unverified tasks from TC claims;
3. report correct and incorrect reuse rather than raw reuse alone;
4. include explicit regression tasks after library growth;
5. preserve generated artifacts, summaries, and source hashes when available;
6. publish task/session traces sufficient to reproduce decisions;
7. evaluate library-management policies such as promotion, deduplication, and retirement.

## Quick start

```bash
pip install -e ".[dev]"

# Audit verifier coverage.
python scripts/audit_tasks.py

# Regenerate paper tables from canonical results.
python scripts/build_from_run.py --input results_strict_run --output results_canonical/
# or use the included canonical strict-subset tables in paper/kdd_eval2026/.
```

## Citation

```bibtex
@inproceedings{anonymous2026evolvetoolbench,
  title     = {Beyond Task Completion: Auditing Evolving Tool Libraries in Agentic AI},
  author    = {Anonymous},
  booktitle = {Workshop on Evaluation and Trustworthiness of Agentic AI at KDD 2026},
  year      = {2026}
}
```

## License

MIT
