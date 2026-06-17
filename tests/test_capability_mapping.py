"""Tests for capability-aligned hidden-test mapping and runner propagation."""
from evolvetool_bench.harness.runner import AgentSystem, run_session
from evolvetool_bench.types import Session, Task, TaskType, ToolRecord


class StubSystem(AgentSystem):
    """Minimal agent; optionally creates one tool on GAP tasks."""

    def __init__(self, create_on_gap: bool = False, capability: str | None = None):
        self._create = create_on_gap
        self._cap = capability

    def setup(self, seed_tools: list[dict]) -> None:
        pass

    def run_task(self, task_description: str) -> dict:
        tools = []
        if self._create:
            tools = [
                {
                    "name": "tool_x",
                    "implementation": "def f(x):\n    return x",
                    "test_suite": "",
                },
            ]
        return {
            "output": "x",
            "tools_created": tools,
            "tools_used": [],
            "llm_calls": 1,
        }

    def get_library(self) -> list[dict]:
        return []


def test_toolrecord_carries_capability():
    record = ToolRecord(
        name="parse_tool",
        implementation="def parse(): pass",
        test_suite="",
        created_at_task="dt1_t4",
        capability_id="parse_abr",
        source_task_id="dt1_t4",
    )
    assert record.capability_id == "parse_abr"
    assert record.source_task_id == "dt1_t4"


def test_task_capability_field():
    task = Task(
        id="t1",
        description="decode records",
        task_type=TaskType.GAP,
        capability_id="parse_abr",
    )
    assert task.capability_id == "parse_abr"


def test_runner_propagates_capability():
    task_id = "gap_cap"
    session = Session(
        id="cap_propagation",
        name="Capability propagation",
        domain="test",
        tasks=[
            Task(
                id=task_id,
                description="Create a tool for capability cap_x",
                task_type=TaskType.GAP,
                capability_id="cap_x",
            ),
        ],
    )
    result = run_session(
        StubSystem(create_on_gap=True),
        session,
        verbose=False,
    )
    assert len(result.tools_created) == 1
    tool = result.tools_created[0]
    assert tool.capability_id == "cap_x"
    assert tool.source_task_id == task_id
