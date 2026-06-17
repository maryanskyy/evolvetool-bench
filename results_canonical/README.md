# Canonical strict-subset results

This directory contains the canonical artifacts used by the KDD Eval 2026 workshop submission.

- `run_manifest.jsonl`: session-level strict verified-subset rows for 5 protocols x 3 seeds x 8 sessions = 120 rows.
- `aggregate.json`: system-level aggregates used in the main results table.
- `claims.json`: pre-specified task-completion contrasts with confidence intervals.
- `tool_manifest.jsonl`: system-level tool/reuse summaries for the strict pilot.
- `audit_report.json`: scope and verifier-coverage accounting.

The strict pilot excludes unverified tasks from task-completion claims. API orchestration remains part of the benchmark design but is not included in the main strict TC denominator until deterministic verifiers are complete. Per-tool hidden conformance results are intentionally not headlined in this submission.
