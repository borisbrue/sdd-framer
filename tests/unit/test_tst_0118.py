# TST-0118 – Ausführungsort von Tasks (Unit)
# Spec: SPEC-0026 | Contract: CON-0099 (v0.2.0)
#
# Bis #113 prüfte diese Datei ein hier definiertes MockContainerRuntime. Die
# Tests dagegen konnten nicht rot werden, wenn Produktionscode kaputtgeht. Jetzt
# übt jeder Test Produktionscode aus: TaskLifecycle, Task-Serialisierung und
# DistributionOrchestrator.
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from sdd_cli.dist_orchestrator import DistributionOrchestrator
from sdd_cli.llm_pool import CostTier, LlmEntry, LlmPoolRegistry, LlmType
from sdd_cli.task_lifecycle import InvalidTransitionError, TaskLifecycle
from sdd_cli.task_model import Complexity, ContextSize, Task, TaskStatus, TaskType


def _task(title="T") -> Task:
    return Task(
        spec_id="SPEC-0026", title=title, description="",
        type=TaskType.CODE, complexity=Complexity.LOW,
        context_size=ContextSize.S, estimated_tokens=500,
    )


class TestTST0118:
    def test_start_running_haelt_ausfuehrungsort_fest(self):
        """G-01: Status und container_id gehen gemeinsam über."""
        t = _task()
        lc = TaskLifecycle(t)
        lc.assign("llm-1")
        lc.start_running("local")
        assert t.status == TaskStatus.RUNNING
        assert t.container_id == "local"

    def test_kein_ausfuehrungsort_ohne_running(self):
        """INV-01: Ein verbotener Übergang hinterlässt keinen container_id."""
        t = _task()
        with pytest.raises(InvalidTransitionError):
            TaskLifecycle(t).start_running("local")
        assert t.status == TaskStatus.PENDING
        assert t.container_id is None

    def test_ausfuehrungsort_uebersteht_speichern_und_laden(self):
        """G-04"""
        t = _task()
        lc = TaskLifecycle(t)
        lc.assign("llm-1")
        lc.start_running("local")
        geladen = Task.from_dict(t.to_dict())
        assert geladen.container_id == "local"
        assert geladen.status == TaskStatus.RUNNING

    def test_distribute_fuehrt_tasks_lokal_aus(self, tmp_path):
        """G-02: container_id ist "local", eine Task-Container-Runtime gibt es nicht."""
        cfg = MagicMock()
        cfg.root = tmp_path
        registry = LlmPoolRegistry([
            LlmEntry("local", LlmType.LOCAL, "ollama", CostTier.CHEAP, 100000)
        ])
        gesehen: dict[str, tuple[TaskStatus, str | None]] = {}

        def review(task, commit_fn=None):
            gesehen[task.title] = (task.status, task.container_id)
            return False  # nichts committed -> keine Finalisierung

        pipeline = MagicMock()
        pipeline.run.side_effect = review
        tasks = [_task("A"), _task("B")]
        with patch("sdd_cli.dist_orchestrator._git",
                   return_value=MagicMock(returncode=0, stdout="")), \
             patch("sdd_cli.dist_orchestrator.ReviewPipeline", return_value=pipeline):
            DistributionOrchestrator(cfg, registry, work_dir=tmp_path).run("SPEC-0026", tasks)

        assert gesehen == {
            "A": (TaskStatus.RUNNING, "local"),
            "B": (TaskStatus.RUNNING, "local"),
        }
