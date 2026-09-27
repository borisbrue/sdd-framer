"""TST-0226 – CON-0197: CLI sdd quality, sdd arch, Erweiterung von sdd test run, ADR-Prüfung.

Spec: SPEC-0054 · Contract: CON-0197
Jedes Szenario aus dem Contract-Artefakt ist ein Test. Solange `sdd quality`/`sdd arch` fehlen,
werden sie übersprungen.
"""
from __future__ import annotations

import json
import subprocess

import click
import pytest
import yaml

from tests.support.quality_project import (
    QualityProject,
    deps,
    fr_status,
    junit,
    make_project,
    requires_quality_cli,
    sarif,
    schema_errors,
    standard_projekt,
)

pytestmark = requires_quality_cli


@pytest.fixture()
def qproject(tmp_path, monkeypatch) -> QualityProject:
    return make_project(tmp_path, monkeypatch)


def _git(p: QualityProject, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=p.root, check=True, capture_output=True,
                          text=True).stdout.strip()


def _git_init(p: QualityProject) -> None:
    _git(p, "init", "-q", "-b", "main")
    _git(p, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    _git(p, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "base")


def _sonden(p: QualityProject) -> dict:
    return yaml.safe_load((p.root / ".sdd/quality.yaml").read_text())


def _sonden_setzen(p: QualityProject, daten: dict) -> None:
    (p.root / ".sdd/quality.yaml").write_text(yaml.safe_dump(daten, sort_keys=False))


def _arch_projekt(p: QualityProject, edges: list[dict]) -> None:
    p.quality_yaml({"imports": p.fixture_probe("imports", deps(edges), "sdd-deps", role="deps")})
    p.architecture({"web": ["web/**"], "core": ["core/**"]},
                   [{"id": "ARCH-01", "adr": "ADR-0007", "kind": "forbidden_dependency",
                     "from": "web", "to_paths": ["core/writer.py"]}])
    p.adr("ADR-0007", "Web delegiert Schreiben an den Kern", enforced_by=("ARCH-01",))


VERSTOSS = {"from": "web/routes.py", "to": "core/writer.py", "symbol": "writer", "line": 4}


# ── sdd quality measure ───────────────────────────────────────────────────────

def test_tc01_measure_schreibt_einen_schema_gueltigen_report(qproject: QualityProject):
    """Scenario: measure schreibt einen schema-gültigen Report (CON-0197)."""
    standard_projekt(qproject)
    ergebnis, report = qproject.measure("--spec", "SPEC-0900")
    assert ergebnis.exit_code == 0
    assert schema_errors("report", report) == []


def test_tc02_measure_mit_out(qproject: QualityProject):
    """Scenario: measure mit --out (CON-0197)."""
    standard_projekt(qproject)
    ergebnis = qproject.run("quality", "measure", "--out", "build/q.json")
    assert ergebnis.exit_code == 0, ergebnis.output
    report = json.loads((qproject.root / "build/q.json").read_text())
    assert schema_errors("report", report) == []
    assert list((qproject.root / ".sdd/quality/runs").glob("*.json"))


def test_tc03_measure_mit_fehlgeschlagenem_gate(qproject: QualityProject):
    """Scenario: measure mit fehlgeschlagenem Gate (CON-0197)."""
    standard_projekt(qproject, frs=["FR-01", "FR-02"],
                     tests=[("a", "passed", ["FR-01"]), ("b", "passed", ["FR-02"]),
                            ("c", "failed", ["FR-02"])])
    qproject.config_quality({"gates": ["requirements >= 1.0"]})
    ergebnis = qproject.run("quality", "measure", "--spec", "SPEC-0900")
    assert ergebnis.exit_code == 1
    assert "requirements >= 1.0" in ergebnis.output and "FR-02" in ergebnis.output


def test_tc04_measure_ohne_quality_yaml(qproject: QualityProject):
    """Scenario: measure ohne quality.yaml (CON-0197)."""
    ergebnis = qproject.run("quality", "measure")
    assert ergebnis.exit_code == 2
    assert "sdd stack apply" in ergebnis.output


def test_tc05_measure_mit_ungueltiger_quality_yaml(qproject: QualityProject):
    """Scenario: measure mit ungültiger quality.yaml (CON-0197)."""
    qproject.quality_yaml({"lint": {"command": "ruff check", "format": "sarif"}})
    ergebnis = qproject.run("quality", "measure")
    assert ergebnis.exit_code == 2
    assert "probes.lint.command" in ergebnis.output


def test_tc06_diff_begrenzte_messung(qproject: QualityProject):
    """Scenario: Diff-begrenzte Messung (CON-0197)."""
    standard_projekt(qproject)
    qproject.source("src/a.py", 10)
    qproject.source("src/b.py", 10)
    befunde = qproject.write(".fixtures/lint.sarif", sarif([]))
    daten = _sonden(qproject)
    daten["probes"]["lint"] = {
        "command": f"echo {{paths}} > .fixtures/paths.txt; cp {befunde} {{out}}",
        "format": "sarif", "metric": "lint_per_kloc", "diff_scoped": True}
    _sonden_setzen(qproject, daten)
    _git_init(qproject)
    qproject.source("src/a.py", 11)
    _, report = qproject.measure("--diff", "main")
    assert (qproject.root / ".fixtures/paths.txt").read_text().split() == ["src/a.py"]
    assert report["base_ref"] == "main"


# ── sdd test run ──────────────────────────────────────────────────────────────

def _letzter_run(p: QualityProject) -> tuple[dict, object]:
    runs = sorted((p.root / ".sdd/test-runs").glob("SPEC-0900-*.json"))
    assert runs, "kein Run-Report"
    return json.loads(runs[-1].read_text()), runs[-1]


def test_tc07_test_run_nutzt_die_testsonde_und_speichert_testfae(qproject: QualityProject):
    """Scenario: test run nutzt die Testsonde und speichert Testfälle (CON-0197)."""
    standard_projekt(qproject, frs=["FR-01"], tests=[("t_eins", "passed", ["FR-01"]),
                                                     ("t_zwei", "failed", [])])
    qproject.run("test", "run", "SPEC-0900")
    run, pfad = _letzter_run(qproject)
    assert (qproject.root / run["junit"]).is_file()
    assert run["junit"].endswith(".junit.xml")
    faelle = {t["name"]: t for t in run["testcases"]}
    assert faelle["t_eins"]["status"] == "passed" and faelle["t_eins"]["frs"] == ["FR-01"]
    assert faelle["t_zwei"]["status"] == "failed"


@pytest.mark.parametrize(
    ("tests", "sonde_kaputt", "exit_code"),
    [([("a", "passed", ["FR-01"])], False, 0),
     ([("a", "passed", ["FR-01"]), ("b", "failed", ["FR-01"])], False, 1),
     ([("a", "passed", ["FR-01"])], True, 2)],
)
def test_test_run_mit_sonde_exit_codes_und_runner(qproject: QualityProject, tests,
                                                    sonde_kaputt, exit_code):
    """INV-05b: Exit-Codes von test run mit Testsonde, runner = probe:<name>."""
    standard_projekt(qproject, frs=["FR-01"], tests=tests)
    if sonde_kaputt:
        daten = _sonden(qproject)
        daten["probes"]["tests"]["command"] = "gibt-es-nicht-4711 > {out}"
        _sonden_setzen(qproject, daten)
    ergebnis = qproject.run("test", "run", "SPEC-0900")
    assert ergebnis.exit_code == exit_code, ergebnis.output
    if not sonde_kaputt:
        run, _ = _letzter_run(qproject)
        assert run["runner"] == "probe:tests"
        assert run["git_sha"] is None or isinstance(run["git_sha"], str)


def test_tc08_test_run_ohne_quality_yaml_bleibt_unveraendert(qproject: QualityProject):
    """Scenario: test run ohne quality.yaml bleibt unverändert (CON-0197)."""
    qproject.spec(["FR-01"])
    qproject.run("test", "run", "SPEC-0900")
    runs = sorted((qproject.root / ".sdd/test-runs").glob("SPEC-0900-*.json"))
    for run in runs:
        daten = json.loads(run.read_text())
        assert "testcases" not in daten and "junit" not in daten


def test_tc09_measure_nutzt_vorhandenen_test_run(qproject: QualityProject):
    """Scenario: measure nutzt vorhandenen Test-Run (CON-0197)."""
    standard_projekt(qproject, frs=["FR-01"])
    _git_init(qproject)
    qproject.run("test", "run", "SPEC-0900")
    _, pfad = _letzter_run(qproject)
    daten = _sonden(qproject)
    daten["probes"]["tests"]["command"] = "gibt-es-nicht-4711 > {out}"
    _sonden_setzen(qproject, daten)
    _, report = qproject.measure("--spec", "SPEC-0900", "--reuse-test-run")
    assert fr_status(report) == {"FR-01": "erfüllt"}
    assert report["requirements"]["test_run"].endswith(pfad.name)


# ── sdd quality doctor / init ─────────────────────────────────────────────────

def test_tc10_doctor_meldet_probleme_je_sonde(qproject: QualityProject):
    """Scenario: doctor meldet Probleme je Sonde (CON-0197)."""
    qproject.spec(["FR-01"])
    qproject.quality_yaml({
        "types": {"command": "gibt-es-nicht-4711 > {out}", "format": "sarif",
                  "metric": "type_errors"},
        "complexity": qproject.fixture_probe(
            "complexity", json.dumps({"format": "sdd-metrics", "version": 1,
                                      "metrics": [{"name": "complexity_max", "value": 3}]}),
            "sdd-metrics"),
    })
    ergebnis = qproject.run("quality", "doctor")
    assert ergebnis.exit_code == 1
    zeilen = ergebnis.output.splitlines()
    assert any("types" in z and "Befehl nicht gefunden" in z for z in zeilen)
    assert any("complexity" in z and "Normierung fehlt" in z for z in zeilen)


def test_tc11_init_verweist_auf_die_stack_vorlage(qproject: QualityProject):
    """Scenario: init verweist auf die Stack-Vorlage (CON-0197, SPEC-0057 FR-09)."""
    ergebnis = qproject.run("quality", "init", "--preset", "python")
    assert ergebnis.exit_code == 1
    assert "sdd stack apply python-cli --only quality" in ergebnis.output
    assert not (qproject.root / ".sdd/quality.yaml").exists()


def test_tc12_init_schreibt_nichts(qproject: QualityProject):
    """Scenario: init schreibt nichts (CON-0197, SPEC-0057 FR-09)."""
    eigen = "version: 1\nprobes:\n  x: {command: 'true > {out}', format: sarif}\n"
    qproject.write(".sdd/quality.yaml", eigen)
    ergebnis = qproject.run("quality", "init", "--preset", "python")
    assert ergebnis.exit_code == 1
    assert (qproject.root / ".sdd/quality.yaml").read_text() == eigen
    assert not list((qproject.root / ".sdd").rglob("*.new"))


# ── sdd arch ──────────────────────────────────────────────────────────────────

def test_tc13_arch_check_meldet_verstoss_mit_adr(qproject: QualityProject):
    """Scenario: arch check meldet Verstoß mit ADR (CON-0197)."""
    _arch_projekt(qproject, [VERSTOSS])
    ergebnis = qproject.run("arch", "check")
    assert ergebnis.exit_code == 1
    for teil in ("ARCH-01", "ADR-0007", "Web delegiert Schreiben an den Kern", "web/routes.py:4"):
        assert teil in ergebnis.output


def _baseline(p: QualityProject, eintraege: list[dict]) -> None:
    p.write(".sdd/quality/arch-baseline.json", json.dumps({"version": 1, "entries": eintraege}))


def test_tc14_arch_check_mit_baseline(qproject: QualityProject):
    """Scenario: arch check mit Baseline (CON-0197)."""
    _arch_projekt(qproject, [VERSTOSS])
    _baseline(qproject, [{"rule": "ARCH-01", "file": "web/routes.py", "symbol": "writer",
                          "reason": "alt"}])
    ergebnis = qproject.run("arch", "check")
    assert ergebnis.exit_code == 0
    assert "warn (Baseline)" in ergebnis.output


def test_tc15_veralteter_baseline_eintrag(qproject: QualityProject):
    """Scenario: Veralteter Baseline-Eintrag (CON-0197)."""
    _arch_projekt(qproject, [])
    _baseline(qproject, [{"rule": "ARCH-01", "file": "web/routes.py", "symbol": "writer",
                          "reason": "alt"}])
    ergebnis = qproject.run("arch", "check")
    assert ergebnis.exit_code == 0
    assert "Baseline kann bereinigt werden" in ergebnis.output


def test_tc16_baseline_schreiben(qproject: QualityProject):
    """Scenario: Baseline schreiben (CON-0197)."""
    _arch_projekt(qproject, [VERSTOSS])
    ergebnis = qproject.run("arch", "check", "--write-baseline")
    assert ergebnis.exit_code == 0
    daten = json.loads((qproject.root / ".sdd/quality/arch-baseline.json").read_text())
    assert daten["entries"] == [{"rule": "ARCH-01", "file": "web/routes.py", "symbol": "writer",
                                 "reason": "TODO"}]


def test_tc17_baseline_fortschreiben_erhaelt_vorhandene_eintraeg(qproject: QualityProject):
    """Scenario: Baseline fortschreiben erhält vorhandene Einträge (CON-0197)."""
    zweiter = {**VERSTOSS, "from": "web/other.py", "file": "web/other.py"}
    _arch_projekt(qproject, [VERSTOSS, zweiter])
    _baseline(qproject, [{"rule": "ARCH-01", "file": "web/routes.py", "symbol": "writer",
                          "reason": "Altlast, SPEC-0053"}])
    ergebnis = qproject.run("arch", "check", "--write-baseline")
    assert ergebnis.exit_code == 0
    daten = json.loads((qproject.root / ".sdd/quality/arch-baseline.json").read_text())
    gruende = {e["file"]: e["reason"] for e in daten["entries"]}
    assert gruende == {"web/routes.py": "Altlast, SPEC-0053", "web/other.py": "TODO"}
    assert "web/other.py" in ergebnis.stderr


def test_tc18_out_ueberschreibt_ein_vorhandenes_ziel(qproject: QualityProject):
    """Scenario: --out überschreibt ein vorhandenes Ziel (CON-0197)."""
    standard_projekt(qproject)
    qproject.write("build/q.json", "{}")
    assert qproject.run("quality", "measure", "--out", "build/q.json").exit_code == 0
    assert json.loads((qproject.root / "build/q.json").read_text())["schema_version"] == 1
    assert not (qproject.root / "build/q.json.new").exists()


def test_tc19_arch_check_ohne_architecture_yaml(qproject: QualityProject):
    """Scenario: arch check ohne architecture.yaml (CON-0197)."""
    ergebnis = qproject.run("arch", "check")
    assert ergebnis.exit_code == 2
    assert "sdd arch init" in ergebnis.output


def test_tc20_arch_init_schlaegt_schichten_vor(qproject: QualityProject):
    """Scenario: arch init schlägt Schichten vor (CON-0197)."""
    qproject.source("alpha/a.py", 1)
    qproject.source("beta/b.py", 1)
    assert qproject.run("arch", "init").exit_code == 0
    daten = yaml.safe_load((qproject.root / ".sdd/architecture.yaml").read_text())
    assert schema_errors("architecture", daten) == []
    assert {"alpha", "beta"} <= set(daten["layers"])
    assert daten["rules"] == []


# ── sdd validate ──────────────────────────────────────────────────────────────

def _validate_projekt(p: QualityProject, rules: list[dict]) -> None:
    p.architecture({"web": ["web/**"], "core": ["core/**"]}, rules)


def test_tc21_validate_prueft_die_adr_verknuepfung(qproject: QualityProject):
    """Scenario: validate prüft die ADR-Verknüpfung (CON-0197)."""
    qproject.adr("ADR-0007", "Entscheidung", enforced_by=("ARCH-09",))
    _validate_projekt(qproject, [{"id": "ARCH-05", "adr": "ADR-0099",
                                  "kind": "forbidden_dependency", "from": "web",
                                  "to_layers": ["core"]}])
    ergebnis = qproject.run("validate")
    assert ergebnis.exit_code == 1
    zeilen = ergebnis.output.splitlines()
    assert any("ARCH-05" in z and "ADR-0099" in z for z in zeilen)
    assert any("ADR-0007" in z and "ARCH-09" in z for z in zeilen)


def test_tc22_validate_warnt_bei_regel_an_abgeloestem_adr(qproject: QualityProject):
    """Scenario: validate warnt bei Regel an abgelöstem ADR (CON-0197)."""
    qproject.adr("ADR-0008", "Alt", status="superseded")
    _validate_projekt(qproject, [{"id": "ARCH-02", "adr": "ADR-0008",
                                  "kind": "forbidden_dependency", "from": "web",
                                  "to_layers": ["core"]}])
    ergebnis = qproject.run("validate")
    assert any("ARCH-02" in z and "ADR-0008" in z for z in ergebnis.output.splitlines())


def test_tc23_validate_meldet_doppelte_regel_ids(qproject: QualityProject):
    """Scenario: validate meldet doppelte Regel-IDs (CON-0197)."""
    qproject.adr("ADR-0101", "E")
    regel = {"id": "ARCH-03", "adr": "ADR-0101", "kind": "forbidden_dependency", "from": "web",
             "to_layers": ["core"]}
    _validate_projekt(qproject, [regel, dict(regel)])
    ergebnis = qproject.run("validate")
    assert ergebnis.exit_code == 1
    assert "doppelte Regel-ID ARCH-03" in ergebnis.output


def test_tc24_zwei_sonden_mit_derselben_rolle(qproject: QualityProject):
    """Scenario: Zwei Sonden mit derselben Rolle (CON-0197)."""
    qproject.spec(["FR-01"])
    qproject.quality_yaml({
        "eins": qproject.fixture_probe("eins", junit([]), "junit", role="tests",
                                       fr_marker="name"),
        "zwei": qproject.fixture_probe("zwei", junit([]), "junit", role="tests",
                                       fr_marker="name")})
    ergebnis = qproject.run("quality", "measure")
    assert ergebnis.exit_code == 2
    assert "eins" in ergebnis.output and "zwei" in ergebnis.output


SPRACHEN_UND_WERKZEUGE = {"python", "pytest", "ruff", "mypy", "pyright", "lizard", "rust",
                          "cargo", "clippy", "node", "npm", "eslint", "jest", "go", "java"}


def _befehlsnamen(gruppe: click.Group, praefix: str = "") -> list[str]:
    namen = []
    for name, befehl in gruppe.commands.items():
        namen.append(praefix + name)
        if isinstance(befehl, click.Group):
            namen += _befehlsnamen(befehl, praefix + name + " ")
    return namen


def test_tc25_keine_sprachspezifischen_befehle():
    """Scenario: Keine sprachspezifischen Befehle (CON-0197)."""
    from sdd_cli.main import cli

    for name in _befehlsnamen(cli):
        teile = set(name.replace("-", " ").split())
        assert not teile & SPRACHEN_UND_WERKZEUGE, name
