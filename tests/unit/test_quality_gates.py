"""SPEC-0054 FR-10, CON-0196 INV-04/INV-07: Gates parsen, prüfen, fail-closed auswerten."""
from __future__ import annotations

import pytest

from sdd_cli.quality.gates import evaluate_gates, validate_gate

REPORT = {
    "score": 0.8,
    "tree": {"name": "total", "weight": 1, "score": 0.8, "children": [
        {"name": "requirements", "weight": 0.5, "score": None, "reason": "x"},
        {"name": "code_quality", "weight": 0.25, "score": 0.6, "metrics": [
            {"name": "lint_per_kloc", "raw": 4, "normalized": 0.6}]}]},
    "requirements": {"frs": [{"id": "FR-01", "status": "fehlt", "tests": []}]},
    "architecture": {"violations": [{"severity": "error"}, {"severity": "warn"}],
                     "rules_na": [], "unresolved_edges": 0},
    "probes": [{"status": "n/a"}, {"status": "ok"}],
}


@pytest.mark.parametrize(("gate", "fehler"), [
    ("requirements >= 1.0", None), ("count.architecture.errors == 0", None),
    ("code_quality.lint_per_kloc >= 0.5", None), ("total > 0.7", None),
    ("count.architecture.errors >= 0.8", "ganze Zahl erwartet"),
    ("requirements >= 3", "Wert in [0, 1] erwartet"),
    ("security >= 0.5", "unbekannter Pfad"), ("requirements ~ 1", "ungültige Syntax"),
    ("count.foo == 1", "unbekannter Pfad")])
def test_validierung(gate, fehler):
    assert validate_gate(gate) == fehler


@pytest.mark.parametrize(("gate", "bestanden"), [
    ("total >= 0.8", True), ("requirements >= 0.0", False),
    ("count.architecture.errors == 0", False), ("count.architecture.warnings <= 1", True),
    ("count.frs_missing == 1", True), ("count.probes_na == 0", False),
    ("code_quality.lint_per_kloc >= 0.5", True), ("code_quality.unbekannt >= 0", False)])
def test_auswertung(gate, bestanden):
    [ergebnis] = evaluate_gates([gate], REPORT)
    assert ergebnis["passed"] is bestanden and ergebnis["expression"] == gate
    if not bestanden:
        assert ergebnis["reason"]
