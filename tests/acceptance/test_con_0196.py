"""TST-0225 – CON-0196: Score-Berechnung (Normierung, Gewichtung, n/a-Semantik, Gates).

Spec: SPEC-0054 · Contract: CON-0196
Jedes Szenario aus dem Contract-Artefakt ist ein Test. Die Tests steuern `sdd quality measure`
über vorbereitete Sondenausgaben (Shell-Sonden, sprachneutral) und lesen den JSON-Report.
Solange `sdd quality` fehlt, werden sie übersprungen.
"""
from __future__ import annotations

import json

import pytest
import yaml

from tests.support.quality_project import (
    QualityProject,
    deps,
    fr_status,
    junit,
    make_project,
    metrics,
    requires_quality_cli,
    sarif,
    score,
    standard_projekt,
)

pytestmark = requires_quality_cli


@pytest.fixture()
def qproject(tmp_path, monkeypatch) -> QualityProject:
    return make_project(tmp_path, monkeypatch)


def _sonden(p: QualityProject) -> dict:
    return yaml.safe_load((p.root / ".sdd/quality.yaml").read_text())


def _sonden_setzen(p: QualityProject, daten: dict) -> None:
    (p.root / ".sdd/quality.yaml").write_text(yaml.safe_dump(daten, sort_keys=False))


def _verstoesse(p: QualityProject, error: int, warn: int, baselined: int = 0) -> None:
    """Abhängigkeitssonde und Regeln so, dass genau diese Verstöße entstehen."""
    edges, rules = [], []
    for i in range(error + warn + baselined):
        rules.append({"id": f"ARCH-{i + 1:02d}", "adr": "ADR-0101", "kind": "forbidden_dependency",
                      "from": "src", "to_paths": [f"ziel{i}/**"],
                      "severity": "warn" if error <= i < error + warn else "error"})
        edges.append({"from": "src/app.py", "to": f"ziel{i}/x.py", "symbol": f"S{i}"})
    p.architecture({"src": ["src/**"]}, rules)
    daten = _sonden(p)
    daten["probes"]["imports"] = p.fixture_probe("imports", deps(edges), "sdd-deps", role="deps")
    _sonden_setzen(p, daten)
    if baselined:
        p.write(".sdd/quality/arch-baseline.json", json.dumps({"version": 1, "entries": [
            {"rule": f"ARCH-{i + 1:02d}", "file": "src/app.py", "symbol": f"S{i}", "reason": "alt"}
            for i in range(error + warn, error + warn + baselined)]}))


# ── Normierung ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("good", "bad", "roh", "norm"),
    [(0, 10, 5, 0.5), (0, 10, 12, 0.0), (0, 10, 0, 1.0), (0.9, 0.5, 0.7, 0.5),
     (0.9, 0.5, 0.95, 1.0)],
)
def test_tc01_lineare_normierung_einer_metrik(qproject: QualityProject, good, bad, roh, norm):
    """Scenario Outline: Lineare Normierung einer Metrik (CON-0196)."""
    standard_projekt(qproject, metrik={"m": roh}, normalization={"m": {"good": good, "bad": bad}})
    _, report = qproject.measure()
    assert score(report, "code_quality.m") == pytest.approx(norm)


# ── Gewichtung und Renormierung ───────────────────────────────────────────────

def test_tc02_gewichteter_gesamtscore(qproject: QualityProject):
    """Scenario: Gewichteter Gesamtscore (CON-0196)."""
    standard_projekt(qproject, metrik={"m": 2}, normalization={"m": {"good": 0, "bad": 10}})
    qproject.config_quality({"architecture": {"threshold": 5}})
    _verstoesse(qproject, error=2, warn=2)
    _, report = qproject.measure("--spec", "SPEC-0900")
    assert score(report, "requirements") == pytest.approx(1.0)
    assert score(report, "architecture") == pytest.approx(0.5)
    assert score(report, "code_quality") == pytest.approx(0.8)
    assert report["score"] == pytest.approx(0.825)
    assert report["incomplete"] is False


def test_tc03_renormierung_bei_ausgefallener_dimension(qproject: QualityProject):
    """Scenario: Renormierung bei ausgefallener Dimension (CON-0196)."""
    standard_projekt(qproject)
    qproject.config_quality({"architecture": {"threshold": 5}})
    _verstoesse(qproject, error=2, warn=2)
    daten = _sonden(qproject)
    daten["probes"]["metriken"]["command"] = "gibt-es-nicht-4711 > {out}"
    _sonden_setzen(qproject, daten)
    _, report = qproject.measure("--spec", "SPEC-0900")
    assert score(report, "code_quality") is None
    assert report["score"] == pytest.approx(0.8333, abs=1e-4)
    assert report["tree"]["renormalized"] is True
    assert report["incomplete"] is True


# ── Anforderungen ─────────────────────────────────────────────────────────────

def test_tc04_anforderungsscore_aus_fr_status(qproject: QualityProject):
    """Scenario: Anforderungsscore aus FR-Status (CON-0196)."""
    standard_projekt(qproject, frs=["FR-01", "FR-02", "FR-03", "FR-04"], tests=[
        ("a", "passed", ["FR-01"]), ("b", "passed", ["FR-02"]),
        ("c", "passed", ["FR-03"]), ("d", "failed", ["FR-03"]), ("e", "failed", ["FR-04"])])
    _, report = qproject.measure("--spec", "SPEC-0900")
    assert fr_status(report) == {"FR-01": "erfüllt", "FR-02": "erfüllt", "FR-03": "teilweise",
                                 "FR-04": "fehlt"}
    assert score(report, "requirements") == pytest.approx(0.5)


@pytest.mark.parametrize(("h", "erwartet"), [(None, 0.7), (0.25, 0.6)])
def test_tc05_holdout_ergebnisse_fliessen_gewichtet_ein(qproject: QualityProject, h, erwartet):
    """Scenario Outline: Holdout-Ergebnisse fließen gewichtet ein (CON-0196)."""
    standard_projekt(qproject, frs=["FR-01", "FR-02"],
                     tests=[("a", "passed", ["FR-01"]), ("b", "failed", ["FR-02"])])
    qproject.spec(["FR-01", "FR-02"], contracts=("CON-9001",))
    qproject.evaluation("2026-09-25T10-00-00", [("CON-9001", True)] * 9 + [("CON-9001", False)])
    if h is not None:
        qproject.config_quality({"weights": {"requirements": {"holdout": h}}})
    _, report = qproject.measure("--spec", "SPEC-0900")
    assert report["requirements"]["holdout_pass_rate"] == pytest.approx(0.9)
    assert score(report, "requirements") == pytest.approx(erwartet)


def test_holdout_ohne_skip_und_messfehler(qproject: QualityProject):
    """Formel holdout_pass_rate: skip und error zählen weder im Zähler noch im Nenner."""
    standard_projekt(qproject, frs=["FR-01"])
    qproject.spec(["FR-01"], contracts=("CON-9001",))
    qproject.evaluation("2026-09-25T10-00-00",
                        [("CON-9001", True), ("CON-9001", False), ("CON-9001", False),
                         ("CON-9001", False), ("CON-8888", False)],
                        verdicts=["", "", "skip", "error", ""])
    _, report = qproject.measure("--spec", "SPEC-0900")
    assert report["requirements"]["holdout_pass_rate"] == pytest.approx(0.5)


def test_holdout_nur_messfehler_ist_keine_gueltige_datei(qproject: QualityProject):
    """Eine Datei nur mit Messfehlern wird ignoriert; der Holdout-Anteil entfällt, statt 0 zu zählen."""
    standard_projekt(qproject, frs=["FR-01"])
    qproject.spec(["FR-01"], contracts=("CON-9001",))
    qproject.evaluation("2026-09-25T10-00-00", [("CON-9001", False)] * 3,
                        verdicts=["error"] * 3)
    _, report = qproject.measure("--spec", "SPEC-0900")
    assert report["requirements"]["holdout_pass_rate"] is None
    assert score(report, "requirements") == pytest.approx(1.0)


def test_tc06_ausgefallene_testsonde(qproject: QualityProject):
    """Scenario: Ausgefallene Testsonde (CON-0196)."""
    standard_projekt(qproject, frs=["FR-01", "FR-02"])
    daten = _sonden(qproject)
    daten["probes"]["tests"]["command"] = "gibt-es-nicht-4711 > {out}"
    _sonden_setzen(qproject, daten)
    _, report = qproject.measure("--spec", "SPEC-0900")
    assert set(fr_status(report).values()) == {"unbekannt"}
    assert score(report, "requirements") is None


@pytest.mark.parametrize(
    ("ergebnisse", "status"),
    [(["passed", "passed"], "erfüllt"), (["passed", "failed"], "teilweise"),
     (["failed", "error"], "fehlt"), ([], "fehlt"), (["skipped", "skipped"], "fehlt")],
)
def test_tc07_status_eines_fr_aus_seinen_testfaellen(qproject: QualityProject, ergebnisse,
                                                      status):
    """Scenario Outline: Status eines FR aus seinen Testfällen (CON-0196)."""
    faelle = [(f"t{i}", e, ["FR-07"]) for i, e in enumerate(ergebnisse)]
    standard_projekt(qproject, frs=["FR-07"], tests=faelle)
    _, report = qproject.measure("--spec", "SPEC-0900")
    assert fr_status(report)["FR-07"] == status


# ── Architektur ───────────────────────────────────────────────────────────────

def test_tc08_architekturscore_aus_gewichteten_verstoessen(qproject: QualityProject):
    """Scenario: Architekturscore aus gewichteten Verstößen (CON-0196)."""
    standard_projekt(qproject)
    qproject.config_quality({"architecture": {"threshold": 5}})
    _verstoesse(qproject, error=2, warn=2)
    _, report = qproject.measure()
    assert score(report, "architecture") == pytest.approx(0.5)


def test_tc09_baseline_verstoesse_zaehlen_als_warn(qproject: QualityProject):
    """Scenario: Baseline-Verstöße zählen als warn (CON-0196)."""
    standard_projekt(qproject)
    qproject.config_quality({"architecture": {"threshold": 5},
                             "gates": ["count.architecture.errors == 0"]})
    _verstoesse(qproject, error=0, warn=0, baselined=4)
    ergebnis, report = qproject.measure()
    assert score(report, "architecture") == pytest.approx(0.8)
    assert ergebnis.exit_code == 0
    assert all(g["passed"] for g in report["gates"])


def test_tc10_konfigurierbare_severity_gewichte(qproject: QualityProject):
    """Scenario: Konfigurierbare Severity-Gewichte (CON-0196)."""
    standard_projekt(qproject)
    qproject.config_quality({"architecture": {"threshold": 5,
                                              "severity_weights": {"error": 1.0, "warn": 0.5}}})
    _verstoesse(qproject, error=2, warn=2)
    _, report = qproject.measure()
    assert score(report, "architecture") == pytest.approx(0.4)


def test_tc11_architektur_ohne_abhaengigkeitssonde(qproject: QualityProject):
    """Scenario: Architektur ohne Abhängigkeitssonde (CON-0196)."""
    standard_projekt(qproject)
    daten = _sonden(qproject)
    del daten["probes"]["imports"]
    _sonden_setzen(qproject, daten)
    _, report = qproject.measure()
    knoten = report["tree"]["children"]
    architektur = {k["name"]: k for k in knoten}["architecture"]
    assert architektur["score"] is None and architektur["reason"]


def test_tc12_zu_viele_regeln_ohne_benoetigte_kantenart(qproject: QualityProject):
    """Scenario: Zu viele Regeln ohne benötigte Kantenart (CON-0196)."""
    standard_projekt(qproject)
    qproject.architecture({"src": ["src/**"]}, [
        {"id": "ARCH-01", "adr": "ADR-0101", "kind": "forbidden_dependency", "from": "src",
         "to_paths": ["x/**"]},
        {"id": "ARCH-02", "adr": "ADR-0101", "kind": "forbidden_call", "in": "src",
         "calls": ["subprocess.*"]},
        {"id": "ARCH-03", "adr": "ADR-0101", "kind": "write_ownership", "paths": ["y/**"],
         "owners": "src"}])
    _, report = qproject.measure()
    assert score(report, "architecture") is None
    assert len(report["architecture"]["rules_na"]) == 2
    assert all(r["reason"] for r in report["architecture"]["rules_na"])


# ── Sonden ────────────────────────────────────────────────────────────────────

def test_tc13_exit_code_ungleich_0_mit_gueltiger_ausgabe_ist_kei(qproject: QualityProject):
    """Scenario: Exit-Code ungleich 0 mit gültiger Ausgabe ist kein Ausfall (CON-0196)."""
    standard_projekt(qproject)
    qproject.source("src/app.py", 1000)
    datei = qproject.write(".fixtures/lint.sarif", sarif(
        [{"rule": f"E{i}", "file": "src/app.py", "line": i + 1} for i in range(3)]))
    daten = _sonden(qproject)
    daten["probes"]["lint"] = {"command": f"cp {datei} {{out}}; exit 1", "format": "sarif",
                               "metric": "lint_per_kloc"}
    _sonden_setzen(qproject, daten)
    _, report = qproject.measure()
    assert {s["name"]: s for s in report["probes"]}["lint"]["status"] == "ok"
    assert score(report, "code_quality.lint_per_kloc") == pytest.approx(0.7)


def test_tc14_ausgefallene_metrik_sonde_wird_renormiert(qproject: QualityProject):
    """Scenario: Ausgefallene Metrik-Sonde wird renormiert (CON-0196)."""
    standard_projekt(qproject, metrik={"a": 4}, normalization={"a": {"good": 0, "bad": 10},
                                                              "b": {"good": 0, "bad": 10}})
    daten = _sonden(qproject)
    daten["probes"]["zweite"] = {"command": "gibt-es-nicht-4711 > {out}",
                                 "format": "sdd-metrics"}
    _sonden_setzen(qproject, daten)
    _, report = qproject.measure()
    assert score(report, "code_quality") == pytest.approx(0.6)
    assert {k["name"]: k for k in report["tree"]["children"]}["code_quality"]["renormalized"]


def test_tc15_judge_ohne_gewicht_veraendert_den_score_nicht(qproject: QualityProject,
                                                              monkeypatch):
    """Scenario: Judge ohne Gewicht verändert den Score nicht (CON-0196)."""
    from sdd_cli.llm.base import CompletionResult

    class _Fake:
        def complete(self, prompt, **_kw):
            return CompletionResult(text='{"scores": {"lesbarkeit": 1, "idiomatik": 1, '
                                         '"passung": 1, "fehlerbehandlung": 1}}')

    # Seit SPEC-0055 (FR-12) läuft der Judge über die Rolle judge.
    monkeypatch.setattr("sdd_cli.pipeline.facade.judge_provider",
                        lambda *a, **k: (_Fake(), "fake-judge"))
    standard_projekt(qproject)
    _, ohne = qproject.measure()
    _, mit = qproject.measure("--judge")
    judge = {k["name"]: k for k in mit["tree"]["children"]}["judge"]
    assert judge["weight"] == 0 and judge["model"] and judge["rubric_version"]
    assert mit["score"] == pytest.approx(ohne["score"])


# ── Gates ─────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("gate", "tests", "bestanden"),
    [("requirements >= 1.0", [("a", "passed", ["FR-01"])], True),
     ("requirements >= 1.0", [("a", "passed", ["FR-01"]), ("b", "failed", ["FR-01"])], False),
     ("requirements >= 1.0", None, False),
     ("count.architecture.errors == 0", [("a", "passed", ["FR-01"])], True),
     ("code_quality >= 0.7", "metrik_na", False),
     ("code_quality.m >= 0.5", [("a", "passed", ["FR-01"])], True)],
)
def test_tc16_gates_sind_fail_closed(qproject: QualityProject, gate, tests, bestanden):
    """Scenario Outline: Gates sind fail-closed (CON-0196)."""
    standard_projekt(qproject, tests=tests if isinstance(tests, list) else None,
                     metrik={"m": 4})
    daten = _sonden(qproject)
    if tests is None:
        daten["probes"]["tests"]["command"] = "gibt-es-nicht-4711 > {out}"
    if tests == "metrik_na":
        daten["probes"]["metriken"]["command"] = "gibt-es-nicht-4711 > {out}"
    _sonden_setzen(qproject, daten)
    qproject.config_quality({"gates": [gate]})
    ergebnis, report = qproject.measure("--spec", "SPEC-0900")
    assert report["gates"][0]["passed"] is bestanden
    assert ergebnis.exit_code == (0 if bestanden else 1)


@pytest.mark.parametrize(
    ("gate", "fehler"),
    [("count.architecture.errors >= 0.8", "ganze Zahl erwartet"),
     ("requirements >= 3", "Wert in [0, 1] erwartet"),
     ("security >= 0.5", "unbekannter Pfad")],
)
def test_tc17_ungueltige_gates_sind_konfigurationsfehler(qproject: QualityProject, gate, fehler):
    """Scenario Outline: Ungültige Gates sind Konfigurationsfehler (CON-0196)."""
    standard_projekt(qproject)
    qproject.config_quality({"gates": [gate]})
    ergebnis = qproject.run("config", "validate")
    assert ergebnis.exit_code == 1
    assert fehler in ergebnis.output
    assert qproject.run("quality", "measure").exit_code == 2


def test_junit_hilfe_erzeugt_fr_properties():
    """Selbsttest der Hilfe: FR-Markierung steht als JUnit-Property im XML."""
    assert '<property name="fr" value="FR-01"/>' in junit([("t", "passed", ["FR-01"])])
    assert metrics({"m": 1})
