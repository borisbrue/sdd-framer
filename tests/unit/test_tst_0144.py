# TST-0144 – Contract-Test: GET /api/specs/{spec_id}/tasks (CON-0123)
# Spec: SPEC-0034 · Contract: CON-0123
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "tool"))


class TestTST0144:
    def test_tasks_response_schema_no_run(self, tmp_path):
        """GET /tasks ohne laufenden Run gibt korrektes Schema zurück (INV-04)."""
        from sdd_cli.task_store import TaskStore
        store = TaskStore(tmp_path)
        run_id, tasks = store.load_latest("SPEC-0034")
        assert run_id is None
        assert tasks == []

    def test_tasks_response_schema_with_run(self, tmp_path):
        """GET /tasks mit Run gibt vollständige Task-Dicts zurück (G-01)."""
        from sdd_cli.task_store import TaskStore
        from sdd_cli.task_model import Task, TaskType, Complexity, ContextSize

        store = TaskStore(tmp_path)
        task = Task(
            spec_id="SPEC-0034",
            title="Test-Task",
            description="Beschreibung",
            type=TaskType.CODE,
            complexity=Complexity.MEDIUM,
            context_size=ContextSize.M,
            estimated_tokens=1500,
            parallel_group="group-1",
            test_ids=["TST-0144"],
        )
        store.save("SPEC-0034", "run-001", [task])
        run_id, loaded = store.load_latest("SPEC-0034")
        assert run_id == "run-001"
        assert len(loaded) == 1
        t = loaded[0]
        assert t.spec_id == "SPEC-0034"
        assert t.estimated_tokens == 1500
        assert t.parallel_group == "group-1"
        assert t.test_ids == ["TST-0144"]
        assert t.actual_tokens is None  # INV-02

    def test_task_inv01_estimated_tokens_positive(self, tmp_path):
        """INV-01: estimated_tokens > 0."""
        from sdd_cli.task_store import TaskStore
        from sdd_cli.task_model import Task, TaskType, Complexity, ContextSize

        store = TaskStore(tmp_path)
        task = Task(
            spec_id="SPEC-0034",
            title="T",
            description="",
            type=TaskType.CODE,
            complexity=Complexity.LOW,
            context_size=ContextSize.S,
            estimated_tokens=1,
        )
        store.save("SPEC-0034", "run-001", [task])
        _, loaded = store.load_latest("SPEC-0034")
        assert loaded[0].estimated_tokens > 0

    def test_task_inv05_latest_run_returned(self, tmp_path):
        """INV-05: immer neuester Run (höchste run_id)."""
        from sdd_cli.task_store import TaskStore
        from sdd_cli.task_model import Task, TaskType, Complexity, ContextSize

        store = TaskStore(tmp_path)
        def _t(title):
            return Task(
                spec_id="SPEC-0034", title=title, description="",
                type=TaskType.CODE, complexity=Complexity.LOW,
                context_size=ContextSize.S, estimated_tokens=100,
            )
        store.save("SPEC-0034", "run-001", [_t("old")])
        store.save("SPEC-0034", "run-002", [_t("new")])
        run_id, tasks = store.load_latest("SPEC-0034")
        assert run_id == "run-002"
        assert tasks[0].title == "new"

    def test_task_dict_schema_completeness(self, tmp_path):
        """G-01: Task-Dict enthält alle geforderten Felder aus CON-0123."""
        from sdd_cli.task_model import Task, TaskType, Complexity, ContextSize

        t = Task(
            spec_id="SPEC-0034", title="T", description="D",
            type=TaskType.TEST, complexity=Complexity.HIGH,
            context_size=ContextSize.L, estimated_tokens=2000,
            parallel_group="g1", test_ids=["TST-0001"],
        )
        d = t.to_dict()
        required_fields = {
            "id", "title", "description", "type", "status",
            "complexity", "context_size", "estimated_tokens",
            "actual_tokens", "llm_id", "parallel_group",
            "dependencies", "test_ids", "error_context",
        }
        for field in required_fields:
            assert field in d, f"Pflichtfeld fehlt: {field}"

    def test_task_event_bus_publish_subscribe(self):
        """CON-0123 INV-08: task_update-Event enthält run_id und timestamp."""
        import asyncio
        from sdd_cli.task_event_bus import TaskEventBus
        from sdd_cli.task_model import Task, TaskType, Complexity, ContextSize

        bus = TaskEventBus()
        task = Task(
            spec_id="SPEC-0034", title="T", description="",
            type=TaskType.CODE, complexity=Complexity.LOW,
            context_size=ContextSize.S, estimated_tokens=100,
        )

        async def run():
            queue = bus.subscribe("SPEC-0034")
            bus.publish("SPEC-0034", "run-001", task.to_dict())
            event_type, payload = await asyncio.wait_for(queue.get(), timeout=1.0)
            return event_type, payload

        event_type, payload = asyncio.run(run())
        assert event_type == "task_update"
        assert "run_id" in payload
        assert "timestamp" in payload
        assert "task" in payload
        assert payload["run_id"] == "run-001"
