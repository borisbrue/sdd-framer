"""Unit-Tests für solid.py – SOLID-Analyse-Engine (SPEC-0015)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sdd_cli.solid import (
    SolidFinding,
    SolidReport,
    NullSolidChecker,
    LlmSolidChecker,
    BatchLlmSolidChecker,
    SolidAnalyzer,
    SrpChecker, OcpChecker, LspChecker, IspChecker, DipChecker,
    _parse_llm_response,
    _extract_json,
    _compute_score,
    _build_summary,
    _checker_error_finding,
    _build_batch_prompt,
    _build_single_principle_prompt,
    PRINCIPLE_LABELS,
)
from sdd_cli.config import SddConfig


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _finding(principle="S", severity="violation"):
    return SolidFinding(
        principle=principle, severity=severity,
        location="Abschnitt 1", description="Desc", suggestion="Fix",
    )


def _make_config(raw: dict | None = None) -> SddConfig:
    return SddConfig(root=Path("/tmp"), raw=raw or {})


# ─── SolidFinding / SolidReport ───────────────────────────────────────────────

class TestSolidFinding:
    def test_to_dict_has_all_fields(self):
        f = _finding("S", "warn")
        d = f.to_dict()
        assert d["principle"] == "S"
        assert d["severity"] == "warn"
        assert "location" in d and "description" in d and "suggestion" in d

    def test_to_dict_roundtrip(self):
        f = _finding("D", "info")
        d = f.to_dict()
        assert d["principle"] == "D"
        assert d["severity"] == "info"


class TestSolidReport:
    def test_has_violations_true(self):
        report = SolidReport("SPEC-0001", "spec", findings=[_finding("S", "violation")])
        assert report.has_violations()

    def test_has_violations_false_for_warn(self):
        report = SolidReport("SPEC-0001", "spec", findings=[_finding("S", "warn")])
        assert not report.has_violations()

    def test_to_dict_structure(self):
        report = SolidReport(
            artifact_id="SPEC-0001",
            artifact_type="spec",
            findings=[_finding("O", "warn")],
            overall_solid_score="warn",
            summary="One warning",
        )
        d = report.to_dict()
        assert d["artifact_id"] == "SPEC-0001"
        assert d["artifact_type"] == "spec"
        assert len(d["solid_findings"]) == 1
        assert d["overall_solid_score"] == "warn"


# ─── NullSolidChecker ─────────────────────────────────────────────────────────

class TestNullSolidChecker:
    def test_returns_empty_list(self):
        checker = NullSolidChecker()
        assert checker.check("anything", "SPEC-0001") == []

    def test_principle_is_all(self):
        assert NullSolidChecker.principle == "ALL"


# ─── LlmSolidChecker ──────────────────────────────────────────────────────────

class TestLlmSolidChecker:
    def test_unknown_principle_raises(self):
        with pytest.raises(ValueError, match="Unbekanntes SOLID-Prinzip"):
            LlmSolidChecker("X", MagicMock())

    def test_valid_principles_accepted(self):
        for p in "SOLID":
            checker = LlmSolidChecker(p, MagicMock())
            assert checker.principle == p

    def test_check_returns_findings_from_provider(self):
        provider = MagicMock()
        payload = json.dumps({
            "solid_findings": [{
                "principle": "S",
                "severity": "warn",
                "location": "§1",
                "description": "Too much",
                "suggestion": "Split",
            }],
            "overall_solid_score": "warn",
            "summary": "ok",
        })
        provider.complete.return_value = MagicMock(text=payload)
        checker = LlmSolidChecker("S", provider)
        findings = checker.check("spec text", "SPEC-0001")
        assert len(findings) == 1
        assert findings[0].principle == "S"

    def test_check_returns_error_finding_on_provider_exception(self):
        provider = MagicMock()
        provider.complete.side_effect = RuntimeError("network error")
        checker = LlmSolidChecker("O", provider)
        findings = checker.check("text", "SPEC-0002")
        assert len(findings) == 1
        assert findings[0].principle == "O"
        assert findings[0].severity == "info"


# ─── BatchLlmSolidChecker ─────────────────────────────────────────────────────

class TestBatchLlmSolidChecker:
    def test_returns_all_findings(self):
        provider = MagicMock()
        payload = json.dumps({
            "solid_findings": [
                {"principle": "S", "severity": "violation", "location": "§1",
                 "description": "SRP violated", "suggestion": "Split"},
                {"principle": "D", "severity": "warn", "location": "§2",
                 "description": "DIP issue", "suggestion": "Inject"},
            ],
            "overall_solid_score": "violation",
            "summary": "Two issues",
        })
        provider.complete.return_value = MagicMock(text=payload)
        checker = BatchLlmSolidChecker(provider)
        findings = checker.check("spec", "SPEC-0001")
        assert len(findings) == 2

    def test_filter_applies(self):
        provider = MagicMock()
        payload = json.dumps({
            "solid_findings": [
                {"principle": "S", "severity": "warn", "location": "§1",
                 "description": "SRP", "suggestion": "x"},
                {"principle": "D", "severity": "warn", "location": "§2",
                 "description": "DIP", "suggestion": "y"},
            ],
            "overall_solid_score": "warn",
            "summary": "",
        })
        provider.complete.return_value = MagicMock(text=payload)
        checker = BatchLlmSolidChecker(provider, principle_filter="S")
        findings = checker.check("spec", "SPEC-0001")
        assert all(f.principle == "S" for f in findings)

    def test_error_returns_info_finding(self):
        provider = MagicMock()
        provider.complete.side_effect = Exception("fail")
        checker = BatchLlmSolidChecker(provider)
        findings = checker.check("spec", "SPEC-0001")
        assert len(findings) == 1
        assert findings[0].severity == "info"


# ─── Named Factory Functions ───────────────────────────────────────────────────

class TestCheckerFactories:
    def test_srp_checker_principle(self):
        assert SrpChecker(MagicMock()).principle == "S"

    def test_ocp_checker_principle(self):
        assert OcpChecker(MagicMock()).principle == "O"

    def test_lsp_checker_principle(self):
        assert LspChecker(MagicMock()).principle == "L"

    def test_isp_checker_principle(self):
        assert IspChecker(MagicMock()).principle == "I"

    def test_dip_checker_principle(self):
        assert DipChecker(MagicMock()).principle == "D"


# ─── SolidAnalyzer ────────────────────────────────────────────────────────────

class TestSolidAnalyzer:
    def test_empty_checkers_returns_compliant(self):
        analyzer = SolidAnalyzer([])
        report = analyzer.analyze("text", "SPEC-0001")
        assert report.overall_solid_score == "compliant"
        assert report.findings == []

    def test_null_checker_returns_compliant(self):
        analyzer = SolidAnalyzer([NullSolidChecker()])
        report = analyzer.analyze("text", "SPEC-0001", artifact_type="contract")
        assert report.artifact_type == "contract"
        assert report.overall_solid_score == "compliant"

    def test_violation_finding_sets_violation_score(self):
        checker = MagicMock()
        checker.check.return_value = [_finding("S", "violation")]
        analyzer = SolidAnalyzer([checker])
        report = analyzer.analyze("text", "SPEC-0001")
        assert report.overall_solid_score == "violation"
        assert report.has_violations()

    def test_checker_exception_caught_and_added_as_error_finding(self):
        class BrokenChecker:
            principle = "S"
            def check(self, *_):
                raise RuntimeError("broken")

        analyzer = SolidAnalyzer([BrokenChecker()])
        report = analyzer.analyze("text", "SPEC-0001")
        assert len(report.findings) == 1
        assert report.findings[0].severity == "info"

    def test_multiple_checkers_aggregated(self):
        c1 = MagicMock()
        c1.check.return_value = [_finding("S", "warn")]
        c2 = MagicMock()
        c2.check.return_value = [_finding("D", "violation")]
        analyzer = SolidAnalyzer([c1, c2])
        report = analyzer.analyze("text", "SPEC-0001")
        assert len(report.findings) == 2
        assert report.overall_solid_score == "violation"

    def test_all_principle_checker_error_uses_s(self):
        class AllChecker:
            principle = "ALL"
            def check(self, *_):
                raise RuntimeError("fail")

        analyzer = SolidAnalyzer([AllChecker()])
        report = analyzer.analyze("text", "SPEC-0001")
        assert report.findings[0].principle == "S"


# ─── _compute_score ───────────────────────────────────────────────────────────

class TestComputeScore:
    def test_no_findings_is_compliant(self):
        assert _compute_score([]) == "compliant"

    def test_only_info_is_compliant(self):
        assert _compute_score([_finding("S", "info")]) == "compliant"

    def test_warn_finding_is_warn(self):
        assert _compute_score([_finding("S", "warn")]) == "warn"

    def test_violation_overrides_warn(self):
        assert _compute_score([_finding("S", "warn"), _finding("D", "violation")]) == "violation"


# ─── _build_summary ───────────────────────────────────────────────────────────

class TestBuildSummary:
    def test_compliant_message(self):
        assert "kein" in _build_summary([], "compliant").lower()

    def test_violation_count_in_summary(self):
        summary = _build_summary([_finding("S", "violation"), _finding("D", "violation")], "violation")
        assert "2" in summary

    def test_warn_count_in_summary(self):
        summary = _build_summary([_finding("S", "warn")], "warn")
        assert "1" in summary


# ─── _parse_llm_response ──────────────────────────────────────────────────────

class TestParseLlmResponse:
    def test_valid_json_returns_findings(self):
        payload = json.dumps({
            "solid_findings": [{
                "principle": "S",
                "severity": "violation",
                "location": "§1",
                "description": "Too big",
                "suggestion": "Split",
            }],
            "overall_solid_score": "violation",
            "summary": "One issue",
        })
        findings, score, summary = _parse_llm_response(payload)
        assert len(findings) == 1
        assert score == "violation"
        assert summary == "One issue"

    def test_invalid_json_raises_instead_of_faking_compliance(self):
        """Vorher: [], "compliant" – eine unauswertbare Antwort sah aus wie
        eine bestandene Pruefung. Jetzt fliegt sie in den Checker-Fehler-Pfad
        (CON-0045 INV-04)."""
        from sdd_cli.solid import SolidResponseError

        with pytest.raises(SolidResponseError, match="nicht als JSON parsebar"):
            _parse_llm_response("NOT JSON")

    def test_unknown_principle_skipped(self):
        payload = json.dumps({
            "solid_findings": [{"principle": "X", "severity": "warn",
                                "location": "§1", "description": "d", "suggestion": "s"}],
            "overall_solid_score": "warn",
            "summary": "",
        })
        findings, _, _ = _parse_llm_response(payload)
        assert findings == []

    def test_invalid_severity_defaults_to_info(self):
        payload = json.dumps({
            "solid_findings": [{"principle": "S", "severity": "CRITICAL",
                                "location": "§1", "description": "d", "suggestion": "s"}],
            "overall_solid_score": "warn",
            "summary": "",
        })
        findings, _, _ = _parse_llm_response(payload)
        assert findings[0].severity == "info"

    def test_invalid_score_recomputed(self):
        payload = json.dumps({
            "solid_findings": [{"principle": "D", "severity": "violation",
                                "location": "§1", "description": "d", "suggestion": "s"}],
            "overall_solid_score": "UNKNOWN",
            "summary": "",
        })
        _, score, _ = _parse_llm_response(payload)
        assert score == "violation"

    def test_markdown_json_block_extracted(self):
        payload = '```json\n{"solid_findings": [], "overall_solid_score": "compliant", "summary": "ok"}\n```'
        findings, score, _ = _parse_llm_response(payload)
        assert findings == []
        assert score == "compliant"


# ─── _extract_json ────────────────────────────────────────────────────────────

class TestExtractJson:
    def test_extracts_from_markdown_code_block(self):
        text = '```json\n{"key": "value"}\n```'
        assert _extract_json(text) == '{"key": "value"}'

    def test_extracts_bare_json_object(self):
        text = 'prefix {"key": "value"} suffix'
        assert _extract_json(text) == '{"key": "value"}'

    def test_plain_text_returned_stripped(self):
        text = "  no json here  "
        assert _extract_json(text) == "no json here"


# ─── Prompt Builders ──────────────────────────────────────────────────────────

class TestPromptBuilders:
    def test_batch_prompt_contains_artifact_id(self):
        prompt = _build_batch_prompt("spec content", "SPEC-0001", None)
        assert "SPEC-0001" in prompt
        assert "SOLID" in prompt

    def test_batch_prompt_with_filter_mentions_principle(self):
        prompt = _build_batch_prompt("content", "SPEC-0001", "S")
        assert "Single Responsibility" in prompt

    def test_single_principle_prompt_contains_principle(self):
        prompt = _build_single_principle_prompt("content", "SPEC-0001", "O", "Open/Closed")
        assert "O" in prompt
        assert "Open/Closed" in prompt
        assert "SPEC-0001" in prompt


# ─── create_analyzer ──────────────────────────────────────────────────────────

class TestCreateAnalyzer:
    def test_disabled_solid_gate_returns_null_checker(self):
        from sdd_cli.solid import create_analyzer
        cfg = _make_config({"solid_gate": {"enabled": False}})
        analyzer = create_analyzer(cfg)
        assert isinstance(analyzer, SolidAnalyzer)
        report = analyzer.analyze("text", "SPEC-0001")
        assert report.findings == []
