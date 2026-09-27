"""Speicherung von todo-service als JSON-Datei. Importiert nur `todo.domain` (ADR-0001)."""
from todo.domain import StorageError

from .json_file import JsonFileRepository

__all__ = ["JsonFileRepository", "StorageError"]
