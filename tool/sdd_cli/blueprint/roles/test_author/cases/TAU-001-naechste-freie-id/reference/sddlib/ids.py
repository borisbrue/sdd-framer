"""Vergabe der nächsten freien Artefakt-ID (SPEC-, CON-, TST-, ADR-)."""
from __future__ import annotations

import re
from collections.abc import Iterable


def next_id(existing: Iterable[str], prefix: str, padding: int = 4) -> str:
    """Nächste freie ID mit `prefix` nach den bereits vergebenen IDs in `existing`."""
    if padding < 1:
        raise ValueError("padding muss mindestens 1 sein")
    pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
    numbers = [int(m.group(1)) for i in existing if (m := pattern.match(i))]
    nxt = (max(numbers) + 1) if numbers else 1
    return f"{prefix}-{str(nxt).zfill(padding)}"
