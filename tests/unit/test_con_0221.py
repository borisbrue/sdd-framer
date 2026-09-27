# AUTO-GENERATED from CON-0221 via sdd test generate — do not delete
"""TST-0250 – CON-0221: Bench-Matrix und Suite.

Spec: SPEC-0056 · Contract: CON-0221
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sdd_cli.bench.config import BenchError, load_matrix, load_suite, overlay
from sdd_cli.config import SddConfig
from sdd_cli.pipeline.schemas import errors

PROFILE = {"lokal": {"provider": "openai-compat", "base_url": "http://h/v1", "model": "q"},
           "claude": {"provider": "claude-cli"}}


def _cfg(tmp_path: Path) -> SddConfig:
    raw = {"llm": {"profiles": PROFILE}}
    return SddConfig(root=tmp_path, raw=raw, raw_basis=raw)


def _matrix(tmp_path: Path, daten: dict) -> Path:
    pfad = tmp_path / "matrix.yaml"
    pfad.write_text(yaml.safe_dump(daten), encoding="utf-8")
    return pfad


def test_tc01_valid_instance_passes(tmp_path):
    """Valide Instanz besteht Schema-Validierung (CON-0221)."""
    matrix = {"suites": ["roles"], "profiles": ["lokal"], "variants": {"think": {"thinking": True}},
              "sweep": {"role": "implementer", "profiles": ["lokal", "lokal@think"]},
              "budget": {"max_tokens": 1000}}
    suite = {"name": "regen", "kind": "regen", "commit": "96e622b", "test_command": "true",
             "tasks": [{"module": "a.py", "tests": ["t.py"]}]}
    assert errors("bench-matrix", matrix, "matrix") == []
    assert errors("bench-matrix", suite, "suite") == []


@pytest.mark.parametrize("definition, daten", [
    ("matrix", {"suites": []}),
    ("matrix", {"suites": ["roles"], "assignments": [{"name": "a b", "roles": {}}]}),
    ("matrix", {"suites": ["roles"], "profiles": ["x"], "unbekannt": 1}),
    ("suite", {"name": "regen", "kind": "regen", "test_command": "true"}),
])
def test_tc02_invalid_instance_rejected(definition, daten):
    """Invalide Instanz wird abgelehnt (CON-0221)."""
    assert errors("bench-matrix", daten, definition)


def test_stern_varianten_und_sweep(tmp_path):
    """INV-01/03: `*` füllt die Pipeline-Rollen; Sweep erzeugt sweep-<profil>."""
    pfad = _matrix(tmp_path, {
        "suites": ["regen"], "variants": {"think": {"thinking": True}},
        "assignments": [{"name": "basis", "roles": {"*": "lokal", "supervisor": "claude"}}],
        "sweep": {"role": "implementer", "profiles": ["lokal", "lokal@think"]}})
    m = load_matrix(pfad, _cfg(tmp_path))
    basis = m.assignments[0].roles
    assert basis["decomposer"] == "lokal" and basis["supervisor"] == "claude"
    assert [a.name for a in m.assignments] == ["basis", "sweep-lokal", "sweep-lokal-think"]
    assert m.assignments[2].roles["implementer"] == "lokal@think"
    assert m.assignments[2].roles["supervisor"] == "claude"


def test_ohne_stern_gilt_die_config(tmp_path):
    pfad = _matrix(tmp_path, {"suites": ["regen"],
                              "assignments": [{"name": "a", "roles": {"implementer": "lokal"}}]})
    roles = load_matrix(pfad, _cfg(tmp_path)).assignments[0].roles
    assert roles["implementer"] == "lokal" and roles["decomposer"] == "config"


@pytest.mark.parametrize("ref", ["fehlt", "lokal@fehlt"])
def test_unbekanntes_profil_oder_variante(tmp_path, ref):
    """INV-02: unbekannte Profile oder Varianten sind Fehler."""
    pfad = _matrix(tmp_path, {"suites": ["roles"], "profiles": [ref]})
    with pytest.raises(BenchError):
        load_matrix(pfad, _cfg(tmp_path))


def test_variante_nur_im_speicher(tmp_path):
    """INV-02: die Variante wirkt auf eine Config im Speicher, nie auf config.yaml."""
    cfg = _cfg(tmp_path)
    pfad = _matrix(tmp_path, {"suites": ["roles"], "profiles": ["lokal@think"],
                              "variants": {"think": {"thinking": True}}})
    m = load_matrix(pfad, cfg)
    neu = overlay(cfg, m, {"implementer": "lokal@think"})
    assert neu.raw["llm"]["profiles"]["lokal@think"] == {**PROFILE["lokal"], "thinking": True}
    assert neu.raw["llm"]["roles"]["implementer"] == {"profile": "lokal@think"}
    assert "roles" not in cfg.raw["llm"]


def test_doppelte_namen(tmp_path):
    pfad = _matrix(tmp_path, {"suites": ["regen"], "assignments": [
        {"name": "a", "roles": {"*": "lokal"}}, {"name": "a", "roles": {"*": "claude"}}]})
    with pytest.raises(BenchError, match="doppelt"):
        load_matrix(pfad, _cfg(tmp_path))


def test_suite_laden_und_art(tmp_path):
    """INV-04: regen verlangt commit, test_command und tasks."""
    (tmp_path / "bench/suites").mkdir(parents=True)
    (tmp_path / "bench/suites/regen.yaml").write_text(yaml.safe_dump(
        {"name": "regen", "kind": "regen", "test_command": "true"}))
    with pytest.raises(BenchError):
        load_suite(tmp_path, "regen")
    with pytest.raises(BenchError, match="fehlt"):
        load_suite(tmp_path, "gibtsnicht")
    from sdd_cli.bench.suites import task_class

    with pytest.raises(BenchError, match="Unbekannte Suite-Art"):
        task_class("e2e-fehlt")
