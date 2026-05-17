# AUTO-GENERATED from CON-0045 via sdd test generate — do not delete
"""Contract-Tests für SOLID Analyzer Behavior (CON-0045).

Spec: SPEC-0015 · Contract: CON-0045
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[4] / "tool"))

from sdd_cli.solid import (
    NullSolidChecker,
    SolidAnalyzer,
    SolidFinding,
    _compute_score,
    _checker_error_finding,
)


def _make_finding(principle: str, severity: str) -> SolidFinding:
    return SolidFinding(
        principle=principle,
        severity=severity,
        location="Abschnitt X",
        description="Test-Finding",
        suggestion="Verbesserungsvorschlag",
    )


def test_tc01_konformes_artefakt_erh_lt_score_compliant():
    """Scenario: Konformes Artefakt erhält Score 'compliant' (CON-0045 INV-02)."""
    findings: list[SolidFinding] = []
    score = _compute_score(findings)
    assert score == "compliant"


def test_tc02_srp_violation_wird_als_violation_gemeldet():
    """Scenario: SRP-Violation wird als 'violation' gemeldet (CON-0045 INV-01/02)."""
    f = _make_finding("S", "violation")
    assert f.principle == "S"
    assert f.severity == "violation"
    assert f.location
    assert f.description
    assert f.suggestion
    score = _compute_score([f])
    assert score == "violation"


def test_tc03_ocp_warnung_bei_fehlendem_erweiterungspunkt():
    """Scenario: OCP-Warnung (CON-0045)."""
    f = _make_finding("O", "warn")
    assert f.principle == "O"
    assert f.severity in {"warn", "violation"}


def test_tc04_nullsolidchecker_liefert_immer_leeres_ergebnis():
    """Scenario: NullSolidChecker liefert immer leeres Ergebnis (CON-0045 INV-03)."""
    checker = NullSolidChecker()
    analyzer = SolidAnalyzer([checker])
    report = analyzer.analyze("beliebiger Artefakt-Text", "SPEC-XXXX", "spec")
    assert report.findings == []
    assert report.overall_solid_score == "compliant"


def test_tc05_checker_fehler_unterbricht_kette_nicht():
    """Scenario: Checker-Fehler unterbricht Kette nicht (CON-0045 INV-04)."""

    class FaultyChecker:
        principle = "I"

        def check(self, text: str, aid: str) -> list[SolidFinding]:
            raise RuntimeError("Simulierter Checker-Fehler")

    class GoodChecker:
        principle = "D"

        def check(self, text: str, aid: str) -> list[SolidFinding]:
            return [_make_finding("D", "info")]

    analyzer = SolidAnalyzer([FaultyChecker(), GoodChecker()])
    report = analyzer.analyze("text", "SPEC-TEST", "spec")

    principles = [f.principle for f in report.findings]
    assert "D" in principles, "GoodChecker (D) muss trotz FaultyChecker laufen"
    error_findings = [f for f in report.findings if "Fehler" in f.description]
    assert error_findings, "Fehler-Finding muss vorhanden sein"


def test_tc06_score_violation_wenn_mindestens_ein_violation_find():
    """Scenario: Score 'violation' wenn mind. ein violation-Finding (CON-0045 INV-02)."""
    findings = [
        _make_finding("S", "warn"),
        _make_finding("O", "violation"),
        _make_finding("L", "info"),
    ]
    assert _compute_score(findings) == "violation"


def test_tc07_score_warn_wenn_nur_warn_findings_kein_violation():
    """Scenario: Score 'warn' wenn nur warn-Findings, kein violation (CON-0045 INV-02)."""
    findings = [
        _make_finding("S", "warn"),
        _make_finding("O", "info"),
    ]
    assert _compute_score(findings) == "warn"
