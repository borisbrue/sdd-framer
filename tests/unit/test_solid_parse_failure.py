"""Eine unparsbare LLM-Antwort darf nicht als `compliant` erscheinen.

_parse_llm_response gab bei JSONDecodeError `[], "compliant", ...` zurueck.
Ohne Findings entstand kein "Checker-Fehler"-Eintrag, SolidReport.had_llm_error
blieb False, und die Warnung in der CLI feuerte nicht. Eine Antwort, die das
Modell gar nicht auswertbar geliefert hatte, erschien als bestandene Pruefung —
genau der Ausgang, den SPEC-0050 FR-03/FR-04 ablehnen.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

from sdd_cli.solid import LlmSolidChecker, SolidAnalyzer, SolidReport


class _Provider:
    """Antwortet mit dem uebergebenen Text, egal was gefragt wird."""

    def __init__(self, text: str) -> None:
        self._text = text

    def complete(self, prompt, **kwargs):
        class _R:
            text = self._text
        return _R()


_GUELTIG = json.dumps({
    "solid_findings": [],
    "overall_solid_score": "compliant",
    "summary": "ok",
})


class TestParseFailureIsAnError:
    def test_unparseable_answer_yields_a_checker_error_finding(self):
        checker = LlmSolidChecker("S", _Provider("Hier ist deine Analyse!"))
        findings = checker.check("code", "CON-0001")

        assert len(findings) == 1
        assert findings[0].location == "Checker-Fehler"

    def test_had_llm_error_becomes_true(self):
        """Das ist der Schalter, an dem die CLI-Warnung haengt."""
        checker = LlmSolidChecker("S", _Provider("kein JSON"))
        report = SolidReport(artifact_id="CON-0001", artifact_type="contract",
                             findings=checker.check("code", "CON-0001"))
        assert report.had_llm_error is True

    def test_valid_answer_keeps_had_llm_error_false(self):
        checker = LlmSolidChecker("S", _Provider(_GUELTIG))
        report = SolidReport(artifact_id="CON-0001", artifact_type="contract",
                             findings=checker.check("code", "CON-0001"))
        assert report.had_llm_error is False

    def test_reason_names_the_cause(self):
        checker = LlmSolidChecker("S", _Provider("kein JSON"))
        beschreibung = checker.check("code", "CON-0001")[0].description
        assert "nicht als JSON parsebar" in beschreibung


class TestChainStillCompletes:
    """CON-0045 INV-04: ein Checker-Fehler unterbricht die Kette nicht."""

    def test_finding_has_info_severity(self):
        checker = LlmSolidChecker("I", _Provider("kein JSON"))
        assert checker.check("code", "CON-0001")[0].severity == "info"

    def test_analyzer_runs_all_checkers_despite_the_error(self):
        kaputt = LlmSolidChecker("S", _Provider("kein JSON"))
        heil = LlmSolidChecker("O", _Provider(_GUELTIG))
        report = SolidAnalyzer([kaputt, heil]).analyze("code", "CON-0001", "contract")

        assert report.had_llm_error is True
        assert report.has_violations() is False

    def test_parse_failure_does_not_report_a_violation(self):
        """Der Fehler soll sichtbar sein, aber kein Verstoss erfunden werden."""
        checker = LlmSolidChecker("S", _Provider("kein JSON"))
        report = SolidAnalyzer([checker]).analyze("code", "CON-0001", "contract")
        assert report.overall_solid_score == "compliant"
        assert report.had_llm_error is True, (
            "Der Score allein taeuscht – had_llm_error muss den Unterschied tragen"
        )
