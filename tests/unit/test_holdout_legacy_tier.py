"""Legacy-Holdouts: --tier und priority waren wirkungslos.

Tier-Filter, priority-Uebernahme und Fail-Fast existierten nur im
strukturierten Pfad (SPEC-0042 FR-01/FR-02/FR-04). _run_legacy_evaluation
bekam den Filter gar nicht erst uebergeben: `--tier critical` fuehrte alle
Szenarien aus, und jedes Ergebnis trug priority "normal", womit tier_summary
im Report die Staffelung nicht auswerten konnte.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

from sdd_cli.config import SddConfig
from sdd_cli.evaluator import EvaluationReport, ScenarioResult, ScenarioRun


class _Doc:
    def __init__(self, hol_id: str, priority: str) -> None:
        self.frontmatter = {"id": hol_id, "title": hol_id, "contract": "CON-0001",
                            "priority": priority, "spec": "SPEC-0001"}
        self.body = "Beschreibung des Szenarios."


def _cfg() -> SddConfig:
    return SddConfig(root=Path("/tmp"), raw={})


def _lauf(docs, tier_filter=None, ergebnisse=None):
    """Fuehrt _run_legacy_evaluation mit gemocktem HTTP/LLM aus."""
    from sdd_cli import evaluator

    reihenfolge: list[str] = []

    def fake_once(i, title, body, base_url, http, provider):
        reihenfolge.append(title)
        passed = (ergebnisse or {}).get(title, True)
        return ScenarioRun(run=i, passed=passed, request={}, response_status=200,
                           response_body="", llm_verdict="pass" if passed else "fail",
                           llm_reasoning="")

    with patch.object(evaluator, "_run_scenario_once", fake_once), \
         patch("sdd_cli.llm.get_completion_provider", return_value=object()):
        report = evaluator._run_legacy_evaluation(
            _cfg(), "http://localhost:8000", docs, tier_filter=tier_filter)
    return report, reihenfolge


class TestTierFilter:
    def test_signature_accepts_tier_filter(self):
        from sdd_cli.evaluator import _run_legacy_evaluation
        assert "tier_filter" in inspect.signature(_run_legacy_evaluation).parameters

    def test_run_evaluation_passes_it_through(self):
        from sdd_cli import evaluator
        src = inspect.getsource(evaluator.run_evaluation)
        assert "tier_filter=tier_filter)" in src or "tier_filter=tier_filter," in src

    def test_only_the_requested_tier_runs(self):
        """Der gemeldete Fall: --tier critical fuehrte alle 12 Szenarien aus."""
        docs = [_Doc("HOL-0001", "critical"), _Doc("HOL-0002", "normal"),
                _Doc("HOL-0003", "edge-case"), _Doc("HOL-0009", "critical")]
        report, gelaufen = _lauf(docs, tier_filter="critical")

        assert sorted(gelaufen) == ["HOL-0001", "HOL-0009"]
        assert len(report.scenarios) == 2

    def test_without_filter_everything_runs(self):
        docs = [_Doc("HOL-0001", "critical"), _Doc("HOL-0002", "normal")]
        _, gelaufen = _lauf(docs)
        assert len(gelaufen) == 2


class TestPriorityIsCarried:
    def test_priority_reaches_the_result(self):
        """Vorher trug jedes Ergebnis 'normal' – tier_summary war damit blind."""
        report, _ = _lauf([_Doc("HOL-0001", "critical")])
        assert report.scenarios[0].priority == "critical"

    def test_tier_summary_counts_the_right_bucket(self):
        docs = [_Doc("HOL-0001", "critical"), _Doc("HOL-0003", "edge-case")]
        report, _ = _lauf(docs)
        summary = report.to_dict()["tier_summary"]
        assert summary["critical"]["passed"] == 1
        assert summary["edge-case"]["passed"] == 1
        assert summary["normal"]["passed"] == 0

    def test_critical_runs_before_normal(self):
        docs = [_Doc("HOL-0003", "edge-case"), _Doc("HOL-0002", "normal"),
                _Doc("HOL-0001", "critical")]
        _, gelaufen = _lauf(docs)
        assert gelaufen == ["HOL-0001", "HOL-0002", "HOL-0003"]


class TestFailFast:
    def test_critical_failure_skips_the_rest(self):
        docs = [_Doc("HOL-0001", "critical"), _Doc("HOL-0002", "normal"),
                _Doc("HOL-0003", "edge-case")]
        report, gelaufen = _lauf(docs, ergebnisse={"HOL-0001": False})

        assert gelaufen == ["HOL-0001"], "normal und edge-case muessen entfallen"
        assert len(report.scenarios) == 3, "uebersprungene erscheinen im Report"

    def test_normal_failure_skips_only_edge_case(self):
        docs = [_Doc("HOL-0001", "critical"), _Doc("HOL-0002", "normal"),
                _Doc("HOL-0003", "edge-case")]
        _, gelaufen = _lauf(docs, ergebnisse={"HOL-0002": False})
        assert gelaufen == ["HOL-0001", "HOL-0002"]

    def test_no_fail_fast_when_a_tier_is_selected(self):
        """Mit --tier laeuft ohnehin nur eine Stufe – Fail-Fast waere sinnlos."""
        docs = [_Doc("HOL-0001", "critical"), _Doc("HOL-0009", "critical")]
        _, gelaufen = _lauf(docs, tier_filter="critical",
                            ergebnisse={"HOL-0001": False})
        assert len(gelaufen) == 2
