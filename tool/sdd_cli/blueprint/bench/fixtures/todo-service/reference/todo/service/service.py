"""TodoService: Anwendungsfälle über einem injizierten Repository (SPEC-0001 bis SPEC-0003)."""
from __future__ import annotations

import datetime as dt
from collections.abc import Callable, Iterable
from dataclasses import replace

from todo.domain import (
    Todo,
    TodoNotFoundError,
    normalize_tag,
    normalize_tags,
    normalize_title,
    validate_due,
)

from . import export
from .repository import InMemoryRepository, TodoRepository


class TodoService:
    def __init__(self, repository: TodoRepository | None = None) -> None:
        self._repo: TodoRepository = repository if repository is not None \
            else InMemoryRepository()
        self._next_id, geladen = self._repo.load()
        self._todos: dict[int, Todo] = {t.id: t for t in geladen}
        self._history: list[dict[int, Todo]] = []

    # ── Lesen ──
    def get(self, todo_id: int) -> Todo:
        try:
            return self._todos[todo_id]
        except (KeyError, TypeError):
            raise TodoNotFoundError(todo_id) from None

    def list_todos(self, *, done: bool | None = None, tag: str | None = None,
                   due_before: dt.date | None = None, text: str | None = None) -> list[Todo]:
        ergebnis = [self._todos[i] for i in sorted(self._todos)]
        if done is not None:
            ergebnis = [t for t in ergebnis if t.done == done]
        if tag is not None:
            gesucht = tag.strip().lower()
            ergebnis = [t for t in ergebnis if gesucht in t.tags]
        if due_before is not None:
            ergebnis = [t for t in ergebnis if t.due is not None and t.due < due_before]
        if text is not None:
            klein = text.casefold()
            ergebnis = [t for t in ergebnis if klein in t.title.casefold()]
        return ergebnis

    def overdue(self, today: dt.date) -> list[Todo]:
        offen = [t for t in self._todos.values()
                 if not t.done and t.due is not None and t.due < today]
        return sorted(offen, key=lambda t: (t.due, t.id))

    def export_json(self) -> str:
        return export.to_json(self.list_todos())

    def export_csv(self) -> str:
        return export.to_csv(self.list_todos())

    # ── Ändern ──
    def add(self, title: str, tags: Iterable[str] = (), due: dt.date | None = None) -> Todo:
        todo = Todo(id=self._next_id, title=normalize_title(title),
                    tags=normalize_tags(tags), due=validate_due(due))

        def aendern(todos: dict[int, Todo]) -> None:
            todos[todo.id] = todo

        self._change(aendern, next_id=self._next_id + 1)
        return todo

    def complete(self, todo_id: int) -> Todo:
        return self._update(todo_id, lambda t: replace(t, done=True))

    def reopen(self, todo_id: int) -> Todo:
        return self._update(todo_id, lambda t: replace(t, done=False))

    def rename(self, todo_id: int, title: str) -> Todo:
        self.get(todo_id)
        neu = normalize_title(title)
        return self._update(todo_id, lambda t: replace(t, title=neu))

    def tag(self, todo_id: int, *tags: str) -> Todo:
        self.get(todo_id)
        neu = [normalize_tag(t) for t in tags]
        return self._update(todo_id, lambda t: replace(t, tags=tuple(sorted({*t.tags, *neu}))))

    def untag(self, todo_id: int, *tags: str) -> Todo:
        self.get(todo_id)
        weg = {normalize_tag(t) for t in tags}
        return self._update(todo_id,
                            lambda t: replace(t, tags=tuple(x for x in t.tags if x not in weg)))

    def set_due(self, todo_id: int, due: dt.date | None) -> Todo:
        self.get(todo_id)
        datum = validate_due(due)
        return self._update(todo_id, lambda t: replace(t, due=datum))

    def delete(self, todo_id: int) -> None:
        self.get(todo_id)

        def aendern(todos: dict[int, Todo]) -> None:
            del todos[todo_id]

        self._change(aendern)

    def undo(self) -> bool:
        if not self._history:
            return False
        vorher = self._history.pop()
        self._repo.save(self._next_id, [vorher[i] for i in sorted(vorher)])
        self._todos = vorher
        return True

    # ── intern ──
    def _update(self, todo_id: int, fn: Callable[[Todo], Todo]) -> Todo:
        neu = fn(self.get(todo_id))

        def aendern(todos: dict[int, Todo]) -> None:
            todos[todo_id] = neu

        self._change(aendern)
        return neu

    def _change(self, aendern: Callable[[dict[int, Todo]], None],
                next_id: int | None = None) -> None:
        neu = dict(self._todos)
        aendern(neu)
        naechste = self._next_id if next_id is None else next_id
        self._repo.save(naechste, [neu[i] for i in sorted(neu)])
        self._history.append(self._todos)
        self._todos, self._next_id = neu, naechste
