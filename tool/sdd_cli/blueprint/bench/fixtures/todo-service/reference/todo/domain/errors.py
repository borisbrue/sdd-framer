"""Fehlertypen der Domäne."""


class ValidationError(ValueError):
    """Eine Eingabe verletzt eine Regel des Modells (Titel, Tag, Fälligkeit)."""


class TodoNotFoundError(LookupError):
    """Es gibt keine Aufgabe mit der angefragten ID."""

    def __init__(self, todo_id: object) -> None:
        super().__init__(f"Aufgabe #{todo_id} gibt es nicht")
        self.todo_id = todo_id


class StorageError(Exception):
    """Der gespeicherte Zustand ist unlesbar oder beschädigt (re-exportiert von todo.persistence)."""
