"""SPEC-0054 FR-01/FR-02, CON-0192: Laden und Prüfen von .sdd/quality.yaml."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from sdd_cli.quality.config import (
    QualityConfigError,
    check_quality_config,
    load_quality_config,
)
from sdd_cli.quality.schemas import load_schema
from sdd_cli.quality.settings import QualitySettings

REPO = Path(__file__).resolve().parents[2]
CONTRACT_SCHEMAS = {
    "quality-config": "quality-config-sonden-normierung-und-suppressions-in-sdd-quality-yaml",
    "exchange-formats": "austauschformate-sdd-deps-sdd-metrics-und-sdd-findings",
    "architecture-rules": "architekturregeln-und-baseline",
    "arch-baseline": "architektur-baseline",
    "quality-report": "quality-report",
}


@pytest.mark.parametrize(("paket", "contract"), CONTRACT_SCHEMAS.items())
def test_paket_schemas_entsprechen_den_contract_artefakten(paket, contract):
    artefakt = REPO / ".sdd/contracts/data" / f"{contract}.schema.json"
    assert load_schema(paket) == json.loads(artefakt.read_text(encoding="utf-8"))


def _schreiben(root: Path, daten: dict) -> None:
    (root / ".sdd").mkdir(parents=True, exist_ok=True)
    (root / ".sdd/quality.yaml").write_text(yaml.safe_dump(daten, sort_keys=False), encoding="utf-8")


def test_laden_liefert_sonden_in_deklarationsreihenfolge(tmp_path):
    _schreiben(tmp_path, {"version": 1, "probes": {
        "b": {"command": "x > {out}", "format": "sarif", "metric": "lint_per_kloc"},
        "a": {"command": "y > {out}", "format": "junit", "role": "tests", "fr_marker": "name"},
    }, "normalization": {"m": {"good": 0, "bad": 5}}, "paths": ["src/**"]})
    cfg = load_quality_config(tmp_path)
    assert [p.name for p in cfg.probes] == ["b", "a"]
    assert cfg.probe_for_role("tests").name == "a"
    assert cfg.probe_for_role("deps") is None
    assert cfg.probes[0].timeout_seconds == 600
    assert cfg.normalization["m"].bad == 5
    assert cfg.paths == ["src/**"]


def test_fehlende_datei(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_quality_config(tmp_path)


def test_schemafehler_mit_feldpfad(tmp_path):
    _schreiben(tmp_path, {"version": 1, "probes": {"lint": {"command": "ruff", "format": "sarif"}}})
    with pytest.raises(QualityConfigError) as fehler:
        load_quality_config(tmp_path)
    assert "probes.lint.command" in [p.path for p in fehler.value.problems]


def test_doppelte_rolle_nennt_beide_sonden():
    probleme = check_quality_config({"version": 1, "probes": {
        "eins": {"command": "a > {out}", "format": "junit", "role": "tests", "fr_marker": "name"},
        "zwei": {"command": "b > {out}", "format": "junit", "role": "tests", "fr_marker": "name"},
    }})
    assert len(probleme) == 1
    assert "eins" in probleme[0].message and "zwei" in probleme[0].message


def test_gleiche_normierungsgrenzen_sind_fehler():
    probleme = check_quality_config({"version": 1, "probes": {
        "m": {"command": "a > {out}", "format": "sdd-metrics"}},
        "normalization": {"m": {"good": 3, "bad": 3}}})
    assert [p.path for p in probleme] == ["normalization.m"]


def test_settings_defaults():
    s = QualitySettings.from_raw({})
    assert s.root_weights == {"requirements": 0.5, "architecture": 0.25, "code_quality": 0.25,
                              "judge": 0.0}
    assert s.holdout_weight == 0.5
    assert s.architecture_threshold == 5
    assert s.severity_weights == {"error": 1.0, "warn": 0.25}
    assert s.gates == [] and s.finalize == "warn"


def test_settings_aus_config():
    s = QualitySettings.from_raw({"quality": {
        "weights": {"requirements": {"holdout": 0.25}, "judge": 0.1,
                    "code_quality": {"lint_per_kloc": 2}},
        "architecture": {"threshold": 3, "severity_weights": {"warn": 0.5}},
        "gates": ["requirements >= 1.0"], "finalize": "block"}})
    assert s.holdout_weight == 0.25 and s.root_weights["judge"] == 0.1
    assert s.metric_weight("lint_per_kloc") == 2 and s.metric_weight("anders") == 1
    assert s.architecture_threshold == 3
    assert s.severity_weights == {"error": 1.0, "warn": 0.5}
    assert s.gates == ["requirements >= 1.0"] and s.finalize == "block"
