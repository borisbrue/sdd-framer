# TST-0143 | SPEC-0035 | CON-0122
# Fehler-Propagation: Sub-Agenten-Fehler hält Orchestrator an

from pathlib import Path
from unittest.mock import MagicMock

from tool.sdd_cli.config import SddConfig
from tool.sdd_cli.sub_agent import SubAgentOrchestrator
from tool.sdd_cli.task_model import Complexity, ContextSize, Task, TaskType


def _cfg(root: Path) -> SddConfig:
    """root muss ein tmp_path sein.

    Vorher stand hier Path("."), also das Arbeitsverzeichnis von pytest — der
    Orchestrator schrieb damit .sdd/evaluations.db des echten Repositories.
    """
    return SddConfig(root=root, raw={})


def _task(title: str, idx: int) -> Task:
    return Task(
        spec_id="SPEC-0035",
        title=title,
        description="",
        type=TaskType.CODE,
        complexity=Complexity.LOW,
        context_size=ContextSize.S,
        estimated_tokens=100,
        id=f"t{idx}",
    )


class TestTST0143:
    def _make_orchestrator(self, tmp_path: Path):
        return SubAgentOrchestrator(config=_cfg(tmp_path), spec_id="SPEC-0035")

    def test_tc01_task1_succeeds_before_failure(self, tmp_path) -> None:
        tasks = [_task("Task 1", 1), _task("Task 2", 2), _task("Task 3", 3)]
        call_counts = {"t1": 0, "t2": 0, "t3": 0}

        def spawn(task):
            call_counts[task.id] += 1
            if task.id == "t2":
                raise RuntimeError("Task 2 fehlgeschlagen")
            return MagicMock(usage=None)

        report = self._make_orchestrator(tmp_path).run(tasks, spawn)
        assert call_counts["t1"] == 1
        assert len(report.completed_tasks) == 1
        assert report.completed_tasks[0].task_id == "t1"

    def test_tc02_failing_task_retried_exactly_once(self, tmp_path) -> None:
        tasks = [_task("Task 2", 2)]
        call_count = [0]

        def spawn(task):
            call_count[0] += 1
            raise RuntimeError("fehlgeschlagen")

        self._make_orchestrator(tmp_path).run(tasks, spawn)
        assert call_count[0] == 2  # initial + 1 retry

    def test_tc03_subsequent_tasks_not_started_after_failure(self, tmp_path) -> None:
        tasks = [_task("Task 1", 1), _task("Task 2", 2), _task("Task 3", 3)]
        started = []

        def spawn(task):
            started.append(task.id)
            if task.id == "t2":
                raise RuntimeError("fehlgeschlagen")
            return MagicMock(usage=None)

        report = self._make_orchestrator(tmp_path).run(tasks, spawn)
        assert "t3" not in started
        assert report.halted is True

    def test_tc04_error_report_contains_task_id(self, tmp_path) -> None:
        tasks = [_task("Task 2", 2)]

        def spawn(task):
            raise RuntimeError("konkreter Fehler")

        report = self._make_orchestrator(tmp_path).run(tasks, spawn)
        assert report.failed_task is not None
        assert report.failed_task.task_id == "t2"
        assert report.failed_task.error is not None
        assert len(report.failed_task.error) > 0
