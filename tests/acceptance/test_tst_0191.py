"""TST-0191 – sdd holdout run --smoke Selbsttest (Acceptance)

Bis #112 liefen die Tests ueber den Altnamen `sdd evaluate --smoke`: dessen
Entfernt-Stub reicht --smoke weiter an denselben Selbsttest. Geprueft wurde
also das Richtige, aufgerufen aber ein Befehl, den es offiziell nicht mehr gibt.
Spec: SPEC-0042 · Contract: CON-0163
"""
import time
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from sdd_cli.main import cli


@pytest.fixture()
def mock_cfg(tmp_path):
    cfg = MagicMock()
    cfg.root = tmp_path
    cfg.holdout_dir = tmp_path / "holdout"
    cfg.holdout_dir.mkdir()
    return cfg


# ── TC-01: --smoke läuft durch, Exit 0 ────────────────────────────────────────

def test_smoke_exits_zero(mock_cfg):
    runner = CliRunner()
    with patch("sdd_cli.main._ensure_project", return_value=mock_cfg):
        result = runner.invoke(cli, ["holdout", "run", "--smoke"])
    assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"


# ── TC-02–04: Ausgabe enthält alle drei Checks ────────────────────────────────

def test_smoke_reports_tier_sort_ok(mock_cfg):
    runner = CliRunner()
    with patch("sdd_cli.main._ensure_project", return_value=mock_cfg):
        result = runner.invoke(cli, ["holdout", "run", "--smoke"])
    assert "Tier-Sortierung" in result.output, result.output


def test_smoke_reports_failfast_critical_normal_ok(mock_cfg):
    runner = CliRunner()
    with patch("sdd_cli.main._ensure_project", return_value=mock_cfg):
        result = runner.invoke(cli, ["holdout", "run", "--smoke"])
    assert "critical" in result.output.lower(), result.output


def test_smoke_reports_failfast_normal_edgecase_ok(mock_cfg):
    runner = CliRunner()
    with patch("sdd_cli.main._ensure_project", return_value=mock_cfg):
        result = runner.invoke(cli, ["holdout", "run", "--smoke"])
    assert "normal" in result.output.lower() or "edge" in result.output.lower(), result.output


# ── TC-05: Laufzeit < 2 s ─────────────────────────────────────────────────────

def test_smoke_runs_under_two_seconds(mock_cfg):
    runner = CliRunner()
    with patch("sdd_cli.main._ensure_project", return_value=mock_cfg):
        t0 = time.monotonic()
        runner.invoke(cli, ["holdout", "run", "--smoke"])
        elapsed = time.monotonic() - t0
    assert elapsed < 2.0, f"--smoke dauerte {elapsed:.2f}s (Limit: 2.0s)"


# ── TC-06: Kein HTTP-Aufruf ───────────────────────────────────────────────────

def test_smoke_makes_no_http_calls(mock_cfg):
    """--smoke darf keine HTTP-Verbindung aufbauen."""
    from unittest.mock import patch as _patch

    import sdd_cli.holdout_runner as runner_mod

    runner = CliRunner()
    with patch("sdd_cli.main._ensure_project", return_value=mock_cfg), \
         _patch.object(runner_mod, "ActionExecutor") as mock_executor_cls:
        result = runner.invoke(cli, ["holdout", "run", "--smoke"])

    assert result.exit_code == 0, result.output
    # Vorher stand hier `assert_not_called(), "…"` — ein Tupel; die Meldung
    # wurde nie ausgegeben.
    mock_executor_cls.assert_not_called()
