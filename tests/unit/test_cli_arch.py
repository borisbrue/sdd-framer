"""SPEC-0054 FR-07, CON-0197: CLI sdd arch check und sdd arch init."""
from __future__ import annotations

import json

import pytest

from tests.support.quality_project import deps, make_project


@pytest.fixture()
def qproject(tmp_path, monkeypatch):
    return make_project(tmp_path, monkeypatch)


def _projekt(p, edges):
    p.quality_yaml({"imports": p.fixture_probe("imports", deps(edges), "sdd-deps", role="deps")})
    p.architecture({"web": ["web/**"], "core": ["core/**"]},
                   [{"id": "ARCH-01", "adr": "ADR-0007", "kind": "forbidden_dependency",
                     "from": "web", "to_layers": ["core"]}])
    p.adr("ADR-0007", "Web ruft den Kern nur über die CLI")


def test_ohne_verstoss_exit_0(qproject):
    _projekt(qproject, [])
    assert qproject.run("arch", "check").exit_code == 0


def test_json_ist_architecture_objekt(qproject):
    _projekt(qproject, [{"from": "web/a.py", "to": "core/b.py", "symbol": "B", "line": 2}])
    ergebnis = qproject.run("arch", "check", "--json")
    assert ergebnis.exit_code == 1
    daten = json.loads(ergebnis.stdout)
    assert daten["violations"][0]["adr_title"] == "Web ruft den Kern nur über die CLI"


def test_ohne_deps_sonde_exit_2(qproject):
    qproject.quality_yaml({"x": qproject.fixture_probe("x", "{}", "sdd-metrics")})
    qproject.architecture({"web": ["web/**"]}, [])
    ergebnis = qproject.run("arch", "check")
    assert ergebnis.exit_code == 2 and "role: deps" in ergebnis.output


def test_init_ueberschreibt_nicht(qproject):
    (qproject.root / "pkg").mkdir()
    (qproject.root / "pkg/a.py").write_text("x")
    qproject.write(".sdd/architecture.yaml", "version: 1\nlayers: {eigen: ['x/**']}\nrules: []\n")
    assert qproject.run("arch", "init").exit_code == 0
    assert "eigen" in (qproject.root / ".sdd/architecture.yaml").read_text()
    assert (qproject.root / ".sdd/architecture.yaml.new").is_file()
