"""`sdd review pattern accept|reject|list` — Pattern-Entscheidungen festhalten (#90).

SPEC-0044 hat `sdd pattern` entfernt, ohne Nachfolger. PatternRegistry und der
Katalog blieben, hatten aber keinen Aufrufer: `sdd review spec` erzeugte
Vorschlaege, deren Entscheidung nirgends landete. Die Skill-Datei half sich mit
einem `python3 -c`-Einzeiler an der CLI vorbei.
"""
from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest
from click.testing import CliRunner


@pytest.fixture
def projekt(tmp_path, monkeypatch):
    from sdd_cli.init import init_project

    init_project(tmp_path, title="Testprojekt")
    (tmp_path / ".sdd" / "specs" / "SPEC-0007-steuerung.md").write_text(
        "---\nid: SPEC-0007\ntitle: Steuerung\nstatus: draft\n---\n\n# Steuerung\n",
        encoding="utf-8",
    )
    con = tmp_path / ".sdd" / "contracts" / "behavior"
    con.mkdir(parents=True, exist_ok=True)
    (con / "CON-0016-steuerbefehle.md").write_text(
        "---\nid: CON-0016\ntitle: Steuerbefehle\nspec: SPEC-0007\nstatus: draft\n---\n\n# C\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _cli(*args: str):
    from sdd_cli.main import cli
    return CliRunner().invoke(cli, ["review", "pattern", *args])


def _register(root: Path, artefakt: str) -> list[dict]:
    datei = root / ".sdd" / "patterns" / f"{artefakt}-patterns.json"
    return json.loads(datei.read_text(encoding="utf-8"))["patterns"]


class TestAnnehmen:
    def test_schreibt_register(self, projekt):
        r = _cli("accept", "SPEC-0007", "Strategy", "--reason", "Austauschbare Treiber.",
                 "--url", "https://refactoring.guru/design-patterns/strategy")
        assert r.exit_code == 0, r.output
        [eintrag] = _register(projekt, "SPEC-0007")
        assert eintrag["pattern_name"] == "Strategy"
        assert eintrag["status"] == "accepted"
        assert eintrag["acceptance_reason"] == "Austauschbare Treiber."
        assert eintrag["refactoring_guru_url"].endswith("/strategy")

    def test_landet_im_projektweiten_katalog(self, projekt):
        """Der Katalog speist spaetere Vorschlaege (SPEC-0048) — der eigentliche
        Gewinn gegenueber einer Notiz im Contract-Text."""
        _cli("accept", "SPEC-0007", "Strategy", "--reason", "x")
        katalog = list((projekt / ".sdd" / "patterns").glob("_catalog*.json"))
        assert katalog, "kein Katalog angelegt"
        assert "Strategy" in katalog[0].read_text(encoding="utf-8")

    def test_funktioniert_auch_fuer_contracts(self, projekt):
        """Vorschlaege entstehen auch in `sdd review contract`."""
        r = _cli("accept", "CON-0016", "Command", "--reason", "Befehle als Objekte.")
        assert r.exit_code == 0, r.output
        assert _register(projekt, "CON-0016")[0]["pattern_name"] == "Command"


class TestAblehnen:
    def test_schreibt_ablehnung_mit_grund(self, projekt):
        r = _cli("reject", "SPEC-0007", "Singleton", "--reason", "Globaler Zustand.")
        assert r.exit_code == 0, r.output
        [eintrag] = _register(projekt, "SPEC-0007")
        assert eintrag["status"] == "rejected"
        assert eintrag["rejection_reason"] == "Globaler Zustand."
        assert eintrag["acceptance_reason"] is None

    def test_umentscheiden_ueberschreibt_statt_zu_verdoppeln(self, projekt):
        _cli("accept", "SPEC-0007", "Strategy", "--reason", "erst ja")
        _cli("reject", "SPEC-0007", "Strategy", "--reason", "dann nein")
        eintraege = _register(projekt, "SPEC-0007")
        assert len(eintraege) == 1
        assert eintraege[0]["status"] == "rejected"


class TestVertrag:
    """CON-0048: exit 1 ohne Begruendung, exit 2 bei unbekannter ID."""

    @pytest.mark.parametrize("aktion", ["accept", "reject"])
    def test_ohne_reason_exit_1(self, projekt, aktion):
        r = _cli(aktion, "SPEC-0007", "Strategy")
        assert r.exit_code == 1
        assert "--reason ist erforderlich" in r.output
        assert not (projekt / ".sdd" / "patterns" / "SPEC-0007-patterns.json").exists()

    @pytest.mark.parametrize("aktion", ["accept", "reject"])
    def test_leere_reason_zaehlt_nicht(self, projekt, aktion):
        r = _cli(aktion, "SPEC-0007", "Strategy", "--reason", "   ")
        assert r.exit_code == 1

    @pytest.mark.parametrize("aktion", ["accept", "reject"])
    def test_unbekannte_id_exit_2(self, projekt, aktion):
        r = _cli(aktion, "SPEC-9999", "Strategy", "--reason", "x")
        assert r.exit_code == 2
        assert "nicht gefunden" in r.output


class TestListe:
    def test_leeres_register_ist_kein_fehler(self, projekt):
        r = _cli("list", "SPEC-0007")
        assert r.exit_code == 0
        assert "Keine Pattern-Entscheidungen" in r.output

    def test_zeigt_entscheidungen(self, projekt):
        _cli("accept", "SPEC-0007", "Strategy", "--reason", "ja")
        _cli("reject", "SPEC-0007", "Singleton", "--reason", "nein")
        r = _cli("list", "SPEC-0007")
        assert r.exit_code == 0
        for erwartet in ("Strategy", "Singleton", "accepted", "rejected"):
            assert erwartet in r.output

    def test_ohne_id_zeigt_alle(self, projekt):
        _cli("accept", "SPEC-0007", "Strategy", "--reason", "ja")
        _cli("accept", "CON-0016", "Command", "--reason", "ja")
        r = _cli("list")
        assert r.exit_code == 0
        assert "Strategy" in r.output and "Command" in r.output

    def test_unbekannte_id_exit_2(self, projekt):
        assert _cli("list", "SPEC-9999").exit_code == 2


class TestHinweisNachDerVorschlagsphase:
    def test_nennt_den_befehl(self):
        """Der Hinweis nach `sdd review spec` nannte vor #68 einen entfernten
        Befehl, danach keinen. Jetzt nennt er den, den es gibt."""
        from sdd_cli import main

        quelle = inspect.getsource(main._run_pattern_phase)
        assert "sdd review pattern" in quelle
