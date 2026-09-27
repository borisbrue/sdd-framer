"""Schnittstelle der Speicherung und die Speicher-Umsetzung für TodoService()."""
from __future__ import annotations

from typing import Protocol

from todo.domain import Todo


class TodoRepository(Protocol):
    def load(self) -> tuple[int, list[Todo]]:
        """(nächste ID, Aufgaben aufsteigend nach ID)."""
        ...

    def save(self, next_id: int, todos: list[Todo]) -> None: ...


class InMemoryRepository:
    def __init__(self) -> None:
        self._next_id = 1
        self._todos: list[Todo] = []

    def load(self) -> tuple[int, list[Todo]]:
        return self._next_id, list(self._todos)

    def save(self, next_id: int, todos: list[Todo]) -> None:
        self._next_id, self._todos = next_id, list(todos)
