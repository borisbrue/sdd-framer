"""SchedulerCommand-Protocol + CommandQueue für SPEC-0037.

Command Pattern (CON-0132): WebUI-Eingriffe als serialisierbare Objekte,
DAG-Invarianz-Prüfung vor Ausführung.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable


# ─────────────────────────────────────────────────────────────────────────────
# Protocol
# ─────────────────────────────────────────────────────────────────────────────

@runtime_checkable
class SchedulerCommand(Protocol):
    run_id: str
    task_id: str
    command_type: str

    def apply(self, scheduler_state: "SchedulerState") -> None: ...


# ─────────────────────────────────────────────────────────────────────────────
# Shared scheduler state (mutiert durch Commands, gelesen vom DagScheduler)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SchedulerState:
    """Minimaler, mutabler Zustand den Commands verändern dürfen."""
    paused_tasks: set[str] = field(default_factory=set)
    route_overrides: dict[str, Literal["local", "cloud"]] = field(default_factory=dict)
    skipped_tasks: set[str] = field(default_factory=set)
    restart_tasks: set[str] = field(default_factory=set)
    # task_id → set of dependency task_ids (für Invarianz-Check)
    deps_by_task: dict[str, set[str]] = field(default_factory=dict)
    # task_ids mit Status "done"
    completed_tasks: set[str] = field(default_factory=set)
    # task_ids mit Status "failed"
    failed_tasks: set[str] = field(default_factory=set)


class InvariantViolation(ValueError):
    """Command würde DAG-Invariante verletzen."""


# ─────────────────────────────────────────────────────────────────────────────
# Concrete Commands
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PauseTaskCommand:
    run_id: str
    task_id: str
    command_type: str = field(default="pause_task", init=False)

    def apply(self, state: SchedulerState) -> None:
        state.paused_tasks.add(self.task_id)


@dataclass
class ResumeTaskCommand:
    run_id: str
    task_id: str
    command_type: str = field(default="resume_task", init=False)

    def apply(self, state: SchedulerState) -> None:
        state.paused_tasks.discard(self.task_id)


@dataclass
class ForceLocalCommand:
    run_id: str
    task_id: str
    command_type: str = field(default="force_local", init=False)

    def apply(self, state: SchedulerState) -> None:
        state.route_overrides[self.task_id] = "local"


@dataclass
class ForceCloudCommand:
    run_id: str
    task_id: str
    command_type: str = field(default="force_cloud", init=False)

    def apply(self, state: SchedulerState) -> None:
        state.route_overrides[self.task_id] = "cloud"


@dataclass
class SkipTaskCommand:
    run_id: str
    task_id: str
    command_type: str = field(default="skip_task", init=False)

    def apply(self, state: SchedulerState) -> None:
        # Invarianz: skip nur wenn keine unerfüllten Abhängigkeiten offen sind
        # (d.h. alle deps müssen done oder skipped sein)
        open_deps = state.deps_by_task.get(self.task_id, set()) - state.completed_tasks - state.skipped_tasks
        if open_deps:
            raise InvariantViolation(
                f"Cannot skip {self.task_id}: open dependencies {open_deps}"
            )
        state.skipped_tasks.add(self.task_id)


@dataclass
class RestartTaskCommand:
    run_id: str
    task_id: str
    command_type: str = field(default="restart_task", init=False)

    def apply(self, state: SchedulerState) -> None:
        # Invarianz: restart nur für failed tasks (FR-04)
        if self.task_id not in state.failed_tasks:
            raise InvariantViolation(
                f"Cannot restart {self.task_id}: not in failed state"
            )
        state.restart_tasks.add(self.task_id)
        state.failed_tasks.discard(self.task_id)


_COMMAND_TYPES: dict[str, type] = {
    "pause_task":   PauseTaskCommand,
    "resume_task":  ResumeTaskCommand,
    "force_local":  ForceLocalCommand,
    "force_cloud":  ForceCloudCommand,
    "skip_task":    SkipTaskCommand,
    "restart_task": RestartTaskCommand,
}


def build_command(run_id: str, task_id: str, command_type: str) -> SchedulerCommand:
    cls = _COMMAND_TYPES.get(command_type)
    if cls is None:
        raise ValueError(f"Unknown command_type: {command_type!r}")
    return cls(run_id=run_id, task_id=task_id)


# ─────────────────────────────────────────────────────────────────────────────
# CommandQueue
# ─────────────────────────────────────────────────────────────────────────────

class CommandQueue:
    """FIFO-Queue für SchedulerCommands, run_id-isoliert (CON-0132)."""

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}

    def _q(self, run_id: str) -> asyncio.Queue:
        if run_id not in self._queues:
            self._queues[run_id] = asyncio.Queue()
        return self._queues[run_id]

    async def enqueue(self, command: SchedulerCommand) -> None:
        await self._q(command.run_id).put(command)

    def enqueue_sync(self, command: SchedulerCommand) -> None:
        """Für synchrone HTTP-Handler ohne laufenden Event-Loop."""
        self._q(command.run_id).put_nowait(command)

    def drain(self, run_id: str, state: SchedulerState) -> list[str]:
        """Leert die Queue und wendet alle Commands auf state an.
        Gibt Liste von Fehlermeldungen zurück (Invarianz-Verletzungen werden geloggt, nicht geworfen).
        """
        errors: list[str] = []
        q = self._queues.get(run_id)
        if not q:
            return errors
        while not q.empty():
            try:
                cmd = q.get_nowait()
                cmd.apply(state)
            except InvariantViolation as e:
                errors.append(str(e))
        return errors

    def clear(self, run_id: str) -> None:
        self._queues.pop(run_id, None)


# Prozess-weiter Singleton
_queue: CommandQueue | None = None


def get_command_queue() -> CommandQueue:
    global _queue
    if _queue is None:
        _queue = CommandQueue()
    return _queue
