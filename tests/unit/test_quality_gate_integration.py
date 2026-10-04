"""SPEC-0054 FR-10, CON-0196 INV-08: Quality-Gates in Finalize, Auto-Merge und Gate-Datei."""
from __future__ import annotations

import json

import pytest

from sdd_cli.quality.gate_integration import check_quality_gates
from tests.support.quality_project import make_project, standard_projekt


@pytest.fixture()
def qproject(tmp_path, monkeypatch):
    return make_project(tmp_path, monkeypatch)


def _raw(qproject):
    import yaml

    return yaml.safe_load((qproject.root / ".sdd/config.yaml").read_text())


def test_ohne_quality_yaml_nicht_anwendbar(qproject):
    entscheidung = check_quality_gates(qproject.root, "SPEC-0900", _raw(qproject))
    assert entscheidung.passed is None


def test_modus_off(qproject):
    standard_projekt(qproject)
    qproject.config_quality({"finalize": "off", "gates": ["requirements >= 1.0"]})
    assert check_quality_gates(qproject.root, "SPEC-0900", _raw(qproject)).passed is None


def test_modus_off_gilt_nicht_fuer_auto_merge(qproject):
    standard_projekt(qproject, tests=[("a", "failed", ["FR-01"])])
    qproject.config_quality({"finalize": "off", "gates": ["requirements >= 1.0"]})
    e = check_quality_gates(qproject.root, "SPEC-0900", _raw(qproject), respect_mode=False)
    assert e.passed is False


def test_warn_mit_beleg_in_gate_datei(qproject):
    standard_projekt(qproject, tests=[("a", "failed", ["FR-01"])])
    qproject.config_quality({"gates": ["requirements >= 1.0"]})
    e = check_quality_gates(qproject.root, "SPEC-0900", _raw(qproject))
    assert e.passed is False and e.mode == "warn" and "requirements >= 1.0" in e.message
    gate = json.loads((qproject.root / ".sdd/pipeline/SPEC-0900-gate.json").read_text())
    eintrag = next(p for p in gate["phase_history"] if p["phase"] == "quality-gates")
    assert eintrag["result"] == "failed"
    assert (qproject.root / eintrag["report_path"]).is_file()
    assert eintrag["schema_version"] == 1 and "git_sha" in eintrag


def test_konfigurationsfehler_ist_fail_closed(qproject):
    standard_projekt(qproject)
    qproject.config_quality({"gates": ["security >= 1"]})
    e = check_quality_gates(qproject.root, "SPEC-0900", _raw(qproject))
    assert e.passed is False and "unbekannter Pfad" in e.message


def test_finalize_blockiert(qproject, monkeypatch):
    from sdd_cli.finalize import SpecFinalizer
    from sdd_cli.quality import gate_integration

    monkeypatch.setattr(gate_integration, "check_quality_gates",
                        lambda *a, **k: gate_integration.QualityGateDecision(
                            "block", False, "Quality-Gates nicht bestanden: requirements >= 1.0"))
    import subprocess

    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=qproject.root, check=True)
    # Identitaet im Repo, nicht per -c: finalize committet selbst und bricht
    # ohne Identitaet ab, bevor die Quality-Gates greifen (HF-0014).
    for args in (["config", "user.email", "t@t"], ["config", "user.name", "t"],
                 ["commit", "-q", "--allow-empty", "-m", "x"]):
        subprocess.run(["git", *args], cwd=qproject.root, check=True)
    from sdd_cli.config import load_config

    report = SpecFinalizer(load_config(qproject.root)).run("SPEC-0900", skip_container=True)
    assert report.error and "Quality-Gates" in report.error
    assert report.tests_passed is False
