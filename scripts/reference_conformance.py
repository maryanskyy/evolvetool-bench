#!/usr/bin/env python3
"""Calibration check: hand-written reference implementations vs. conformance suites.

For every gap-task capability in the verified subset (16 capabilities across
8 sessions), evaluate the released hand-written reference implementation
against the same held-out conformance suite (hidden + adversarial tests) used
to score agent-synthesised tools. If a correct implementation exists that
scores C=1.00 on every suite, the suites are passable and the silent-rot rate
reported in the paper is a property of the synthesised tools, not of the tests.

Usage:
    python scripts/reference_conformance.py [--out reference_conformance.json]

No LLM calls; runs in seconds.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from evolvetool_bench.types import ToolRecord  # noqa: E402
from evolvetool_bench.evaluation.tool_quality import evaluate_tool  # noqa: E402

from evolvetool_bench.baselines.reference.data_transform_s1_s2 import (  # noqa: E402
    REFERENCE_IMPLS as R12,
)
from evolvetool_bench.baselines.reference.data_transform_s3_s4 import (  # noqa: E402
    REFERENCE_IMPLS as R34,
)
from evolvetool_bench.baselines.reference.data_transform_s5 import (  # noqa: E402
    REFERENCE_IMPLS as R5,
)
from evolvetool_bench.baselines.reference.numerical_s1_s2 import (  # noqa: E402
    REFERENCE_IMPLS as RN12,
)
from evolvetool_bench.baselines.reference.numerical_s3 import (  # noqa: E402
    REFERENCE_IMPLS as RN3,
)

from evolvetool_bench.domains.data_transform import (  # noqa: E402
    session_1 as dt_s1, session_2 as dt_s2, session_3 as dt_s3,
    session_4 as dt_s4, session_5 as dt_s5,
)
from evolvetool_bench.domains.numerical import (  # noqa: E402
    session_1 as num_s1, session_2 as num_s2, session_3 as num_s3,
)

ALL_IMPLS: dict[str, dict] = {**R12, **R34, **R5, **RN12, **RN3}

SESSIONS = {
    f().id: f()
    for f in [
        dt_s1.create_session, dt_s2.create_session, dt_s3.create_session,
        dt_s4.create_session, dt_s5.create_session,
        num_s1.create_session, num_s2.create_session, num_s3.create_session,
    ]
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reference_conformance.json")
    args = ap.parse_args()

    rows = []
    for cap_id, spec in sorted(ALL_IMPLS.items()):
        session = SESSIONS[spec["session_id"]]
        task = next(t for t in session.tasks if t.id == spec["task_id"])
        tool = ToolRecord(
            name=spec["name"],
            implementation=spec["implementation"],
            test_suite="",
            created_at_task=spec["task_id"],
            capability_id=cap_id,
        )
        evaluate_tool(tool, task.hidden_tests or [], task.adversarial_tests or [])
        rows.append({
            "capability_id": cap_id,
            "session_id": spec["session_id"],
            "task_id": spec["task_id"],
            "name": spec["name"],
            "n_hidden": len(task.hidden_tests or []),
            "n_adversarial": len(task.adversarial_tests or []),
            "correctness": tool.correctness,
            "robustness": tool.robustness,
            "generality": tool.generality,
            "code_quality": tool.code_quality,
        })
        print(f"{cap_id:28s} {spec['session_id']:20s} "
              f"C={tool.correctness:.2f} R={tool.robustness:.2f} G={tool.generality:.2f}")

    n_perfect = sum(1 for r in rows if r["correctness"] == 1.0)
    summary = {
        "n_capabilities": len(rows),
        "n_reference_at_c_1": n_perfect,
        "all_pass": n_perfect == len(rows),
        "rows": rows,
    }
    with open(args.out, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n{n_perfect}/{len(rows)} reference implementations at C=1.00 "
          f"-> {args.out}")
    return 0 if summary["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
