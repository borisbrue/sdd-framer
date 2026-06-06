from __future__ import annotations

from typing import Protocol, runtime_checkable

from .process_manager import ProcessManager


@runtime_checkable
class ProjectCommand(Protocol):
    project_id: str

    def execute(self, manager: ProcessManager) -> None: ...


class StartProjectCommand:
    def __init__(self, project_id: str) -> None:
        self.project_id = project_id

    def execute(self, manager: ProcessManager) -> None:
        manager.start(self.project_id)


class StopProjectCommand:
    def __init__(self, project_id: str) -> None:
        self.project_id = project_id

    def execute(self, manager: ProcessManager) -> None:
        manager.stop(self.project_id)
