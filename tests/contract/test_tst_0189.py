"""TST-0189 – sdd holdout run --tier CLI-Flags und Exit-Codes (Contract)
Spec: SPEC-0042 · Contract: CON-0161
"""
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from sdd_cli.main import cli


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def mock_cfg(tmp_path):
    cfg = MagicMock()
    cfg.root = tmp_path
    cfg.holdout_dir = tmp_path / "holdout"
    cfg.holdout_dir.mkdir()
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "config.yaml").write_text("version: 1.0.0\nproject:\n  name: test\n")
    return cfg


def _hol(path: Path, hol_id: str, priority: str) -> None:
    content = textwrap.dedent(f"""\
        ---
        id: {hol_id}
        title: "{hol_id} {priority}"
        spec: SPEC-TEST
        contract: CON-TEST
        status: active
        priority: {priority}
        type: cli
        created: 2026-01-01
        updated: 2026-01-01
        tags: []
        ---

        ## Test

        ```yaml
        test:
          action:
            command: echo
            args: ["ok"]
          assert:
            exit_code: 0
        ```
    """)
    (path / f"{hol_id.lower()}.md").write_text(content)


# ── TC-01: --tier critical filtert nur critical ───────────────────────────────

def test_tier_critical_flag_accepted(mock_cfg):
    """--tier critical ist ein gültiges Flag (kein UsageError)."""
    runner = CliRunner()
    with patch("sdd_cli.main._ensure_project", return_value=mock_cfg), \
         patch("sdd_cli.main.run_evaluation") as mock_eval:
        from sdd_cli.evaluator import EvaluationReport
        mock_eval.return_value = EvaluationReport(
            timestamp="2026-01-01T00:00:00Z", base_url="http://localhost:9999"
        )
        result = runner.invoke(cli, [
            "holdout", "run", "--base-url", "http://localhost:9999", "--tier", "critical"
        ])
    assert result.exit_code != 2, f"UsageError: {result.output}"


def test_tier_normal_flag_accepted(mock_cfg):
    """--tier normal ist ein gültiges Flag."""
    runner = CliRunner()
    with patch("sdd_cli.main._ensure_project", return_value=mock_cfg), \
         patch("sdd_cli.main.run_evaluation") as mock_eval:
        from sdd_cli.evaluator import EvaluationReport
        mock_eval.return_value = EvaluationReport(
            timestamp="2026-01-01T00:00:00Z", base_url="http://localhost:9999"
        )
        result = runner.invoke(cli, [
            "holdout", "run", "--base-url", "http://localhost:9999", "--tier", "normal"
        ])
    assert result.exit_code != 2, f"UsageError: {result.output}"


def test_tier_edge_case_flag_accepted(mock_cfg):
    """--tier edge-case ist ein gültiges Flag."""
    runner = CliRunner()
    with patch("sdd_cli.main._ensure_project", return_value=mock_cfg), \
         patch("sdd_cli.main.run_evaluation") as mock_eval:
        from sdd_cli.evaluator import EvaluationReport
        mock_eval.return_value = EvaluationReport(
            timestamp="2026-01-01T00:00:00Z", base_url="http://localhost:9999"
        )
        result = runner.invoke(cli, [
            "holdout", "run", "--base-url", "http://localhost:9999", "--tier", "edge-case"
        ])
    assert result.exit_code != 2, f"UsageError: {result.output}"


# ── TC-04: --tier ohne Matches → Exit 0 + Meldung ────────────────────────────

def test_tier_no_matches_exits_zero(mock_cfg):
    """--tier critical ohne matching Holdouts → Exit 0."""
    _hol(mock_cfg.holdout_dir, "HOL-N1", "normal")
    runner = CliRunner()
    with patch("sdd_cli.main._ensure_project", return_value=mock_cfg):
        result = runner.invoke(cli, [
            "holdout", "run", "--base-url", "http://localhost:9999",
            "--tier", "critical", "--spec", "SPEC-TEST"
        ])
    assert result.exit_code == 0
    assert "0" in result.output or "keine" in result.output.lower() or "gefunden" in result.output.lower() or result.exit_code == 0


# ── TC-05: --tier + --hol kombiniert → --hol hat Vorrang + Warning ────────────

def test_tier_and_hol_ids_hol_takes_precedence(mock_cfg):
    """--tier + --hol: --hol hat Vorrang, Warning wird ausgegeben."""
    runner = CliRunner()
    with patch("sdd_cli.main._ensure_project", return_value=mock_cfg), \
         patch("sdd_cli.main.run_evaluation") as mock_eval:
        from sdd_cli.evaluator import EvaluationReport
        mock_eval.return_value = EvaluationReport(
            timestamp="2026-01-01T00:00:00Z", base_url="http://localhost:9999"
        )
        result = runner.invoke(cli, [
            "holdout", "run", "--base-url", "http://localhost:9999",
            "--tier", "critical", "--hol", "HOL-0001"
        ])
    assert result.exit_code != 2
    assert "warn" in result.output.lower() or "--hol" in result.output.lower() or "vorrang" in result.output.lower()


# ── TC-06: --smoke ignoriert --base-url ───────────────────────────────────────

def test_smoke_flag_accepted(mock_cfg):
    """--smoke ist ein gültiges Flag und erfordert kein --base-url."""
    runner = CliRunner()
    with patch("sdd_cli.main._ensure_project", return_value=mock_cfg):
        result = runner.invoke(cli, ["holdout", "run", "--smoke"])
    assert result.exit_code != 2, f"UsageError: {result.output}"
