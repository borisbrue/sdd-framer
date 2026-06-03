# TST-0145 – Acceptance-Tests: Task-Completion-Gate (CON-0124, SPEC-0034 FR-04/FR-05)
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "tool"))

from sdd_cli.task_model import Task, TaskStatus, TaskType, Complexity, ContextSize
from sdd_cli.task_lifecycle import TaskLifecycle, TaskTestRequiredError


def _task_in_review(**kwargs) -> Task:
    t = Task(
        spec_id="SPEC-0034",
        title="T",
        description="",
        type=TaskType.CODE,
        complexity=Complexity.LOW,
        context_size=ContextSize.S,
        estimated_tokens=100,
        **kwargs,
    )
    t.status = TaskStatus.REVIEW
    return t


def _runner(success: bool, output: str = "") -> MagicMock:
    r = MagicMock()
    r.run.return_value = (success, output)
    return r


class TestTST0145:
    def test_passed_transition_with_passing_test(self):
        """Szenario: Passed-Transition mit grünem Test (CON-0124 G-01)."""
        task = _task_in_review(test_ids=["TST-0001"])
        lc = TaskLifecycle(task, runner=_runner(True), enforce_test_gate=True)
        lc.mark_passed()
        assert task.status == TaskStatus.PASSED
        assert task.error_context == []

    def test_passed_transition_with_failing_test(self):
        """Szenario: Passed-Transition mit fehlgeschlagenem Test (CON-0124 G-02)."""
        task = _task_in_review(test_ids=["TST-0001"])
        lc = TaskLifecycle(task, runner=_runner(False, "AssertionError: expected 200, got 500"), enforce_test_gate=True)
        lc.mark_passed()
        assert task.status == TaskStatus.FAILED
        assert any("AssertionError" in e for e in task.error_context)

    def test_passed_transition_without_test_ids_blocked(self):
        """Szenario: Passed-Transition ohne test_ids blockiert (CON-0124 INV-01)."""
        task = _task_in_review(test_ids=[])
        lc = TaskLifecycle(task, runner=_runner(True), enforce_test_gate=True)
        with pytest.raises(TaskTestRequiredError):
            lc.mark_passed()
        assert task.status == TaskStatus.REVIEW  # unverändert
        assert any("Kein Test zugewiesen" in e for e in task.error_context)

    def test_passed_transition_multiple_tests_one_fails(self):
        """Szenario: Mehrere Tests – einer fehlschlägt → failed (CON-0124 INV-02)."""
        task = _task_in_review(test_ids=["TST-0001", "TST-0002"])
        runner = MagicMock()
        runner.run.side_effect = [
            (True, "ok"),
            (False, "TimeoutError"),
        ]
        lc = TaskLifecycle(task, runner=runner, enforce_test_gate=True)
        lc.mark_passed()
        assert task.status == TaskStatus.FAILED
        assert any("TimeoutError" in e for e in task.error_context)

    def test_passed_transition_multiple_tests_all_pass(self):
        """Szenario: Mehrere Tests – alle grün → passed (CON-0124 INV-02)."""
        task = _task_in_review(test_ids=["TST-0001", "TST-0002"])
        runner = MagicMock()
        runner.run.side_effect = [(True, "ok"), (True, "ok")]
        lc = TaskLifecycle(task, runner=runner, enforce_test_gate=True)
        lc.mark_passed()
        assert task.status == TaskStatus.PASSED

    def test_error_context_contains_test_failure_message(self):
        """CON-0124 INV-03: error_context enthält originale Fehlermeldung."""
        task = _task_in_review(test_ids=["TST-0001"])
        lc = TaskLifecycle(task, runner=_runner(False, "SyntaxError: invalid syntax\nFAILED"), enforce_test_gate=True)
        lc.mark_passed()
        assert len(task.error_context) > 0

    def test_task_store_persist_and_load(self, tmp_path):
        """FR-03: Tasks persistieren in .sdd/runs/{spec_id}/{run_id}/tasks.json."""
        from sdd_cli.task_store import TaskStore
        store = TaskStore(tmp_path)
        task = Task(
            spec_id="SPEC-0034", title="Persist-Test", description="",
            type=TaskType.CODE, complexity=Complexity.LOW,
            context_size=ContextSize.S, estimated_tokens=500,
            parallel_group="g1", test_ids=["TST-0145"],
        )
        store.save("SPEC-0034", "run-test", [task])
        run_id, loaded = store.load("SPEC-0034", "run-test"), "run-test"
        assert len(store.load("SPEC-0034", "run-test")) == 1
        loaded_task = store.load("SPEC-0034", "run-test")[0]
        assert loaded_task.title == "Persist-Test"
        assert loaded_task.parallel_group == "g1"

    def test_sse_bus_run_started_event(self):
        """FR-02: SSE-Stream sendet run_started-Event (CON-0123 INV-08)."""
        import asyncio
        from sdd_cli.task_event_bus import TaskEventBus

        bus = TaskEventBus()

        async def run():
            queue = bus.subscribe("SPEC-0034")
            bus.publish_run_started("SPEC-0034", "run-sse-001")
            event_type, payload = await asyncio.wait_for(queue.get(), timeout=1.0)
            return event_type, payload

        event_type, payload = asyncio.run(run())
        assert event_type == "run_started"
        assert payload["run_id"] == "run-sse-001"
        assert payload["spec_id"] == "SPEC-0034"
        assert "timestamp" in payload
