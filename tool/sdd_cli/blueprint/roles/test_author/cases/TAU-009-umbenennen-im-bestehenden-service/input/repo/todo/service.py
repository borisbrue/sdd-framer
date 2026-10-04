"""Anwendungsfälle der Todo-Verwaltung."""
from __future__ import annotations

from dataclasses import replace

from todo.domain import Todo, TodoNotFoundError, clean_title
from todo.repository import InMemoryRepository


class TodoService:
    """Legt Todos an, erledigt und benennt sie um."""

    def __init__(self, repository: InMemoryRepository) -> None:
        self._repo = repository

    def add(self, title: str) -> Todo:
        """Neues, offenes Todo mit bereinigtem Titel."""
        todo = Todo(id=self._repo.next_id(), title=clean_title(title))
        self._repo.save(todo)
        return todo

    def complete(self, todo_id: int) -> Todo:
        """Markiert das Todo als erledigt."""
        todo = self._get(todo_id)
        erledigt = replace(todo, done=True)
        self._repo.save(erledigt)
        return erledigt

    def rename(self, todo_id: int, title: str) -> Todo:
        """Neuer Titel für ein bestehendes Todo; ID und Erledigt-Status bleiben."""
        raise NotImplementedError

    def _get(self, todo_id: int) -> Todo:
        todo = self._repo.get(todo_id)
        if todo is None:
            raise TodoNotFoundError(todo_id)
        return todo
