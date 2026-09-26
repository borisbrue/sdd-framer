"""Dauerangaben wie "1h30m" für Timeouts in der Konfiguration."""
from __future__ import annotations

import re

UNITS = {"d": 86400, "h": 3600, "m": 60, "s": 1}
ORDER = "dhms"
_TOKEN = re.compile(r"(\d+)([a-z])")


class DurationError(ValueError):
    """Ungültige Dauerangabe."""


def parse_duration(text: str) -> int:
    """Wandelt eine Dauerangabe in Sekunden um."""
    roh = text.strip().lower()
    if not roh:
        raise DurationError("leere Dauer")
    if roh.isdigit():
        return int(roh)
    pos, total, letzte = 0, 0, -1
    for m in _TOKEN.finditer(roh):
        if m.start() != pos:
            raise DurationError(f"ungültige Dauer: {text!r}")
        zahl, einheit = int(m.group(1)), m.group(2)
        if einheit not in UNITS:
            raise DurationError(f"unbekannte Einheit {einheit!r}")
        rang = ORDER.index(einheit)
        if rang <= letzte:
            raise DurationError(f"Einheit {einheit!r} doppelt oder in falscher Reihenfolge")
        letzte = rang
        total += zahl * UNITS[einheit]
        pos = m.end()
    if pos != len(roh):
        raise DurationError(f"ungültige Dauer: {text!r}")
    return total
