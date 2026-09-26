"""Run-IDs der Pipeline: <SPEC-ID>-<UTC-Zeitstempel>."""
from __future__ import annotations

import re
from datetime import datetime, timezone

_SPEC_ID = re.compile(r"^[A-Z]+-\d+$")
_RUN_ID = re.compile(r"^(?P<spec>[A-Z]+-\d+)-(?P<ts>\d{8}T\d{6}Z)$")
_FORMAT = "%Y%m%dT%H%M%SZ"


def new_run_id(spec_id: str, when: datetime) -> str:
    """Run-ID aus Spec-ID und zeitzonenbewusstem Zeitpunkt."""
    if when.tzinfo is None or when.utcoffset() is None:
        raise ValueError("Zeitpunkt braucht eine Zeitzone")
    if not _SPEC_ID.match(spec_id):
        raise ValueError(f"ungültige Spec-ID: {spec_id!r}")
    return f"{spec_id}-{when.astimezone(timezone.utc).strftime(_FORMAT)}"


def parse_run_id(run_id: str) -> tuple[str, datetime]:
    """Umkehrung von new_run_id: (spec_id, Zeitpunkt in UTC)."""
    m = _RUN_ID.match(run_id)
    if m is None:
        raise ValueError(f"ungültige Run-ID: {run_id!r}")
    when = datetime.strptime(m["ts"], _FORMAT).replace(tzinfo=timezone.utc)
    return m["spec"], when
