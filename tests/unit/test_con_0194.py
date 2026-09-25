"""TST-0223 – CON-0194: Architekturregeln (.sdd/architecture.yaml).

Spec: SPEC-0054 · Contract: CON-0194
Schematests laufen sofort. Die Auswertung je Regelart (Strategy) prüft `sdd arch check --json`
auf vorbereiteten sdd-deps-Kanten und überspringt, solange der Befehl fehlt.
"""
from __future__ import annotations

import json

import pytest

from tests.support.quality_project import (
    QualityProject,
    deps,
    make_project,
    requires_quality_cli,
    schema_errors,
)

LAYERS = {"web": ["web/**"], "cli": ["cli/**"], "llm": ["llm/**"]}


def _regel(**felder: object) -> dict:
    return {"id": "ARCH-01", "adr": "ADR-0101", **felder}


def _datei(rules: list[dict], layers: dict | None = None) -> dict:
    return {"version": 1, "layers": layers or LAYERS, "rules": rules}


@pytest.fixture()
def qproject(tmp_path, monkeypatch) -> QualityProject:
    return make_project(tmp_path, monkeypatch)


def test_tc01_valid_instance_passes():
    """Valide Instanz mit allen vier Regelarten besteht (CON-0194)."""
    instanz = _datei([
        _regel(kind="forbidden_dependency", **{"from": "web"}, to_paths=["cli/writer.py"]),
        _regel(id="ARCH-02", kind="allowed_dependencies", graph={"web": ["cli"], "cli": ["llm"]}),
        _regel(id="ARCH-03", kind="forbidden_call", **{"in": ["cli"]}, calls=["subprocess.*"],
               args_match="^claude$", **{"except": ["llm/claude.py"]}),
        _regel(id="ARCH-04", kind="write_ownership", paths=[".sdd/specs/**"], owners="cli",
               severity="warn"),
    ])
    assert schema_errors("architecture", instanz) == []


def test_tc02_invalid_instance_rejected():
    """Beispiel aus dem Contract: adr fehlt, fremdes Feld, altes 'to'."""
    instanz = _datei([{"id": "ARCH-01", "kind": "forbidden_dependency", "from": "web",
                       "to": ["cli"], "calls": ["x"]}])
    assert schema_errors("architecture", instanz)


class TestSchemaInvarianten:
    def test_inv01_adr_pflicht(self):
        regel = {"id": "ARCH-01", "kind": "forbidden_dependency", "from": "web",
                 "to_layers": ["cli"]}
        assert schema_errors("architecture", _datei([regel]))

    @pytest.mark.parametrize("rid", ["ARCH-1", "arch-01", "ARCH-A1"])
    def test_inv01_id_format(self, rid):
        assert schema_errors("architecture", _datei([_regel(
            id=rid, kind="forbidden_dependency", **{"from": "web"}, to_layers=["cli"])]))

    def test_inv03_fremde_felder_je_art(self):
        assert schema_errors("architecture", _datei([_regel(
            kind="write_ownership", paths=["x/**"], owners="cli", calls=["y"])]))

    def test_inv05_forbidden_dependency_braucht_ziel(self):
        assert schema_errors("architecture", _datei([_regel(kind="forbidden_dependency",
                                                            **{"from": "web"})]))

    def test_severity_geschlossen(self):
        assert schema_errors("architecture", _datei([_regel(
            kind="forbidden_dependency", **{"from": "web"}, to_layers=["cli"],
            severity="info")]))


@requires_quality_cli
class TestAuswertung:
    def _check(self, p: QualityProject, rules: list[dict], edges: list[dict],
               kinds: tuple[str, ...] = ("import", "call", "write"),
               layers: dict | None = None) -> dict:
        p.quality_yaml({"imports": p.fixture_probe("imports", deps(edges, kinds), "sdd-deps",
                                                   role="deps")})
        p.architecture(layers or LAYERS, rules)
        p.adr("ADR-0101", "Testentscheidung")
        ergebnis = p.run("arch", "check", "--json")
        assert ergebnis.exit_code in (0, 1), ergebnis.output
        return json.loads(ergebnis.stdout)

    def _verstoesse(self, arch: dict) -> list[tuple[str, str, str]]:
        return sorted((v["rule"], v["file"], v["symbol"]) for v in arch["violations"])

    def test_forbidden_dependency_to_paths(self, qproject: QualityProject):
        arch = self._check(qproject,
                           [_regel(kind="forbidden_dependency", **{"from": "web"},
                                   to_paths=["cli/writer.py"])],
                           [{"from": "web/routes.py", "to": "cli/writer.py", "symbol": "write",
                             "line": 4},
                            {"from": "web/routes.py", "to": "cli/reader.py", "symbol": "read"}])
        assert self._verstoesse(arch) == [("ARCH-01", "web/routes.py", "write")]
        assert arch["violations"][0]["line"] == 4
        assert arch["violations"][0]["adr"] == "ADR-0101"

    def test_forbidden_dependency_to_layers(self, qproject: QualityProject):
        arch = self._check(qproject,
                           [_regel(kind="forbidden_dependency", **{"from": "web"},
                                   to_layers=["llm"])],
                           [{"from": "web/a.py", "to": "llm/p.py", "symbol": "P"},
                            {"from": "web/a.py", "to": "cli/c.py", "symbol": "C"}])
        assert self._verstoesse(arch) == [("ARCH-01", "web/a.py", "P")]

    def test_inv04_allowed_dependencies(self, qproject: QualityProject):
        arch = self._check(qproject,
                           [_regel(kind="allowed_dependencies", graph={"web": ["cli"],
                                                                       "cli": ["llm"]})],
                           [{"from": "web/a.py", "to": "cli/c.py", "symbol": "ok1"},
                            {"from": "cli/c.py", "to": "llm/p.py", "symbol": "ok2"},
                            {"from": "cli/c.py", "to": "cli/d.py", "symbol": "gleiche_schicht"},
                            {"from": "cli/c.py", "to": "web/a.py", "symbol": "rueckwaerts"},
                            {"from": "llm/p.py", "to": "cli/c.py", "symbol": "ohne_eintrag"}])
        assert self._verstoesse(arch) == [("ARCH-01", "cli/c.py", "rueckwaerts"),
                                          ("ARCH-01", "llm/p.py", "ohne_eintrag")]

    def test_inv06_forbidden_call_mit_args_und_except(self, qproject: QualityProject):
        arch = self._check(qproject,
                           [_regel(kind="forbidden_call", **{"in": ["cli", "llm"]},
                                   calls=["subprocess.*"], args_match="^claude$",
                                   **{"except": ["llm/claude.py"]})],
                           [{"from": "cli/a.py", "kind": "call", "symbol": "subprocess.run",
                             "args": ["claude", "--print"]},
                            {"from": "cli/b.py", "kind": "call", "symbol": "subprocess.run",
                             "args": ["git"]},
                            {"from": "llm/claude.py", "kind": "call", "symbol": "subprocess.Popen",
                             "args": ["claude"]},
                            {"from": "cli/c.py", "kind": "call", "symbol": "subprocess.os.system",
                             "args": ["claude"]}])
        assert self._verstoesse(arch) == [("ARCH-01", "cli/a.py", "subprocess.run")]

    def test_write_ownership(self, qproject: QualityProject):
        arch = self._check(qproject,
                           [_regel(kind="write_ownership", paths=[".sdd/specs/**"],
                                   owners=["cli"])],
                           [{"from": "web/a.py", "to": ".sdd/specs/SPEC-0001.md", "kind": "write",
                             "symbol": "pathlib.Path.write_text"},
                            {"from": "cli/b.py", "to": ".sdd/specs/SPEC-0001.md", "kind": "write",
                             "symbol": "pathlib.Path.write_text"},
                            {"from": "web/a.py", "to": "build/out.txt", "kind": "write",
                             "symbol": "open"}])
        assert self._verstoesse(arch) == [("ARCH-01", "web/a.py", "pathlib.Path.write_text")]

    def test_inv02_erste_passende_schicht_gewinnt(self, qproject: QualityProject):
        layers = {"web": ["src/web/**"], "core": ["src/**"]}
        arch = self._check(qproject,
                           [_regel(kind="forbidden_dependency", **{"from": "core"},
                                   to_layers=["web"])],
                           [{"from": "src/web/a.py", "to": "src/web/b.py", "symbol": "innen"},
                            {"from": "src/x.py", "to": "src/web/b.py", "symbol": "verboten"}],
                           layers=layers)
        assert self._verstoesse(arch) == [("ARCH-01", "src/x.py", "verboten")]

    def test_inv02_dateien_ohne_schicht_werden_ignoriert(self, qproject: QualityProject):
        arch = self._check(qproject,
                           [_regel(kind="allowed_dependencies", graph={"web": []})],
                           [{"from": "scripts/x.py", "to": "web/a.py", "symbol": "s"}])
        assert arch["violations"] == []

    def test_inv03_fehlende_kantenart_macht_regel_na(self, qproject: QualityProject):
        arch = self._check(qproject,
                           [_regel(kind="forbidden_call", **{"in": ["cli"]}, calls=["x.*"])],
                           [], kinds=("import",))
        assert [r["rule"] for r in arch["rules_na"]] == ["ARCH-01"]

    def test_inv04_unaufgeloeste_kanten_sind_kein_verstoss(self, qproject: QualityProject):
        arch = self._check(qproject,
                           [_regel(kind="forbidden_dependency", **{"from": "web"},
                                   to_layers=["cli"])],
                           [{"from": "web/a.py", "to": None, "symbol": "dyn"}])
        assert arch["violations"] == []
        assert arch["unresolved_edges"] == 1

    def test_inv07_unbekannte_schicht_macht_regel_na(self, qproject: QualityProject):
        arch = self._check(qproject,
                           [_regel(kind="forbidden_dependency", **{"from": "gibtsnicht"},
                                   to_layers=["cli"])], [])
        na = {r["rule"]: r["reason"] for r in arch["rules_na"]}
        assert "unbekannte Schicht" in na["ARCH-01"]

    def test_inv09_schluessel_ist_stabil_gegen_zeilen(self, tmp_path, monkeypatch):
        regel = [_regel(kind="forbidden_dependency", **{"from": "web"}, to_layers=["cli"])]
        a = self._check(make_project(tmp_path / "a", monkeypatch), regel,
                        [{"from": "web/a.py", "to": "cli/c.py", "symbol": "C", "line": 3}])
        b = self._check(make_project(tmp_path / "b", monkeypatch), regel,
                        [{"from": "web/a.py", "to": "cli/c.py", "symbol": "C", "line": 30}])
        assert self._verstoesse(a) == self._verstoesse(b)
