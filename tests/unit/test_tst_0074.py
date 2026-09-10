# TST-0074 – Docker Spec Lifecycle (CON-0065)
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from sdd_cli.dev_container import (
    ContainerRuntime,
    DevContainerManager,
    branch_name,
    container_name,
)


@pytest.fixture
def cfg(tmp_path):
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "config.yaml").write_text("docker:\n  image: sdd-dev:latest\n")
    from sdd_cli.config import SddConfig
    return SddConfig(root=tmp_path, raw={"docker": {"image": "sdd-dev:latest"}})


def _mock_runtime(status: str | None = None) -> MagicMock:
    rt = MagicMock(spec=ContainerRuntime)
    rt.inspect_status.return_value = status
    rt.exec_in.return_value = MagicMock(returncode=0)
    return rt


def _mgr(cfg, runtime=None):
    return DevContainerManager(cfg, runtime=runtime or _mock_runtime())


# ── Naming conventions ────────────────────────────────────────────────────────

def test_container_name():
    assert container_name("SPEC-0021") == "sdd-dev-spec-0021"


def test_branch_name():
    assert branch_name("SPEC-0021") == "dev/SPEC-0021"


# ── TC-01: Normaler Start ─────────────────────────────────────────────────────

def test_tc01_normal_start(cfg):
    rt = _mock_runtime(status=None)
    with (
        patch("sdd_cli.dev_container._branch_exists", return_value=False),
        patch("sdd_cli.dev_container._git") as mock_git,
    ):
        _mgr(cfg, rt).start("SPEC-0021")

    rt.run_container.assert_called_once_with(
        "sdd-dev-spec-0021",
        "sdd-dev:latest",
        volume=f"{cfg.root}:/workspace",
        env={"SPEC_ID": "SPEC-0021", "GIT_BRANCH": "dev/SPEC-0021"},
    )
    # CON-0065 G-01 v0.3.0: aus dem aktuellen HEAD, nicht fest aus main.
    mock_git.assert_any_call(["checkout", "-b", "dev/SPEC-0021"])


# ── TC-02: Idempotenz – Container läuft bereits ───────────────────────────────

def test_tc02_idempotenz_running(cfg, capsys):
    rt = _mock_runtime(status="running")
    _mgr(cfg, rt).start("SPEC-0021")

    rt.run_container.assert_not_called()
    err = capsys.readouterr().err
    assert "läuft bereits" in err


# ── TC-03: Gestoppter Container wird wieder gestartet ─────────────────────────

def test_tc03_restart_stopped_container(cfg):
    rt = _mock_runtime(status="exited")
    _mgr(cfg, rt).start("SPEC-0021")

    rt.start.assert_called_once_with("sdd-dev-spec-0021")
    rt.run_container.assert_not_called()


# ── TC-04: Atomarer Rollback bei Runtime-Fehler ────────────────────────────────

def test_tc04_rollback_on_docker_failure(cfg):
    rt = _mock_runtime(status=None)
    rt.run_container.side_effect = subprocess.CalledProcessError(1, "docker run")

    with (
        patch("sdd_cli.dev_container._branch_exists", return_value=False),
        patch("sdd_cli.dev_container._git") as mock_git,
        pytest.raises(SystemExit),
    ):
        _mgr(cfg, rt).start("SPEC-0021")

    branch_delete_calls = [c for c in mock_git.call_args_list if "-D" in c.args[0]]
    assert branch_delete_calls, "Branch wurde bei Runtime-Fehler nicht zurückgerollt"


# ── TC-05: sdd dev exec leitet Output weiter ──────────────────────────────────

def test_tc05_exec_forwards_output(cfg):
    rt = _mock_runtime(status="running")
    rt.exec_in.return_value = MagicMock(returncode=0)

    with pytest.raises(SystemExit) as exc_info:
        _mgr(cfg, rt).exec_cmd("SPEC-0021", ["pytest", "tests/", "-x"])

    rt.exec_in.assert_called_once_with("sdd-dev-spec-0021", ["pytest", "tests/", "-x"])
    assert exc_info.value.code == 0


# ── TC-06: sdd dev exec – Container nicht aktiv ──────────────────────────────

def test_tc06_exec_no_container(cfg, capsys):
    rt = _mock_runtime(status=None)

    with pytest.raises(SystemExit) as exc_info:
        _mgr(cfg, rt).exec_cmd("SPEC-0021", ["pytest"])

    assert exc_info.value.code != 0
    assert "läuft nicht" in capsys.readouterr().err


# ── TC-07: sdd dev close ──────────────────────────────────────────────────────

def test_tc07_close_stops_and_removes(cfg):
    rt = _mock_runtime()
    _mgr(cfg, rt).close("SPEC-0021")

    rt.stop.assert_called_once_with("sdd-dev-spec-0021")
    rt.rm.assert_called_once_with("sdd-dev-spec-0021")


# ── TC-08: sdd dev close --delete-branch ─────────────────────────────────────

def test_tc08_close_deletes_branch(cfg):
    rt = _mock_runtime()
    with (
        patch("sdd_cli.dev_container._branch_exists", return_value=True),
        patch("sdd_cli.dev_container._git") as mock_git,
    ):
        _mgr(cfg, rt).close("SPEC-0021", delete_branch=True)

    mock_git.assert_called_with(["branch", "-D", "dev/SPEC-0021"])
