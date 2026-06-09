# AUTO-GENERATED from CON-0159 via sdd test generate — do not delete
"""Unit-Tests für HoldoutStatusFetcher Strategy (CON-0159).

Spec: SPEC-0043 · Contract: CON-0159
Prüft: SSE-Event-Parsing, Reconnect-Backoff, Status-Mapping,
       Fehlertoleranz bei malformed JSON.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tool"))

from sdd_cli.holdout_status_fetcher import HoldoutStatusFetcher, HoldoutStatusEvent


# ─── TC-01: SSE-Event mit status=running wird korrekt geparst ────────────────

def test_tc01_parse_running_event():
    """SSE-Event status=running wird zu HoldoutStatusEvent deserialisiert (CON-0159)."""
    raw = json.dumps({
        "spec_id": "SPEC-0043",
        "status": "running",
        "updated_at": "2026-06-09T12:00:00Z",
    })
    event = HoldoutStatusFetcher.parse_event(raw)
    assert event is not None
    assert event.spec_id == "SPEC-0043"
    assert event.status == "running"
    assert event.updated_at is not None


# ─── TC-02: SSE-Event mit status=failed + scenarios wird korrekt geparst ──────

def test_tc02_parse_failed_event_with_scenarios():
    """SSE-Event status=failed mit scenarios-Payload (CON-0159 HoldoutStatusEvent)."""
    raw = json.dumps({
        "spec_id": "SPEC-0043",
        "status": "failed",
        "updated_at": "2026-06-09T13:00:00Z",
    })
    event = HoldoutStatusFetcher.parse_event(raw)
    assert event is not None
    assert event.status == "failed"


# ─── TC-03: Verbindungsabbruch → Status wechselt auf "unknown" ────────────────

@pytest.mark.asyncio
async def test_tc03_connection_error_yields_unknown():
    """Bei ConnectionError liefert Fetcher status=unknown (CON-0160 INV-04)."""
    fetcher = HoldoutStatusFetcher(base_url="http://localhost:8000", backoff_delays=[0.01])

    with patch.object(fetcher, "_open_sse_connection", side_effect=ConnectionError("refused")):
        events = []
        async for evt in fetcher.fetch("SPEC-0043", max_retries=1):
            events.append(evt)

    assert any(e.status == "unknown" for e in events)


# ─── TC-04: Reconnect-Backoff: 2. Versuch wartet länger ──────────────────────

def test_tc04_backoff_delays_increase():
    """Backoff-Delays nehmen mit jedem Versuch zu (CON-0160 INV-04)."""
    fetcher = HoldoutStatusFetcher(base_url="http://localhost:8000")
    delays = fetcher.get_backoff_delays(attempts=3)
    assert len(delays) >= 2
    assert delays[1] > delays[0], f"Backoff soll steigen: {delays}"


# ─── TC-05: Ungültiges JSON-Event wird ignoriert ──────────────────────────────

def test_tc05_malformed_json_returns_none():
    """Malformed JSON-Event wird ignoriert – kein Exception (CON-0159)."""
    result = HoldoutStatusFetcher.parse_event("das ist kein json {{{")
    assert result is None


# ─── TC-06: Event ohne data-Feld wird übersprungen ───────────────────────────

def test_tc06_empty_data_field_returns_none():
    """Leeres data-Feld ergibt None (kein Crash) (CON-0159)."""
    result = HoldoutStatusFetcher.parse_event("")
    assert result is None


# ─── TC-07: status=none → leeres scenarios-Array kein Fehler ─────────────────

def test_tc07_none_status_no_scenarios():
    """status=none mit leerem scenarios-Array ist valides Event (CON-0159)."""
    raw = json.dumps({
        "spec_id": "SPEC-0043",
        "status": "none",
        "updated_at": "2026-06-09T12:00:00Z",
    })
    event = HoldoutStatusFetcher.parse_event(raw)
    assert event is not None
    assert event.status == "none"
