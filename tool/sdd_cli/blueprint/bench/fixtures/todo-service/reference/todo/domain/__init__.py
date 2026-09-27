"""Domänenmodell von todo-service: Aufgaben und Fehlertypen, ohne Ein-/Ausgabe.

Darf nichts aus `todo.service`, `todo.persistence` oder `todo.cli` importieren (ADR-0001).
"""
from .errors import StorageError, TodoNotFoundError, ValidationError
from .model import (
    MAX_TITLE_LENGTH,
    Todo,
    normalize_tag,
    normalize_tags,
    normalize_title,
    validate_due,
)

__all__ = [
    "MAX_TITLE_LENGTH",
    "StorageError",
    "Todo",
    "TodoNotFoundError",
    "ValidationError",
    "normalize_tag",
    "normalize_tags",
    "normalize_title",
    "validate_due",
]
