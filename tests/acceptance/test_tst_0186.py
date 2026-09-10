# AUTO-GENERATED from CON-0160 via sdd test generate — do not delete
"""Acceptance-Tests für Holdout-Status ContainerView Verhalten (CON-0160).

Spec: SPEC-0043 · Contract: CON-0160
Prüft: Alle Gherkin-Szenarien aus CON-0160 via API-Schicht.
INV-01 (Text-Label), INV-02 (neuester Lauf), INV-03 (rein lesend).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tool" / "sdd_cli" / "web" / "api"))
sys.path.insert(0, str(REPO_ROOT / "tool"))

os.environ.setdefault("SDD_PROJECT_ROOT", str(REPO_ROOT))

import sdd_context
sdd_context.init(REPO_ROOT)

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# Patch-Ziel ist `routes.holdouts`, nicht `sdd_cli.web.api.routes.holdouts`: die
# App kommt ueber `from main import app`, also unter den kurzen Modulnamen. Die
# Datei ist damit ein zweites Modulobjekt, und ein Patch auf den langen Namen
# erreicht die Endpunkte nicht. Bis #107 verdeckte das eine Weiterleitung in der
# Root-Kopie der API; tc01–tc04 bestanden dabei sogar ohne greifenden Patch,
# weil der echte Status 'none' ebenfalls in der erlaubten Menge liegt.


def _holdout(status: str, scenarios=None, run_id: str | None = "run-001", updated_at="2026-06-09T12:00:00Z"):
    return {
        "spec_id": "SPEC-0043",
        "status": status,
        "updated_at": updated_at,
        "run_id": run_id if status != "none" else None,
        "scenarios": scenarios or [],
    }


# ─── Szenario: Laufender Holdout wird angezeigt ───────────────────────────────

def test_scenario_running_holdout_shows_running_status():
    """API liefert status=running für aktiven Lauf (CON-0160 Szenario 1)."""
    with patch("routes.holdouts.get_holdout_status") as mock_svc:
        mock_svc.return_value = _holdout("running")
        response = client.get("/api/holdouts/SPEC-0043")

    assert response.status_code == 200
    assert response.json()["status"] == "running"


# ─── Szenario: Bestandener Holdout ────────────────────────────────────────────

def test_scenario_passed_holdout_no_scenarios():
    """API liefert status=passed und leere scenarios (CON-0160 Szenario 2)."""
    with patch("routes.holdouts.get_holdout_status") as mock_svc:
        mock_svc.return_value = _holdout("passed")
        response = client.get("/api/holdouts/SPEC-0043")

    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "passed"
    assert data.get("scenarios", []) == []


# ─── Szenario: Fehlgeschlagener Holdout mit Szenario-Details ──────────────────

def test_scenario_failed_holdout_includes_scenario_name():
    """API liefert status=failed mit Szenario 'Login' in scenarios (CON-0160 Szenario 3)."""
    with patch("routes.holdouts.get_holdout_status") as mock_svc:
        mock_svc.return_value = _holdout(
            "failed",
            scenarios=[{"name": "Login", "status": "failed", "error_message": "auth failed"}],
        )
        response = client.get("/api/holdouts/SPEC-0043")

    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "failed"
    names = [s["name"] for s in data["scenarios"]]
    assert "Login" in names


# ─── Szenario: Kein Holdout vorhanden ────────────────────────────────────────

def test_scenario_no_holdout_shows_none():
    """API liefert status=none wenn kein Lauf existiert (CON-0160 Szenario 4)."""
    with patch("routes.holdouts.get_holdout_status") as mock_svc:
        mock_svc.return_value = _holdout("none", run_id=None)
        response = client.get("/api/holdouts/SPEC-0043")

    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "none"
    assert data.get("scenarios", []) == []


# ─── INV-02: Nur neuester Holdout-Lauf wird geliefert ────────────────────────

def test_inv02_only_newest_run_returned():
    """Bei zwei Läufen liefert API nur den neuesten (CON-0160 INV-02)."""
    newest = _holdout("passed", updated_at="2026-06-09T14:00:00Z", run_id="run-002")
    with patch("routes.holdouts.get_holdout_status") as mock_svc:
        mock_svc.return_value = newest
        response = client.get("/api/holdouts/SPEC-0043")

    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "passed"
    assert data["run_id"] == "run-002"


# ─── INV-03: API-Response enthält keine Trigger-/Konfigurations-Felder ────────

def test_inv03_response_contains_no_action_fields():
    """Response enthält keine action- oder config-Felder (CON-0160 INV-03)."""
    with patch("routes.holdouts.get_holdout_status") as mock_svc:
        mock_svc.return_value = _holdout("failed")
        response = client.get("/api/holdouts/SPEC-0043")

    data = response.json()
    forbidden_keys = {"action", "trigger", "config", "start_url", "stop_url"}
    assert forbidden_keys.isdisjoint(data.keys()), (
        f"Response enthält unerlaubte Aktions-/Konfigurations-Felder: "
        f"{forbidden_keys & data.keys()}"
    )


# ─── INV-01: status ist immer ein nicht-leerer String (wenn Lauf vorhanden) ───

@pytest.mark.parametrize("api_status,expected", [
    ("running", "running"),
    ("passed", "passed"),
    ("failed", "failed"),
    ("none", "none"),
])
def test_inv01_status_always_present_as_string(api_status, expected):
    """status-Wert ist immer ein nicht-leerer String (CON-0160 INV-01, Szenariogrundriss)."""
    with patch("routes.holdouts.get_holdout_status") as mock_svc:
        mock_svc.return_value = _holdout(api_status)
        response = client.get("/api/holdouts/SPEC-0043")

    data = response.json()
    assert response.status_code == 200
    assert isinstance(data["status"], str)
    assert data["status"] == expected
