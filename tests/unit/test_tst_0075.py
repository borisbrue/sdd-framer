# TST-0075 – sdd dev pr Validierungsgatter (CON-0066)
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from sdd_cli.config import SddConfig
from sdd_cli.dev_container import DevContainerManager, save_test_result


@pytest.fixture
def cfg(tmp_path):
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "config.yaml").write_text("")
    return SddConfig(root=tmp_path, raw={})


def _mgr(cfg):
    return DevContainerManager(cfg)


def _write_test_result(cfg, spec_id, result, passed, total):
    save_test_result(cfg, spec_id, passed=passed, total=total)


# ── TC-01: Erfolgreiches Gate ─────────────────────────────────────────────────

def test_tc01_successful_gate_creates_pr(cfg):
    _write_test_result(cfg, "SPEC-0021", "passed", 5, 5)
    mock_strategy = MagicMock()

    with (
        patch("sdd_cli.dev_container._run") as mock_run,
        patch("sdd_cli.dev_container._git") as mock_git,
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        mock_git.return_value = MagicMock(returncode=0, stdout="")
        mgr = DevContainerManager(cfg, pr_strategy=mock_strategy)
        mgr.pr("SPEC-0021")

    mock_strategy.create.assert_called_once_with("SPEC-0021", cfg)


# ── TC-02: Gate blockiert – Tests fehlgeschlagen ──────────────────────────────

def test_tc02_gate_blocks_on_failed_tests(cfg, capsys):
    _write_test_result(cfg, "SPEC-0021", "failed", 3, 5)

    with pytest.raises(SystemExit) as exc_info:
        _mgr(cfg).pr("SPEC-0021")

    assert exc_info.value.code != 0
    assert "nicht grün" in capsys.readouterr().err


# ── TC-03: Gate blockiert – sdd validate Fehler ───────────────────────────────

def test_tc03_gate_blocks_on_validate_error(cfg, capsys):
    _write_test_result(cfg, "SPEC-0021", "passed", 5, 5)

    with (
        patch("sdd_cli.dev_container._run") as mock_run,
        patch("sdd_cli.dev_container._git") as mock_git,
        pytest.raises(SystemExit) as exc_info,
    ):
        mock_run.return_value = MagicMock(returncode=1, stdout="✗ Fehler gefunden")
        mock_git.return_value = MagicMock(returncode=0, stdout="")
        _mgr(cfg).pr("SPEC-0021")

    assert exc_info.value.code != 0
    assert "validate" in capsys.readouterr().err.lower()


# ── TC-04: Warnung bei uncommitted changes – kein Abbruch ────────────────────

def test_tc04_warn_on_uncommitted_no_abort(cfg, capsys):
    _write_test_result(cfg, "SPEC-0021", "passed", 5, 5)
    mock_strategy = MagicMock()

    with (
        patch("sdd_cli.dev_container._run") as mock_run,
        patch("sdd_cli.dev_container._git") as mock_git,
    ):
        def git_side(args, **_):
            m = MagicMock()
            m.returncode = 0
            m.stdout = "M somefile.py" if args == ["status", "--porcelain"] else ""
            return m

        mock_run.return_value = MagicMock(returncode=0, stdout="")
        mock_git.side_effect = git_side
        mgr = DevContainerManager(cfg, pr_strategy=mock_strategy)
        mgr.pr("SPEC-0021")

    err = capsys.readouterr().err
    assert "Uncommitted" in err
    mock_strategy.create.assert_called_once()


# ── TC-05: Gate blockiert – kein Test-Ergebnis ───────────────────────────────

def test_tc05_gate_blocks_no_test_result(cfg, capsys):
    with pytest.raises(SystemExit) as exc_info:
        _mgr(cfg).pr("SPEC-0021")

    assert exc_info.value.code != 0
    assert "Kein Test-Ergebnis" in capsys.readouterr().err
