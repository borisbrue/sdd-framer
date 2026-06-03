# TST-0146 – Unit-Tests: parallel_group Dependency-Auflösung und Zirkel-Erkennung
# Spec: SPEC-0034 · Contract: CON-0124 (partial)
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "tool"))

from sdd_cli.decompose import detect_circular_dependencies
from sdd_cli.task_model import Task, TaskStatus, TaskType, Complexity, ContextSize


def _task(title: str, deps: list[str] | None = None, pg: str | None = None) -> Task:
    return Task(
        spec_id="SPEC-0034",
        title=title,
        description="",
        type=TaskType.CODE,
        complexity=Complexity.LOW,
        context_size=ContextSize.S,
        estimated_tokens=100,
        dependencies=deps or [],
        parallel_group=pg,
    )


class TestTST0146:
    def test_no_circular_dependencies(self):
        t1 = _task("A")
        t2 = _task("B", deps=["A"])
        result = detect_circular_dependencies([t1, t2])
        assert result == set()

    def test_direct_cycle_detected(self):
        t1 = _task("A", deps=["B"])
        t2 = _task("B", deps=["A"])
        result = detect_circular_dependencies([t1, t2])
        assert t1.id in result or t2.id in result

    def test_three_node_cycle_detected(self):
        t1 = _task("A", deps=["C"])
        t2 = _task("B", deps=["A"])
        t3 = _task("C", deps=["B"])
        result = detect_circular_dependencies([t1, t2, t3])
        assert len(result) > 0

    def test_independent_tasks_no_cycle(self):
        tasks = [_task(f"Task{i}") for i in range(5)]
        result = detect_circular_dependencies(tasks)
        assert result == set()

    def test_self_dependency_detected(self):
        t = _task("A", deps=["A"])
        result = detect_circular_dependencies([t])
        assert t.id in result

    def test_parallel_group_set_on_task(self):
        t = _task("A", pg="group-1")
        assert t.parallel_group == "group-1"

    def test_parallel_group_none_by_default(self):
        t = _task("A")
        assert t.parallel_group is None

    def test_task_model_new_fields_roundtrip(self):
        t = _task("X", pg="g1")
        t.test_ids = ["TST-0001"]
        t.actual_tokens = 500
        t.run_id = "run-001"
        d = t.to_dict()
        assert d["parallel_group"] == "g1"
        assert d["test_ids"] == ["TST-0001"]
        assert d["actual_tokens"] == 500
        assert d["run_id"] == "run-001"
        t2 = Task.from_dict(d)
        assert t2.parallel_group == "g1"
        assert t2.test_ids == ["TST-0001"]
        assert t2.actual_tokens == 500
        assert t2.run_id == "run-001"

    def test_circular_tasks_get_blocked_status(self):
        t1 = _task("A", deps=["B"])
        t2 = _task("B", deps=["A"])
        circular = detect_circular_dependencies([t1, t2])
        for task in [t1, t2]:
            if task.id in circular:
                task.status = TaskStatus.BLOCKED
                task.error_context.append("circular dependency detected")
        blocked = [t for t in [t1, t2] if t.status == TaskStatus.BLOCKED]
        assert len(blocked) >= 1
        assert any("circular dependency detected" in t.error_context for t in blocked)
