"""Kommandozeile von todo-service. Importiert nur `todo.service` und `todo.domain` (ADR-0001)."""
from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    """Einstiegspunkt der CLI; gibt den Exit-Code zurück."""
    print("todo: noch keine Befehle implementiert", file=sys.stderr)
    return 2
