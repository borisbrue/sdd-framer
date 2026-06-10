"""TaskExecutor Protocol – Strategy-Interface für Task-Ausführung (SPEC-0045).

Konsument von CompletionProvider / CodeGenProvider (SPEC-0008).
Kein Duplikat von Provider-Interfaces: TaskExecutor operiert auf Task-Ebene.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class TaskExecutor(Protocol):
    """Ausführungsstrategie für einen einzelnen Task.

    Implementierungen: LocalLLMExecutor, ClaudeExecutor.
    Das Routing wählt zur Laufzeit die passende Strategie (Strategy Pattern).
    """

    async def execute(self, task: Any, workspace: Path, iteration: int) -> Any:
        """Führt den Task aus und gibt ein Ergebnis-Objekt zurück."""
        ...
