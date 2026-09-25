"""TST-0227 – CON-0198: Architektur-Baseline (.sdd/quality/arch-baseline.json).

Spec: SPEC-0054 · Contract: CON-0198
Schematests laufen sofort. Herabstufung, veraltete Einträge und das Fortschreiben prüfen
`sdd arch check` und überspringen, solange der Befehl fehlt.
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

EINTRAG = {"rule": "ARCH-03", "file": "tool/sdd_cli/decompose.py",
           "symbol": "ClaudeCliCompletionProvider", "reason": "hart verdrahtet",
           "fixed_by": "SPEC-0053"}


@pytest.fixture()
def qproject(tmp_path, monkeypatch) -> QualityProject:
    return make_project(tmp_path, monkeypatch)


def test_tc01_valid_instance_passes():
    """Valide Instanz besteht Schema-Validierung (CON-0198)."""
    assert schema_errors("baseline", {"version": 1, "entries": [EINTRAG]}) == []


def test_tc02_invalid_instance_rejected():
    """Beispiel aus dem Contract: leeres symbol, reason fehlt."""
    assert schema_errors("baseline", {"version": 1, "entries": [
        {"rule": "ARCH-03", "file": "tool/sdd_cli/decompose.py", "symbol": ""}]})


class TestSchemaInvarianten:
    @pytest.mark.parametrize("feld", ["rule", "file", "symbol", "reason"])
    def test_pflichtfelder(self, feld):
        eintrag = {k: v for k, v in EINTRAG.items() if k != feld}
        assert schema_errors("baseline", {"version": 1, "entries": [eintrag]})

    def test_fixed_by_ist_spec_id(self):
        assert schema_errors("baseline", {"version": 1,
                                          "entries": [{**EINTRAG, "fixed_by": "morgen"}]})


@requires_quality_cli
class TestWirkung:
    REGEL = {"id": "ARCH-01", "adr": "ADR-0101", "kind": "forbidden_dependency",
             "from": "web", "to_layers": ["cli"]}

    def _setup(self, p: QualityProject, edges: list[dict], baseline: list[dict] | None) -> None:
        p.quality_yaml({"imports": p.fixture_probe("imports", deps(edges), "sdd-deps",
                                                   role="deps")})
        p.architecture({"web": ["web/**"], "cli": ["cli/**"]}, [self.REGEL])
        p.adr("ADR-0101", "Web delegiert an CLI")
        if baseline is not None:
            p.write(".sdd/quality/arch-baseline.json",
                    json.dumps({"version": 1, "entries": baseline}))

    def test_inv01_inv02_passender_eintrag_stuft_herab(self, qproject: QualityProject):
        self._setup(qproject, [{"from": "web/a.py", "to": "cli/c.py", "symbol": "C", "line": 7}],
                    [{"rule": "ARCH-01", "file": "web/a.py", "symbol": "C", "reason": "alt"}])
        ergebnis = qproject.run("arch", "check", "--json")
        assert ergebnis.exit_code == 0
        verstoss = json.loads(ergebnis.stdout)["violations"][0]
        assert verstoss["severity"] == "warn" and verstoss["baselined"] is True

    def test_inv01_anderes_symbol_passt_nicht(self, qproject: QualityProject):
        self._setup(qproject, [{"from": "web/a.py", "to": "cli/c.py", "symbol": "D"}],
                    [{"rule": "ARCH-01", "file": "web/a.py", "symbol": "C", "reason": "alt"}])
        assert qproject.run("arch", "check").exit_code == 1

    def test_inv03_veralteter_eintrag(self, qproject: QualityProject):
        self._setup(qproject, [],
                    [{"rule": "ARCH-01", "file": "web/a.py", "symbol": "C", "reason": "alt"}])
        ergebnis = qproject.run("arch", "check", "--json")
        assert ergebnis.exit_code == 0
        assert json.loads(ergebnis.stdout)["stale_baseline_entries"] == 1

    def test_inv05_schreiben_erhaelt_vorhandene_eintraege(self, qproject: QualityProject):
        self._setup(qproject,
                    [{"from": "web/a.py", "to": "cli/c.py", "symbol": "C"},
                     {"from": "web/b.py", "to": "cli/c.py", "symbol": "C"}],
                    [{"rule": "ARCH-01", "file": "web/a.py", "symbol": "C",
                      "reason": "Altlast, SPEC-0053"}])
        assert qproject.run("arch", "check", "--write-baseline").exit_code == 0
        daten = json.loads((qproject.root / ".sdd/quality/arch-baseline.json").read_text())
        assert schema_errors("baseline", daten) == []
        gruende = {e["file"]: e["reason"] for e in daten["entries"]}
        assert gruende == {"web/a.py": "Altlast, SPEC-0053", "web/b.py": "TODO"}
