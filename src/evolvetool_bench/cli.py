"""CLI entry point for EvolveTool-Bench."""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="evolvetool",
        description="EvolveTool-Bench: diagnostic evaluation of evolving tool libraries.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="Run a benchmark session against a system")
    run_p.add_argument("--system", required=True, help="System name: arise|no_evolution|creator|oneshot|toolmaker|toolcoder")
    run_p.add_argument("--domain", default="all", help="Domain: data_transform|numerical|api_orchestration|all")
    run_p.add_argument("--model", default="claude-haiku-4-5", help="Anthropic model ID")
    run_p.add_argument("--output", default="results_canonical/", help="Output directory")
    run_p.add_argument("--seed", type=int, default=42, help="Random seed")
    run_p.add_argument("--verbose", action="store_true")

    audit_p = sub.add_parser("audit", help="Audit tasks or results")
    audit_p.add_argument("target", choices=["tasks", "results"], help="What to audit")
    audit_p.add_argument("--results-dir", default="results_canonical/", help="Results directory to audit")

    args = parser.parse_args(argv)

    if args.cmd == "run":
        print(f"[evolvetool run] system={args.system} domain={args.domain} model={args.model}")
        print("Use run_benchmark.py directly for full runs (CLI stub — full harness integration pending).")
        return 0

    if args.cmd == "audit":
        if args.target == "tasks":
            from scripts.audit_tasks import main as audit_tasks_main
            return audit_tasks_main()
        else:
            print(f"Auditing results in {args.results_dir} (stub — run scripts/audit_results.py directly).")
            return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
