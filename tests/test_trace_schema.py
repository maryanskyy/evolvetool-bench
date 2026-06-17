"""Tests for per-task trace and session summary schema."""
from dataclasses import fields

from evolvetool_bench.types import SessionResult, TaskResult, TaskType, ToolRecord


def test_task_result_fields():
    names = {f.name for f in fields(TaskResult)}
    required = {
        "task_id",
        "task_type",
        "passed",
        "tool_created",
        "tools_used",
        "tool_reused",
        "tool_reused_correctly",
        "llm_calls",
        "duration_ms",
        "agent_output",
    }
    assert required <= names


def test_session_summary_keys():
    result = SessionResult(session_id="schema_test")
    result.task_results = [
        TaskResult(task_id="1", task_type=TaskType.SEED, passed=True, llm_calls=1),
    ]
    summary = result.summary()
    required_keys = {
        "session_id",
        "task_completion",
        "tools_created",
        "mean_tool_quality",
        "reuse_rate",
        "correct_reuse_rate",
        "incorrect_reuse_rate",
        "redundancy_rate",
        "library_health",
        "evolvetool_score",
        "safety_score",
    }
    assert required_keys <= set(summary.keys())
    assert summary["safety_score"] == "not_implemented"


def test_ets_excludes_safety():
    result = SessionResult(session_id="ets_test")
    result.task_results = [
        TaskResult(
            task_id="1",
            task_type=TaskType.SEED,
            passed=True,
            llm_calls=2,
        ),
        TaskResult(
            task_id="2",
            task_type=TaskType.GAP,
            passed=False,
            llm_calls=3,
        ),
    ]
    # Do not set safety_score; ETS should still compute from other axes
    score = result.evolvetool_score
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0
    assert result.summary()["safety_score"] == "not_implemented"


def test_toolrecord_lineage_fields():
    record = ToolRecord(
        name="t",
        implementation="",
        test_suite="",
        created_at_task="task_1",
    )
    assert record.capability_id is None
    assert record.source_task_id is None
