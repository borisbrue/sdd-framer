"""Die Finalisierung ruft das konfigurierte Testkommando richtig auf (#117).

Container- und Compose-Weg berechneten den Aufruf verschieden. Der Container
haengte fest `tests/ -x --tb=short` an jedes Kommando — ein npm-Projekt lief als
`npm tests/ -x --tb=short` und scheiterte immer. Der Compose-Weg gab ein
mehrwortiges Kommando wie `uv run pytest` als einen Programmnamen weiter.
"""
from __future__ import annotations

import shlex
from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

import pytest

# (Konfiguration, package.json vorhanden?, erwarteter Aufruf)
FAELLE = {
    "ohne-kommando":        ({}, False, ["pytest", "tests/", "-x", "--tb=short"]),
    "ohne-kommando-npm":    ({}, True, ["npm", "test"]),
    "blueprint-pytest":     ({"command": "pytest"}, False, ["pytest", "tests/", "-x", "--tb=short"]),
    "uv-run-pytest":        ({"command": "uv run pytest"}, False,
                             ["uv", "run", "pytest", "tests/", "-x", "--tb=short"]),
    "python-m-pytest":      ({"command": "python -m pytest"}, False,
                             ["python", "-m", "pytest", "tests/", "-x", "--tb=short"]),
    "npm-ausdruecklich":    ({"command": "npm"}, False, ["npm", "test"]),
    "make-check":           ({"command": "make check"}, False, ["make", "check"]),
    "mit-extra-args":       ({"command": "make check", "extra_args": ["-j4"]}, False,
                             ["make", "check", "-j4"]),
    "pytest-mit-extra":     ({"command": "pytest", "extra_args": ["-q"]}, False,
                             ["pytest", "tests/", "-x", "--tb=short", "-q"]),
}


@pytest.mark.parametrize("fall", sorted(FAELLE))
def test_berechneter_aufruf(tmp_path, fall):
    from sdd_cli.finalize import testaufruf

    cfg, package_json, erwartet = FAELLE[fall]
    if package_json:
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    assert testaufruf(cfg, tmp_path) == erwartet


def _finalisieren(tmp_path, test_runner: dict, *, compose: str = ""):
    from sdd_cli import finalize
    from sdd_cli.config import SddConfig

    cfg = SddConfig(root=tmp_path, raw={
        "orchestrator": {"build_command": ""},
        "docker": {"compose_file": compose},
        "test_runner": test_runner,
    })
    aufrufe: list[tuple] = []

    def run(befehl, *a, **kw):
        aufrufe.append((befehl, kw))
        return CompletedProcess(befehl, 0, stdout="1 passed", stderr="")

    runtime = MagicMock()
    runtime.inspect_status.return_value = "running"
    runtime.cli.return_value = "podman"
    with patch.object(finalize, "get_runtime", return_value=runtime), \
         patch.object(finalize, "DevContainerManager", return_value=MagicMock()), \
         patch.object(finalize, "_git", return_value=CompletedProcess([], 0, stdout="abc", stderr="")), \
         patch.object(finalize, "save_test_result"), \
         patch.object(finalize.SpecFinalizer, "_run_compliance_check", return_value=None), \
         patch.object(finalize.SpecFinalizer, "_create_pr", return_value=("https://pr/1", None, None)), \
         patch.object(finalize.subprocess, "run", side_effect=run):
        finalize.SpecFinalizer(cfg).run("SPEC-0007", no_commit=True)
    return aufrufe


class TestContainerWeg:
    def test_npm_projekt_laeuft_als_npm_test(self, tmp_path):
        """Der Befund aus #117."""
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")
        [(befehl, _)] = _finalisieren(tmp_path, {})
        assert befehl[:5] == ["podman", "exec", "sdd-dev-spec-0007", "bash", "-c"]
        assert befehl[5] == "cd /workspace && npm test"

    def test_eigenes_kommando_bekommt_keine_pytest_argumente(self, tmp_path):
        [(befehl, _)] = _finalisieren(tmp_path, {"command": "make check"})
        assert befehl[5] == "cd /workspace && make check"

    def test_blueprint_pytest_bleibt_wie_bisher(self, tmp_path):
        """Die haeufigste Konfiguration darf sich im Container nicht aendern."""
        [(befehl, _)] = _finalisieren(tmp_path, {"command": "pytest"})
        assert befehl[5] == "cd /workspace && pytest tests/ -x --tb=short"

    def test_argumente_werden_fuer_die_shell_gequotet(self, tmp_path):
        [(befehl, _)] = _finalisieren(tmp_path, {"command": "make check",
                                                  "extra_args": ["NAME=mit leerzeichen"]})
        assert shlex.split(befehl[5].removeprefix("cd /workspace && ")) == [
            "make", "check", "NAME=mit leerzeichen"]


class TestComposeWeg:
    def test_mehrwortiges_kommando_wird_zerlegt(self, tmp_path):
        """Vorher: `uv run pytest` als ein Programmname -> FileNotFoundError."""
        [(befehl, kw)] = _finalisieren(tmp_path, {"command": "uv run pytest"}, compose="c.yml")
        assert befehl == ["uv", "run", "pytest", "tests/", "-x", "--tb=short"]
        assert not kw.get("shell")

    def test_beide_wege_rufen_dasselbe(self, tmp_path):
        """Die Ursache selbst: zwei Wege, zwei Rechnungen."""
        [(container, _)] = _finalisieren(tmp_path, {"command": "make check", "extra_args": ["-j4"]})
        [(compose, _)] = _finalisieren(tmp_path, {"command": "make check", "extra_args": ["-j4"]},
                                       compose="c.yml")
        assert shlex.split(container[5].removeprefix("cd /workspace && ")) == compose
