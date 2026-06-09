"""TST-0190 – sdd evaluate JSON-Output: tier_summary Schema (Contract)
Spec: SPEC-0042 · Contract: CON-0162
"""
import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from sdd_cli.evaluator import EvaluationReport, ScenarioResult, ScenarioRun
from sdd_cli.main import cli


def _make_scenario(hol_id: str, priority: str, passed: bool) -> ScenarioResult:
    s = ScenarioResult(hol_id=hol_id, title=hol_id, contract="CON-TEST")
    s.runs.append(ScenarioRun(
        run=1, passed=passed,
        request={}, response_status=None, response_body=None,
        llm_verdict="pass" if passed else "fail",
        llm_reasoning="ok" if passed else "fail",
    ))
    return s


def _invoke_json(report: EvaluationReport, mock_cfg: MagicMock) -> dict:
    """Invoke sdd evaluate --json, extract and parse the JSON from output."""
    runner = CliRunner()
    with patch("sdd_cli.main._ensure_project", return_value=mock_cfg), \
         patch("sdd_cli.main.run_evaluation", return_value=report), \
         patch("sdd_cli.main.persist_report", return_value=None):
        result = runner.invoke(cli, [
            "evaluate", "--base-url", "http://x", "--json", "--no-save"
        ])
    assert "{" in result.output, f"Kein JSON in Output: {result.output!r}"
    return json.loads(result.output[result.output.index("{"):])


@pytest.fixture()
def mock_cfg(tmp_path):
    cfg = MagicMock()
    cfg.root = tmp_path
    cfg.holdout_dir = tmp_path / "holdout"
    cfg.holdout_dir.mkdir()
    return cfg


# ── TC-01: --output-json enthält tier_summary ─────────────────────────────────

def test_json_output_contains_tier_summary(mock_cfg):
    report = EvaluationReport(timestamp="2026-01-01T00:00:00Z", base_url="http://x")
    report.scenarios.append(_make_scenario("HOL-C1", "critical", True))
    report.scenarios.append(_make_scenario("HOL-N1", "normal", False))
    data = _invoke_json(report, mock_cfg)
    assert "tier_summary" in data, f"tier_summary fehlt in: {list(data.keys())}"


# ── TC-02: tier_summary enthält alle drei Tier-Keys ──────────────────────────

def test_tier_summary_has_all_three_tiers(mock_cfg):
    report = EvaluationReport(timestamp="2026-01-01T00:00:00Z", base_url="http://x")
    data = _invoke_json(report, mock_cfg)
    ts = data["tier_summary"]
    assert "critical" in ts
    assert "normal" in ts
    assert "edge-case" in ts


# ── TC-03: Szenarien enthalten priority-Feld ──────────────────────────────────

def test_scenarios_contain_priority_field(mock_cfg):
    report = EvaluationReport(timestamp="2026-01-01T00:00:00Z", base_url="http://x")
    report.scenarios.append(_make_scenario("HOL-C1", "critical", True))
    data = _invoke_json(report, mock_cfg)
    scenario = data["scenarios"][0]
    assert "priority" in scenario, f"priority fehlt: {list(scenario.keys())}"
    assert scenario["priority"] in ("critical", "normal", "edge-case")


# ── TC-04: Szenarien enthalten task_delta (null oder string) ──────────────────

def test_scenarios_contain_task_delta_field(mock_cfg):
    report = EvaluationReport(timestamp="2026-01-01T00:00:00Z", base_url="http://x")
    report.scenarios.append(_make_scenario("HOL-N1", "normal", False))
    data = _invoke_json(report, mock_cfg)
    scenario = data["scenarios"][0]
    assert "task_delta" in scenario
    assert scenario["task_delta"] is None or isinstance(scenario["task_delta"], str)


# ── TC-05: tier_summary Summen-Invariante ─────────────────────────────────────

def test_tier_summary_sum_invariant(mock_cfg):
    report = EvaluationReport(timestamp="2026-01-01T00:00:00Z", base_url="http://x")
    report.scenarios.append(_make_scenario("HOL-C1", "critical", True))
    report.scenarios.append(_make_scenario("HOL-C2", "critical", False))
    report.scenarios.append(_make_scenario("HOL-N1", "normal", True))
    data = _invoke_json(report, mock_cfg)
    ts = data["tier_summary"]
    for tier, counts in ts.items():
        total = counts["passed"] + counts["failed"] + counts.get("skipped", 0)
        expected = sum(1 for s in report.scenarios
                       if getattr(s, "priority", "normal") == tier)
        assert total == expected, f"Tier {tier}: {total} != {expected}"


# ── TC-06: Fehlender priority → Fallback "normal" ────────────────────────────

def test_missing_priority_fallback_in_json(mock_cfg):
    report = EvaluationReport(timestamp="2026-01-01T00:00:00Z", base_url="http://x")
    s = ScenarioResult(hol_id="HOL-X", title="X", contract="CON-X")
    s.runs.append(ScenarioRun(
        run=1, passed=True, request={}, response_status=None,
        response_body=None, llm_verdict="pass", llm_reasoning="ok"
    ))
    report.scenarios.append(s)
    data = _invoke_json(report, mock_cfg)
    scenario = data["scenarios"][0]
    assert scenario.get("priority", "normal") == "normal"
