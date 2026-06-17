"""Audit verifier coverage across benchmark sessions."""
from __future__ import annotations

import importlib

from evolvetool_bench.harness.runner import AgentSystem, run_session
from evolvetool_bench.types import Session, Task, TaskType

# All create_session() factories (9 sessions)
_SESSION_MODULES = [
    "evolvetool_bench.domains.data_transform.session_1",
    "evolvetool_bench.domains.data_transform.session_2",
    "evolvetool_bench.domains.data_transform.session_3",
    "evolvetool_bench.domains.data_transform.session_4",
    "evolvetool_bench.domains.data_transform.session_5",
    "evolvetool_bench.domains.numerical.session_1",
    "evolvetool_bench.domains.numerical.session_2",
    "evolvetool_bench.domains.numerical.session_3",
    "evolvetool_bench.domains.api_orchestration.session_1",
]

_DATA_TRANSFORM_MODULES = _SESSION_MODULES[:5]


def _load_all_sessions():
    sessions = []
    for mod_path in _SESSION_MODULES:
        mod = importlib.import_module(mod_path)
        sessions.append(mod.create_session())
    return sessions


class StubSystem(AgentSystem):
    """Minimal agent that returns fixed output without verification."""

    def setup(self, seed_tools: list[dict]) -> None:
        pass

    def run_task(self, task_description: str) -> dict:
        return {
            "output": "x",
            "tools_created": [],
            "tools_used": [],
            "llm_calls": 1,
        }

    def get_library(self) -> list[dict]:
        return []


def test_all_sessions_load():
    for session in _load_all_sessions():
        assert len(session.tasks) == 11


def test_task_types_present():
    valid_types = set(TaskType)
    for session in _load_all_sessions():
        types = [t.task_type for t in session.tasks]
        assert TaskType.GAP in types
        for t in types:
            assert t in valid_types


def test_verifier_coverage_reported(capsys):
    total_verified = 0
    for session in _load_all_sessions():
        verified = sum(
            1 for t in session.tasks
            if t.expected is not None or t.verify is not None
        )
        total_verified += verified
        total = len(session.tasks)
        ratio = verified / total if total else 0.0
        print(f"{session.id}: {verified}/{total} verified ({ratio:.2%})")

    # Tracked deterministic-verifier coverage (expected mappings or verify predicates).
    # Update when adding verifiers; confirm with: python scripts/audit_tasks.py
    assert total_verified == 51

    for mod_path in _DATA_TRANSFORM_MODULES:
        mod = importlib.import_module(mod_path)
        session = mod.create_session()
        gap_tasks = [t for t in session.tasks if t.task_type == TaskType.GAP]
        assert gap_tasks, f"{session.id} has no GAP tasks"
        for task in gap_tasks:
            assert task.hidden_tests, (
                f"{session.id} GAP task {task.id} missing hidden_tests"
            )


def test_unverified_tasks_fail_closed():
    session = Session(
        id="unverified_stub",
        name="Unverified stub",
        domain="test",
        tasks=[
            Task(
                id="gap_unverified",
                description="GAP with no verifier or expected output",
                task_type=TaskType.GAP,
            ),
        ],
    )
    result = run_session(StubSystem(), session, verbose=False)
    assert len(result.task_results) == 1
    assert result.task_results[0].passed is False
