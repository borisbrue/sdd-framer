"""TaskLifecycle – State Machine für Task-Zustandsübergänge (CON-0095).

State Pattern: Ungültige Übergänge sind strukturell unmöglich via ALLOWED_TRANSITIONS.
"""
from __future__ import annotations

from .task_model import Task, TaskStatus

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
    def __init__(self, task: Task) -> None:
        self._task = task

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
