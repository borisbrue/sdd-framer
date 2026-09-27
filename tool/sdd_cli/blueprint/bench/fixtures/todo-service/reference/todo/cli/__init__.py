"""Kommandozeile von todo-service. Importiert nur `todo.service` und `todo.domain` (ADR-0001)."""
from .main import main

__all__ = ["main"]
