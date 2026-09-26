"""Dauerangaben wie "1h30m" für Timeouts in der Konfiguration."""
from __future__ import annotations


class DurationError(ValueError):
    """Ungültige Dauerangabe."""


def parse_duration(text: str) -> int:
    """Wandelt eine Dauerangabe in Sekunden um."""
    raise NotImplementedError
