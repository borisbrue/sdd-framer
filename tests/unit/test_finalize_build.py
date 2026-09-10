"""Der Build laeuft in der Finalisierung, vor den Tests (#111).

SPEC-0026 hat den Build-Schritt aus der Orchestrator-Schleife entfernt, ohne ihn in
der neuen, gemeinsamen Finalisierung wieder anzubinden. --build-cmd und
orchestrator.build_command wurden seither still ignoriert; CON-0012 fuehrt den
Build aber weiter als Schritt 5 und CON-0016 den Config-Schluessel.
"""
from __future__ import annotations

from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

import pytest


def _cfg(tmp_path, *, build: str = "", compose: str = ""):
    from sdd_cli.config import SddConfig

    return SddConfig(root=tmp_path, raw={
        "orchestrator": {"build_command": build},
        "docker": {"compose_file": compose},
        "test_runner": {"command": "pytest"},
    })


class _Welt:
    """Nimmt alle subprocess.run-Aufrufe der Finalisierung auf."""

    def __init__(self, build_rc: int = 0):
        self.aufrufe: list[tuple] = []
        self.build_rc = build_rc

    def run(self, befehl, *args, **kwargs):
        self.aufrufe.append((befehl, kwargs))
        text = befehl if isinstance(befehl, str) else " ".join(befehl)
        if "pytest" in text:
            return CompletedProcess(befehl, 0, stdout="1 passed", stderr="")
        return CompletedProcess(befehl, self.build_rc, stdout="baue…", stderr="" if self.build_rc == 0 else "make: *** Fehler 2")

    def texte(self) -> list[str]:
        return [b if isinstance(b, str) else " ".join(b) for b, _ in self.aufrufe]


@pytest.fixture
def welt():
    return _Welt()


def _finalisieren(cfg, welt, **kwargs):
    from sdd_cli import finalize

    runtime = MagicMock()
    runtime.inspect_status.return_value = "running"
    runtime.cli.return_value = "podman"
    mgr = MagicMock()
    with patch.object(finalize, "get_runtime", return_value=runtime), \
         patch.object(finalize, "DevContainerManager", return_value=mgr), \
         patch.object(finalize, "_git", return_value=CompletedProcess([], 0, stdout="abc123", stderr="")), \
         patch.object(finalize, "save_test_result"), \
         patch.object(finalize.SpecFinalizer, "_run_compliance_check", return_value=None), \
         patch.object(finalize.SpecFinalizer, "_create_pr", return_value=("https://pr/1", None, None)), \
         patch.object(finalize.subprocess, "run", side_effect=welt.run):
        dry = kwargs.pop("dry_run", False)
        report = finalize.SpecFinalizer(cfg, dry_run=dry).run("SPEC-0007", no_commit=True, **kwargs)
    return report, mgr


def test_build_laeuft_im_container_vor_den_tests(tmp_path, welt):
    report, _ = _finalisieren(_cfg(tmp_path, build="make build"), welt)
    texte = welt.texte()
    assert "cd /workspace && make build" in texte[0], texte
    assert "pytest" in texte[1], texte
    assert report.build_passed is True
    assert report.tests_passed is True


def test_gescheiterter_build_ueberspringt_die_tests(tmp_path):
    welt = _Welt(build_rc=2)
    report, mgr = _finalisieren(_cfg(tmp_path, build="make build"), welt)
    assert len(welt.aufrufe) == 1, welt.texte()
    assert report.build_passed is False
    assert report.tests_passed is False
    assert "Build fehlgeschlagen" in report.error
    assert "Fehler 2" in report.build_output
    mgr.close.assert_not_called()  # Container bleibt zum Hineinschauen stehen


def test_argument_sticht_config(tmp_path, welt):
    _finalisieren(_cfg(tmp_path, build="aus-config"), welt, build_cmd="aus-argument")
    assert "aus-argument" in welt.texte()[0]
    assert not any("aus-config" in t for t in welt.texte())


def test_ohne_build_kommando_kein_build_aufruf(tmp_path, welt):
    report, _ = _finalisieren(_cfg(tmp_path), welt)
    assert len(welt.aufrufe) == 1 and "pytest" in welt.texte()[0]
    assert report.build_passed is None


def test_compose_pfad_baut_auf_dem_host(tmp_path, welt):
    _finalisieren(_cfg(tmp_path, build="make", compose="compose.yml"), welt)
    befehl, kwargs = welt.aufrufe[0]
    assert befehl == "make" and kwargs.get("shell") is True
    assert kwargs.get("cwd") == tmp_path


def test_dry_run_baut_nicht(tmp_path, welt):
    report, _ = _finalisieren(_cfg(tmp_path, build="make"), welt, dry_run=True)
    assert welt.aufrufe == []
    assert report.build_passed is None


def test_zeitlimit_ist_ein_fehlschlag(tmp_path):
    from subprocess import TimeoutExpired

    welt = _Welt()

    def zu_langsam(befehl, *a, **kw):
        raise TimeoutExpired(befehl, 1)

    welt.run = zu_langsam
    report, _ = _finalisieren(_cfg(tmp_path, build="make"), welt)
    assert report.build_passed is False
    assert "Zeitlimit" in report.build_output
