"""Regressions-Befunde duerfen keine doppelten IDs bekommen.

Jeder Lauf nummerierte seine Findings neu ab R001, waehrend aufgeloeste
Eintraege stehen blieben. Nach drei Laeufen stand in
.sdd/conflict-reports/SPEC-0003-conflicts.json zweimal CF-0003-R001 mit
verschiedenem Inhalt:

    CF-0003-R001 | resolved | FR-19 definiert Veraltung als 'mehr als zwei…
    CF-0003-R001 | open     | SPEC-0002 hält die Slicer-Schätzung je Dateiname…

`sdd conflict resolve SPEC-0003 CF-0003-R001` trifft die erste Fundstelle. Die
zweite bleibt offen und ist ueber die CLI nicht mehr erreichbar; die Begruendung
fuer den einen Konflikt ueberschreibt die des anderen.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

# Die neuen Helfer lazy, damit die RED-Pruefung nicht auf einen
# Collection-Error zusammenfaellt.
from sdd_cli.regression_check import CheckFinding, RegressionCheckChain


def _conflict_identity(c):
    from sdd_cli.regression_check import _conflict_identity as _impl
    return _impl(c)


def _next_conflict_id(bestand, spec_num):
    from sdd_cli.regression_check import _next_conflict_id as _impl
    return _impl(bestand, spec_num)


def _finding(section: str, beschreibung: str, own: str = "FR-01") -> CheckFinding:
    return CheckFinding(
        spec_id="SPEC-0002", section=section, own_section=own,
        description=beschreibung, severity="error", source="rule", type="semantic",
    )


def _bericht(root: Path) -> dict:
    p = root / ".sdd" / "conflict-reports" / "SPEC-0003-conflicts.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _lauf(root: Path, findings: list[CheckFinding]) -> dict:
    RegressionCheckChain(root)._persist_findings("SPEC-0003", findings)
    return _bericht(root)


class TestKeineDoppeltenIds:
    def test_zweiter_lauf_kollidiert_nicht(self, tmp_path):
        """Der gemeldete Fall: R001 aufgeloest, dann ein neuer Befund."""
        _lauf(tmp_path, [_finding("FR-19", "erster Widerspruch")])
        bericht = _bericht(tmp_path)
        bericht["conflicts"][0]["status"] = "resolved"
        bericht["conflicts"][0]["resolution"] = "begruendet"
        (tmp_path / ".sdd" / "conflict-reports" / "SPEC-0003-conflicts.json").write_text(
            json.dumps(bericht), encoding="utf-8")

        daten = _lauf(tmp_path, [_finding("FR-22", "zweiter Widerspruch")])

        ids = [c["id"] for c in daten["conflicts"]]
        assert len(ids) == len(set(ids)), f"doppelte IDs: {ids}"
        assert ids == ["CF-0003-R001", "CF-0003-R002"]

    def test_aufgeloester_befund_behaelt_seine_begruendung(self, tmp_path):
        _lauf(tmp_path, [_finding("FR-19", "erster")])
        bericht = _bericht(tmp_path)
        bericht["conflicts"][0].update(status="resolved", resolution="begruendet")
        (tmp_path / ".sdd" / "conflict-reports" / "SPEC-0003-conflicts.json").write_text(
            json.dumps(bericht), encoding="utf-8")

        daten = _lauf(tmp_path, [_finding("FR-22", "zweiter")])

        alt = next(c for c in daten["conflicts"] if c["id"] == "CF-0003-R001")
        assert alt["resolution"] == "begruendet" and alt["status"] == "resolved"

    def test_ueber_mehrere_laeufe_eindeutig(self, tmp_path):
        for i in range(1, 6):
            _lauf(tmp_path, [_finding(f"FR-{i:02d}", f"Widerspruch {i}")])
            bericht = _bericht(tmp_path)
            for c in bericht["conflicts"]:
                c["status"] = "resolved"
            (tmp_path / ".sdd" / "conflict-reports" / "SPEC-0003-conflicts.json").write_text(
                json.dumps(bericht), encoding="utf-8")

        ids = [c["id"] for c in _bericht(tmp_path)["conflicts"]]
        assert len(ids) == len(set(ids)) == 5, ids


class TestGleicherWiderspruchWirdAktualisiert:
    def test_kein_zweiter_eintrag(self, tmp_path):
        _lauf(tmp_path, [_finding("FR-19", "alte Formulierung")])
        daten = _lauf(tmp_path, [_finding("FR-19", "neue Formulierung")])

        assert len(daten["conflicts"]) == 1
        assert daten["conflicts"][0]["detail"] == "neue Formulierung"

    def test_id_bleibt_stabil(self, tmp_path):
        _lauf(tmp_path, [_finding("FR-19", "alt")])
        erste_id = _bericht(tmp_path)["conflicts"][0]["id"]
        daten = _lauf(tmp_path, [_finding("FR-19", "neu")])
        assert daten["conflicts"][0]["id"] == erste_id

    def test_aufloesung_ueberlebt_den_erneuten_fund(self, tmp_path):
        """Der LLM formuliert bei jedem Lauf neu — die Begruendung bleibt."""
        _lauf(tmp_path, [_finding("FR-19", "alt")])
        bericht = _bericht(tmp_path)
        bericht["conflicts"][0].update(status="resolved", resolution="geprueft")
        (tmp_path / ".sdd" / "conflict-reports" / "SPEC-0003-conflicts.json").write_text(
            json.dumps(bericht), encoding="utf-8")

        daten = _lauf(tmp_path, [_finding("FR-19", "neu formuliert")])

        assert len(daten["conflicts"]) == 1
        assert daten["conflicts"][0]["resolution"] == "geprueft"
        assert daten["conflicts"][0]["detail"] == "neu formuliert"

    def test_identitaet_ist_das_abschnittspaar(self):
        a = _conflict_identity({"type": "semantic", "new_contract": "FR-01",
                                "conflicting_contract": "SPEC-0002:FR-19"})
        b = _conflict_identity({"type": "semantic", "new_contract": "FR-01",
                                "conflicting_contract": "SPEC-0002:FR-19",
                                "detail": "anders formuliert"})
        assert a == b, "Die Beschreibung darf die Identitaet nicht bestimmen"


class TestVerschwundeneBefundeEntfallen:
    def test_offener_befund_ohne_neuen_fund_wird_entfernt(self, tmp_path):
        _lauf(tmp_path, [_finding("FR-19", "war mal da")])
        daten = _lauf(tmp_path, [])
        assert daten["conflicts"] == []

    def test_fremde_quellen_bleiben_unangetastet(self, tmp_path):
        _lauf(tmp_path, [_finding("FR-19", "regression")])
        pfad = tmp_path / ".sdd" / "conflict-reports" / "SPEC-0003-conflicts.json"
        bericht = json.loads(pfad.read_text(encoding="utf-8"))
        bericht["conflicts"].append({"id": "CF-0003-A001", "source": "analyze",
                                     "status": "open", "type": "x",
                                     "new_contract": "", "conflicting_contract": ""})
        pfad.write_text(json.dumps(bericht), encoding="utf-8")

        daten = _lauf(tmp_path, [])
        assert [c["id"] for c in daten["conflicts"]] == ["CF-0003-A001"]


class TestNaechsteId:
    def test_zaehlt_ueber_die_hoechste_hinaus(self):
        bestand = [{"id": "CF-0003-R001"}, {"id": "CF-0003-R007"}]
        assert _next_conflict_id(bestand, "0003") == "CF-0003-R008"

    def test_leerer_bestand(self):
        assert _next_conflict_id([], "0003") == "CF-0003-R001"

    def test_fremde_ids_stoeren_nicht(self):
        assert _next_conflict_id([{"id": "CF-0003-A009"}], "0003") == "CF-0003-R001"
