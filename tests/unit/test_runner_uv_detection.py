"""Das Pre-Commit-Gate lief in uv-Projekten nie.

Der Default `test_runner.command: pytest` liess _resolve_runner zwei Kandidaten
probieren: `sys.executable -m pytest` (der Interpreter, der sdd ausfuehrt — hat
pytest in der Regel nicht) und `pytest` im PATH (ohne aktiviertes venv nicht da,
der Normalfall bei uv-Projekten). Beide scheiterten:

    [sdd pre-commit] SPEC-0001 uebersprungen: Kein lauffaehiger Test-Runner
    gefunden (konfiguriert: 'pytest').

…und der Commit ging durch. Die Regressionspruefung fiel aus, ohne dass jemand
etwas dagegen tun musste.

Die Antwort ist nicht, wieder zu blockieren (siehe #37), sondern den Default
aufzuloesen statt zu behaupten — wie bei der Container-Runtime in #59.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

from sdd_cli import test_runner


@pytest.fixture(autouse=True)
def _cache_leeren():
    test_runner._RUNNER_CACHE.clear()
    yield
    test_runner._RUNNER_CACHE.clear()


def _uv_projekt(tmp_path: Path) -> Path:
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    return tmp_path


def _probe(erfolgreich: list[str]):
    """Patcht die --version-Probe: nur `erfolgreich` liefert returncode 0."""
    def fake_run(cmd, **kw):
        class R:
            returncode = 0 if list(cmd[:len(erfolgreich)]) == erfolgreich else 1
        return R()
    return patch.object(test_runner.subprocess, "run", fake_run)


class TestUvProjektErkennung:
    def test_uv_lock_ist_das_signal(self, tmp_path):
        assert test_runner._ist_uv_projekt(_uv_projekt(tmp_path)) is True

    def test_pyproject_allein_reicht_nicht(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        assert test_runner._ist_uv_projekt(tmp_path) is False

    def test_leeres_verzeichnis(self, tmp_path):
        assert test_runner._ist_uv_projekt(tmp_path) is False


class TestUvWirdZuerstProbiert:
    def test_uv_run_pytest_gewinnt_im_uv_projekt(self, tmp_path):
        """Der gemeldete Fall: hier lief bisher gar nichts."""
        root = _uv_projekt(tmp_path)
        with patch.object(test_runner.shutil, "which", lambda n: f"/usr/bin/{n}"), \
             _probe(["uv", "run", "pytest"]):
            assert test_runner._resolve_runner("pytest", root) == ["uv", "run", "pytest"]

    def test_ohne_uv_lock_kein_uv(self, tmp_path):
        with patch.object(test_runner.shutil, "which", lambda n: f"/usr/bin/{n}"), \
             _probe(["pytest"]):
            assert test_runner._resolve_runner("pytest", tmp_path) == ["pytest"]

    def test_ohne_uv_im_path_kein_uv(self, tmp_path):
        root = _uv_projekt(tmp_path)
        with patch.object(test_runner.shutil, "which",
                          lambda n: None if n == "uv" else f"/usr/bin/{n}"), \
             _probe(["pytest"]):
            assert test_runner._resolve_runner("pytest", root) == ["pytest"]

    def test_scheiternde_uv_probe_faellt_zurueck(self, tmp_path):
        """uv da, aber pytest nicht im Projekt deklariert."""
        root = _uv_projekt(tmp_path)
        with patch.object(test_runner.shutil, "which", lambda n: f"/usr/bin/{n}"), \
             _probe(["pytest"]):
            assert test_runner._resolve_runner("pytest", root) == ["pytest"]

    def test_ohne_no_sync(self, tmp_path):
        """Seit dem venv-Schutz (#74) schreibt uv nicht mehr in den Mount."""
        root = _uv_projekt(tmp_path)
        with patch.object(test_runner.shutil, "which", lambda n: f"/usr/bin/{n}"), \
             _probe(["uv", "run", "pytest"]):
            assert "--no-sync" not in test_runner._resolve_runner("pytest", root)


class TestKonfiguriertesKommandoSticht:
    def test_expliziter_wert_gewinnt(self, tmp_path):
        root = _uv_projekt(tmp_path)
        with patch.object(test_runner.shutil, "which", lambda n: f"/usr/bin/{n}"), \
             _probe(["poetry", "run", "pytest"]):
            assert test_runner._resolve_runner("poetry run pytest", root) == [
                "poetry", "run", "pytest"]


class TestCacheProProjekt:
    def test_zwei_projekte_teilen_das_ergebnis_nicht(self, tmp_path):
        (tmp_path / "a").mkdir()
        _uv_projekt(tmp_path / "a")
        plain = tmp_path / "b"
        plain.mkdir()

        with patch.object(test_runner.shutil, "which", lambda n: f"/usr/bin/{n}"), \
             _probe(["uv", "run", "pytest"]):
            erst = test_runner._resolve_runner("pytest", tmp_path / "a")
        with patch.object(test_runner.shutil, "which", lambda n: f"/usr/bin/{n}"), \
             _probe(["pytest"]):
            zweit = test_runner._resolve_runner("pytest", plain)

        assert erst == ["uv", "run", "pytest"] and zweit == ["pytest"]

    def test_probe_laeuft_nur_einmal(self, tmp_path):
        root = _uv_projekt(tmp_path)
        aufrufe: list = []

        def fake_run(cmd, **kw):
            aufrufe.append(cmd)
            class R:
                returncode = 0
            return R()

        with patch.object(test_runner.shutil, "which", lambda n: f"/usr/bin/{n}"), \
             patch.object(test_runner.subprocess, "run", fake_run):
            test_runner._resolve_runner("pytest", root)
            test_runner._resolve_runner("pytest", root)
        assert len(aufrufe) == 1


class TestProbeLaeuftImProjekt:
    def test_cwd_ist_der_projektpfad(self, tmp_path):
        """`uv run` haengt vom Arbeitsverzeichnis ab."""
        root = _uv_projekt(tmp_path)
        erfasst: dict = {}

        def fake_run(cmd, **kw):
            erfasst.update(kw)
            class R:
                returncode = 0
            return R()

        with patch.object(test_runner.shutil, "which", lambda n: f"/usr/bin/{n}"), \
             patch.object(test_runner.subprocess, "run", fake_run):
            test_runner._resolve_runner("pytest", root)
        assert erfasst["cwd"] == str(root)
