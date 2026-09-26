"""Vergabe der nächsten freien Artefakt-ID (SPEC-, CON-, TST-, ADR-)."""
from __future__ import annotations

from collections.abc import Iterable


def next_id(existing: Iterable[str], prefix: str, padding: int = 4) -> str:
    """Nächste freie ID mit `prefix` nach den bereits vergebenen IDs in `existing`."""
    raise NotImplementedError
