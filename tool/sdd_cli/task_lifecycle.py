"""TaskLifecycle – State Machine für Task-Zustandsübergänge (CON-0095, SPEC-0034).

State Pattern: Ungültige Übergänge sind strukturell unmöglich via ALLOWED_TRANSITIONS.
SPEC-0034 FR-05: mark_passed() erfordert grüne Tests (TaskTestRequiredError, CON-0124).
"""
from __future__ import annotations

import shlex
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
            ["python", "-m", "pytest", "-x", "-q", "--tb=short", "-k", pattern],
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output


class TaskCommandRunner:
    """Runs task.test_command directly — framework-agnostic (pytest, deno, npm, …)."""

    def run_command(self, command: str, repo_root: Path) -> tuple[bool, str]:
        result = subprocess.run(
            shlex.split(command),
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
        return result.returncode == 0, result.stdout + result.stderr

    def verify_red(self, task: Task, repo_root: Path) -> tuple[bool, str]:
        """Returns (is_red, output). is_red=True means the test fails as expected."""
        if not task.test_command:
            return False, "Kein test_command definiert"
        ok, output = self.run_command(task.test_command, repo_root)
        return not ok, output

    def verify_green(self, task: Task, repo_root: Path) -> tuple[bool, str]:
        """Returns (is_green, output). is_green=True means the test passes."""
        if not task.test_command:
            return False, "Kein test_command definiert"
        return self.run_command(task.test_command, repo_root)


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
        self._cmd_runner = TaskCommandRunner()

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
        """SPEC-0034 FR-05/CON-0124: passed nur wenn test_command grün ist.

        Bevorzugt task.test_command (framework-agnostisch). Fällt auf test_ids +
        PytestTestRunner zurück wenn kein test_command vorhanden.
        enforce_test_gate=True ist jetzt der Default.
        """
        if self._enforce_test_gate:
            if self._task.test_command:
                ok, output = self._cmd_runner.verify_green(self._task, self._repo_root)
                if not ok:
                    last = output.strip().splitlines()[-1] if output.strip() else "Test fehlgeschlagen"
                    self.transition(TaskStatus.FAILED)
                    self._task.error_context.append(last)
                    return
            elif self._task.test_ids:
                for test_id in self._task.test_ids:
                    ok, output = self._runner.run(test_id, self._repo_root)
                    if not ok:
                        last = output.strip().splitlines()[-1] if output.strip() else "Test fehlgeschlagen"
                        self.transition(TaskStatus.FAILED)
                        self._task.error_context.append(last)
                        return
            else:
                self._task.error_context.append("Kein Test zugewiesen – mark_passed() blockiert")
                raise TaskTestRequiredError(
                    f"Task {self._task.id!r} hat test_ids=[] und kein test_command – mark_passed() nicht erlaubt"
                )
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
