"""Run-IDs der Pipeline: <SPEC-ID>-<UTC-Zeitstempel>."""
from __future__ import annotations

from datetime import datetime


def new_run_id(spec_id: str, when: datetime) -> str:
    """Run-ID aus Spec-ID und zeitzonenbewusstem Zeitpunkt."""
    raise NotImplementedError


def parse_run_id(run_id: str) -> tuple[str, datetime]:
    """Umkehrung von new_run_id: (spec_id, Zeitpunkt in UTC)."""
    raise NotImplementedError
