"""Die Finalisierung räumt den Dev-Container auf, und zwar nur nach grünen Tests (#121).

CON-0065 G-06 in der Fassung v0.4.0. Vorher beschrieb G-06 den entfernten Befehl
`sdd dev close`. Das tatsächliche Verhalten stand nur im Code: `close` nach grünen
Tests, stehen lassen nach roten (#65). Den zweiten Fall prüfte kein Test.
"""
from __future__ import annotations

import inspect
from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch


def _finalisieren(tmp_path, *, test_rc: int, compose: str = ""):
    from sdd_cli import finalize
    from sdd_cli.config import SddConfig

    cfg = SddConfig(root=tmp_path, raw={
        "docker": {"compose_file": compose},
        "test_runner": {"command": "pytest"},
        "orchestrator": {"build_command": ""},
    })

    def run(befehl, *a, **kw):
        return CompletedProcess(befehl, test_rc,
                                stdout="1 passed" if test_rc == 0 else "1 failed", stderr="")

    runtime = MagicMock()
    runtime.inspect_status.return_value = "running"
    runtime.cli.return_value = "podman"
    mgr = MagicMock()
    with patch.object(finalize, "get_runtime", return_value=runtime), \
         patch.object(finalize, "DevContainerManager", return_value=mgr), \
         patch.object(finalize, "_git", return_value=CompletedProcess([], 0, stdout="abc", stderr="")), \
         patch.object(finalize, "save_test_result"), \
         patch.object(finalize.SpecFinalizer, "_run_compliance_check", return_value=None), \
         patch.object(finalize.SpecFinalizer, "_create_pr", return_value=("https://pr/1", None, None)), \
         patch.object(finalize.subprocess, "run", side_effect=run):
        report = finalize.SpecFinalizer(cfg).run("SPEC-0021", no_commit=True)
    return report, mgr


def test_gruene_tests_raeumen_den_container_auf(tmp_path):
    report, mgr = _finalisieren(tmp_path, test_rc=0)
    assert report.tests_passed
    mgr.close.assert_called_once_with("SPEC-0021")


def test_rote_tests_lassen_den_container_stehen(tmp_path):
    """Der Fall, den bisher kein Test prüfte."""
    report, mgr = _finalisieren(tmp_path, test_rc=1)
    assert not report.tests_passed
    mgr.close.assert_not_called()


def test_compose_stack_bleibt_unberuehrt(tmp_path):
    _, mgr = _finalisieren(tmp_path, test_rc=0, compose="compose.yml")
    mgr.close.assert_not_called()


def test_close_loescht_keinen_branch_mehr():
    """`delete_branch` bediente das entfernte `sdd dev close --delete-branch`."""
    from sdd_cli.dev_container import DevContainerManager

    assert "delete_branch" not in inspect.signature(DevContainerManager.close).parameters


def test_kein_exec_weg_mehr():
    """`exec_cmd()` und `exec_in` bedienten das entfernte `sdd dev exec`."""
    from sdd_cli.dev_container import ContainerRuntime, DevContainerManager

    assert not hasattr(DevContainerManager, "exec_cmd")
    assert not hasattr(ContainerRuntime, "exec_in")
