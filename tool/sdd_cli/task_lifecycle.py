"""TaskLifecycle – State Machine für Task-Zustandsübergänge (CON-0095, SPEC-0034).

State Pattern: Ungültige Übergänge sind strukturell unmöglich via ALLOWED_TRANSITIONS.
SPEC-0034 FR-05: mark_passed() erfordert grüne Tests (TaskTestRequiredError, CON-0124).
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Protocol

from .task_model import Task, TaskStatus


class TaskTestRequiredError(Exception):
    pass


class TestRunner(Protocol):
    def run(self, test_id: str, repo_root: Path) -> tuple[bool, str]:
        ...


class PytestTestRunner:
    def run(self, test_id: str, repo_root: Path) -> tuple[bool, str]:
        pattern = test_id.lower().replace("-", "_")
        result = subprocess.run(
            ["python", "-m", "pytest", "-x", "-q", "--tb=short", f"-k", pattern],
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output

MAX_RETRIES = 3

ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING:    {TaskStatus.ASSIGNED},
    TaskStatus.ASSIGNED:   {TaskStatus.RUNNING},
    TaskStatus.RUNNING:    {TaskStatus.REVIEW},
    TaskStatus.REVIEW:     {TaskStatus.PASSED, TaskStatus.FAILED},
    TaskStatus.PASSED:     {TaskStatus.COMMITTED},
    TaskStatus.FAILED:     {TaskStatus.RETRYING, TaskStatus.BLOCKED},
    TaskStatus.RETRYING:   {TaskStatus.ASSIGNED},
    TaskStatus.COMMITTED:  set(),
    TaskStatus.BLOCKED:    set(),
}


class InvalidTransitionError(Exception):
    pass


class TaskLifecycle:
    def __init__(
        self,
        task: Task,
        repo_root: Path | None = None,
        runner: TestRunner | None = None,
        enforce_test_gate: bool = False,
    ) -> None:
        self._task = task
        self._repo_root = repo_root or Path(".")
        self._runner: TestRunner = runner or PytestTestRunner()
        self._enforce_test_gate = enforce_test_gate

    @property
    def task(self) -> Task:
        return self._task

    def transition(self, new_status: TaskStatus) -> None:
        allowed = ALLOWED_TRANSITIONS.get(self._task.status, set())
        if new_status not in allowed:
            raise InvalidTransitionError(
                f"{self._task.status.value} → {new_status.value} ist nicht erlaubt"
            )
        self._task.status = new_status

    def assign(self, llm_id: str) -> None:
        self.transition(TaskStatus.ASSIGNED)
        self._task.llm_id = llm_id

    def start_running(self, container_id: str) -> None:
        self.transition(TaskStatus.RUNNING)
        self._task.container_id = container_id

    def submit_for_review(self) -> None:
        self.transition(TaskStatus.REVIEW)

    def mark_passed(self) -> None:
        """SPEC-0034 FR-05/CON-0124: passed nur wenn alle test_ids grün sind.

        enforce_test_gate=True aktiviert das Gate; ohne dieses Flag verhält sich
        mark_passed() wie vor SPEC-0034 (Backward-Kompatibilität).
        """
        if self._enforce_test_gate:
            if not self._task.test_ids:
                self._task.error_context.append("Kein Test zugewiesen – mark_passed() blockiert")
                raise TaskTestRequiredError(
                    f"Task {self._task.id!r} hat test_ids=[] – mark_passed() nicht erlaubt"
                )
            for test_id in self._task.test_ids:
                ok, output = self._runner.run(test_id, self._repo_root)
                if not ok:
                    first_line = output.strip().splitlines()[-1] if output.strip() else "Test fehlgeschlagen"
                    self.transition(TaskStatus.FAILED)
                    self._task.error_context.append(first_line)
                    return
        self.transition(TaskStatus.PASSED)

    def mark_failed(self, reason: str) -> None:
        self.transition(TaskStatus.FAILED)
        self._task.error_context.append(reason)

    def commit(self, commit_hash: str) -> None:
        self.transition(TaskStatus.COMMITTED)
        self._task.commit_hash = commit_hash

    def retry(self) -> None:
        if self._task.retry_count >= MAX_RETRIES:
            self.transition(TaskStatus.BLOCKED)
        else:
            self._task.retry_count += 1
            self.transition(TaskStatus.RETRYING)

    def block(self) -> None:
        """Blockiert direkt, ohne retry_count zu erhöhen (z.B. nach externer Entscheidung)."""
        if self._task.status != TaskStatus.FAILED:
            raise InvalidTransitionError(
                f"block() erfordert status=failed, nicht {self._task.status.value}"
            )
        self._task.status = TaskStatus.BLOCKED
