"""SPEC-0054 FR-11, CON-0192 INV-01/INV-07/INV-09: ProbeRun mit einheitlicher Fehlersemantik."""
from __future__ import annotations

import pytest

from sdd_cli.quality.config import Probe
from sdd_cli.quality.files import collect_files, glob_match
from sdd_cli.quality.probe import ProbeRun

SARIF = '{"version": "2.1.0", "runs": [{"results": []}]}'


@pytest.fixture()
def projekt(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src/a.py").write_text("a\nb\n")
    (tmp_path / "src/b.txt").write_text("x\n")
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd/x.md").write_text("y\n")
    (tmp_path / "vendor").mkdir()
    (tmp_path / "vendor/v.py").write_text("v\n")
    (tmp_path / "ok.sarif").write_text(SARIF)
    return tmp_path


def _probe(command, fmt="sarif", **kw):
    return Probe(name="p", command=command, format=fmt, **kw)


def test_erfolgreiche_sonde(projekt):
    o = ProbeRun(projekt, ["src/a.py"]).execute(_probe("cp ok.sarif {out}",
                                                       version_command="echo t 1.2\necho x"))
    assert o.status == "ok" and o.reason is None
    assert o.exit_code == 0 and o.result.findings == []
    assert o.tool_version == "t 1.2"
    assert o.command == "cp ok.sarif {out}"
    assert o.duration_ms >= 0


def test_paths_werden_quotiert_eingesetzt(projekt):
    ProbeRun(projekt, ["src/a.py", "src/mit leer.py"]).execute(
        _probe("printf '%s\\n' {paths} > seen.txt; cp ok.sarif {out}"))
    assert (projekt / "seen.txt").read_text().splitlines() == ["src/a.py", "src/mit leer.py"]


@pytest.mark.parametrize(("command", "grund"), [
    ("gibt-es-nicht-4711 > {out}", "Befehl nicht gefunden"),
    ("sleep 5; cp ok.sarif {out}", "Zeitlimit überschritten"),
    ("true", "keine Ausgabe"),
    ("true > {out}", "keine Ausgabe"),
    ("echo kaputt > {out}", "Ausgabe nicht parsebar"),
    ("cat .sdd/holdout/x > {out}", "Holdout-Pfad verboten"),
])
def test_ausfallgruende(projekt, command, grund):
    o = ProbeRun(projekt, []).execute(_probe(command, timeout_seconds=1))
    assert o.status == "n/a" and o.reason == grund and o.result is None


def test_exit_ungleich_null_mit_gueltiger_ausgabe_ist_ok(projekt):
    o = ProbeRun(projekt, []).execute(_probe("cp ok.sarif {out}; exit 3"))
    assert o.status == "ok" and o.exit_code == 3


def test_optionen_gehen_an_den_parser(projekt):
    (projekt / "j.xml").write_text(
        '<testsuite><testcase classname="c" name="t_FR-02"/></testsuite>')
    o = ProbeRun(projekt, []).execute(_probe("cp j.xml {out}", "junit", role="tests",
                                             fr_marker="name"))
    assert o.result.cases[0].frs == ("FR-02",)


def test_collect_files_default_ohne_sdd_und_git(projekt):
    assert collect_files(projekt, [], []) == ["ok.sarif", "src/a.py", "src/b.txt",
                                              "vendor/v.py"]


def test_collect_files_mit_paths_und_exclude(projekt):
    assert collect_files(projekt, ["**/*.py"], ["vendor/**"]) == ["src/a.py"]


@pytest.mark.parametrize(("pfad", "muster", "treffer"), [
    ("src/a.py", "src/**", True), ("src/x/y/a.py", "src/**", True), ("src", "src/**", False),
    ("a.py", "**/*.py", True), ("src/a.py", "**/*.py", True), ("src/a.py", "*.py", False),
    ("tool/sdd_cli/web/x.py", "tool/sdd_cli/*.py", False), ("tool/sdd_cli/m.py",
                                                            "tool/sdd_cli/*.py", True),
])
def test_glob_match(pfad, muster, treffer):
    assert glob_match(pfad, muster) is treffer
