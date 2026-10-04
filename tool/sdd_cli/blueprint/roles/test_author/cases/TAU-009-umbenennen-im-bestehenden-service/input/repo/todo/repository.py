"""Ablage der Todos im Speicher."""
from __future__ import annotations

from todo.domain import Todo


class InMemoryRepository:
    """Hält Todos nach ID; `save` legt an oder ersetzt."""

    def __init__(self) -> None:
        self._todos: dict[int, Todo] = {}
        self._letzte_id = 0

    def next_id(self) -> int:
        """Nächste freie ID, beginnend bei 1."""
        self._letzte_id += 1
        return self._letzte_id

    def save(self, todo: Todo) -> None:
        """Legt das Todo an oder ersetzt das mit gleicher ID."""
        self._todos[todo.id] = todo

    def get(self, todo_id: int) -> Todo | None:
        """Das Todo mit dieser ID oder None."""
        return self._todos.get(todo_id)

    def todos(self) -> list[Todo]:
        """Alle Todos nach ID sortiert."""
        return [self._todos[k] for k in sorted(self._todos)]
