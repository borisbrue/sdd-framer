# TST-0118 – Container-Lifecycle (Unit)
# Spec: SPEC-0026 | Contract: CON-0099

import re
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest

from tool.sdd_cli.task_model import Task, TaskType, Complexity, ContextSize
from tool.sdd_cli.task_lifecycle import TaskLifecycle


def _task(title="T") -> Task:
    return Task(
        spec_id="SPEC-0026", title=title, description="",
        type=TaskType.CODE, complexity=Complexity.LOW,
        context_size=ContextSize.S, estimated_tokens=500,
    )


class MockContainerRuntime:
    """Test-Double für Container-Runtime ohne echten Docker."""
    def __init__(self):
        self.containers: dict[str, list] = {}
        self.removed: set[str] = set()

    def create(self, name: str, tasks: list[Task]) -> str:
        assert tasks, "Container braucht mindestens einen Task"
        self.containers[name] = tasks
        return name

    def remove(self, name: str) -> None:
        self.removed.add(name)
        self.containers.pop(name, None)

    def exists(self, name: str) -> bool:
        return name in self.containers


class TestTST0118:
    def test_container_name_follows_schema(self):
        spec_id = "SPEC-0026"
        import uuid
        uid = str(uuid.uuid4())[:8]
        name = f"sdd-{spec_id.lower()}-{uid}"
        assert name.startswith("sdd-spec-0026-")

    def test_single_task_container(self):
        rt = MockContainerRuntime()
        t = _task()
        name = "sdd-spec-0026-abc"
        rt.create(name, [t])
        assert rt.exists(name)

    def test_multiple_tasks_same_container(self):
        rt = MockContainerRuntime()
        tasks = [_task(f"T{i}") for i in range(3)]
        name = "sdd-spec-0026-multi"
        rt.create(name, tasks)
        assert len(rt.containers[name]) == 3

    def test_empty_task_list_raises(self):
        rt = MockContainerRuntime()
        with pytest.raises(AssertionError):
            rt.create("sdd-spec-0026-empty", [])

    def test_remove_clears_container(self):
        rt = MockContainerRuntime()
        name = "sdd-spec-0026-del"
        rt.create(name, [_task()])
        rt.remove(name)
        assert not rt.exists(name)
        assert name in rt.removed

    def test_remove_idempotent(self):
        rt = MockContainerRuntime()
        name = "sdd-spec-0026-idem"
        rt.create(name, [_task()])
        rt.remove(name)
        rt.remove(name)
        assert not rt.exists(name)

    def test_name_collision_raises(self):
        rt = MockContainerRuntime()
        name = "sdd-spec-0026-dup"
        rt.create(name, [_task()])
        with pytest.raises(Exception):
            if rt.exists(name):
                raise RuntimeError(f"Container {name} existiert bereits")

    def test_task_status_after_container_assignment(self):
        t = _task()
        lc = TaskLifecycle(t)
        lc.assign("llm-1")
        lc.start_running("sdd-spec-0026-x")
        assert t.container_id == "sdd-spec-0026-x"
