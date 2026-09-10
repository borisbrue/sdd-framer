"""`sdd test generate` darf eine ausimplementierte Testdatei nicht zerstoeren (#92).

Jeder Test hier bildet ein Symptom aus BEFUND-test-generate-2026-09-09.md ab:
Moduldocstring, Importe, Fixtures, Konstanten, Hilfsklassen, Dekoratoren und —
der Fall, der die Collection zum Scheitern brachte — mehrzeilige Signaturen.
"""
from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest

# Eine Datei, wie sie nach dem Ausimplementieren aussieht: mit allem, was der
# alte Generator nicht kannte.
AUSIMPLEMENTIERT = textwrap.dedent('''\
    """Steuerbefehle fuer den Drucker (CON-0016)."""
    from __future__ import annotations

    import json

    import httpx
    import pytest

    BASIS = "http://localhost:8000"

    AKTIONEN = ["start", "stop", "pause"]


    class Drucker:
        def __init__(self, name):
            self.name = name


    @pytest.fixture
    def drucker():
        return Drucker("prusa")


    @pytest.mark.parametrize("aktion", AKTIONEN)
    def test_tc13_ohne_token_kein_befehl(drucker, aktion):
        """Ohne Token wird kein Befehl gesendet."""
        assert aktion in AKTIONEN


    def test_tc10_409_bedeutet_ausnahmslos_nichts_gesendet(
        drucker,
        aktion,
        grund,
    ):
        """Mehrzeilige Signatur — genau der Fall, der den Koerper verlor."""
        assert drucker.name == "prusa"
        assert json.dumps({"a": 1})
''')

VORLAGE = textwrap.dedent('''\
    # AUTO-GENERATED from CON-0016 via sdd test generate — do not delete
    """Contract-Tests fuer Steuerbefehle (CON-0016)."""
    from __future__ import annotations

    import pytest


    def test_tc01_start():
        """Scenario: Start (CON-0016)."""
        pytest.skip("Test noch nicht implementiert")


    def test_tc13_ohne_token_kein_befehl():
        """Scenario: Ohne Token (CON-0016)."""
        pytest.skip("Test noch nicht implementiert")
''')


@pytest.fixture
def generator(tmp_path):
    from sdd_cli.test_generator import TestGenerator
    return TestGenerator(tmp_path)


@pytest.fixture
def ziel(tmp_path):
    p = tmp_path / "tests" / "contract" / "test_steuerbefehle.py"
    p.parent.mkdir(parents=True)
    p.write_text(AUSIMPLEMENTIERT, encoding="utf-8")
    return p


def _namen(text: str) -> set[str]:
    """Nur Testfunktionen — Fixtures zaehlen nicht als Test."""
    return {
        k.name for k in ast.parse(text).body
        if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef))
        and k.name.startswith("test_")
    }


class TestVorhandeneDateiBleibtIntakt:
    def test_datei_bleibt_syntaktisch_gueltig(self, generator, ziel):
        """Der Befund: uebrig blieb ein Syntaxfehler."""
        generator._write_with_preservation(ziel, VORLAGE)
        ast.parse(ziel.read_text(encoding="utf-8"))

    def test_moduldocstring_bleibt(self, generator, ziel):
        generator._write_with_preservation(ziel, VORLAGE)
        assert "Steuerbefehle fuer den Drucker (CON-0016)." in ziel.read_text(encoding="utf-8")

    def test_importe_bleiben(self, generator, ziel):
        generator._write_with_preservation(ziel, VORLAGE)
        text = ziel.read_text(encoding="utf-8")
        assert "import json" in text
        assert "import httpx" in text

    def test_fixture_und_hilfsklasse_bleiben(self, generator, ziel):
        generator._write_with_preservation(ziel, VORLAGE)
        text = ziel.read_text(encoding="utf-8")
        assert "def drucker():" in text
        assert "class Drucker:" in text

    def test_konstanten_bleiben(self, generator, ziel):
        generator._write_with_preservation(ziel, VORLAGE)
        text = ziel.read_text(encoding="utf-8")
        assert 'BASIS = "http://localhost:8000"' in text
        assert 'AKTIONEN = ["start", "stop", "pause"]' in text

    def test_dekorator_bleibt_an_seiner_funktion(self, generator, ziel):
        """`@pytest.mark.parametrize` stand vor `def` und ging verloren —
        die Funktion behielt ihren Parameter, verlor aber dessen Quelle."""
        generator._write_with_preservation(ziel, VORLAGE)
        baum = ast.parse(ziel.read_text(encoding="utf-8"))
        fn = next(
            k for k in baum.body
            if isinstance(k, ast.FunctionDef)
            and k.name == "test_tc13_ohne_token_kein_befehl"
        )
        assert fn.decorator_list, "parametrize-Dekorator fehlt"

    def test_mehrzeilige_signatur_behaelt_ihren_koerper(self, generator, ziel):
        generator._write_with_preservation(ziel, VORLAGE)
        baum = ast.parse(ziel.read_text(encoding="utf-8"))
        fn = next(
            k for k in baum.body
            if isinstance(k, ast.FunctionDef)
            and k.name.startswith("test_tc10_")
        )
        assert len(fn.body) >= 3, "Koerper der mehrzeiligen Signatur fehlt"

    def test_kein_test_geht_verloren(self, generator, ziel):
        vorher = _namen(AUSIMPLEMENTIERT)
        generator._write_with_preservation(ziel, VORLAGE)
        nachher = _namen(ziel.read_text(encoding="utf-8"))
        assert vorher <= nachher, f"verloren: {sorted(vorher - nachher)}"


class TestNurFehlendesWirdErgaenzt:
    def test_fehlender_rumpf_kommt_dazu(self, generator, ziel):
        outcome = generator._write_with_preservation(ziel, VORLAGE)
        assert outcome.status == "extended"
        assert outcome.stubs_added == 1
        assert "test_tc01_start" in _namen(ziel.read_text(encoding="utf-8"))

    def test_vorhandener_test_wird_nicht_verdoppelt(self, generator, ziel):
        generator._write_with_preservation(ziel, VORLAGE)
        text = ziel.read_text(encoding="utf-8")
        assert text.count("def test_tc13_ohne_token_kein_befehl") == 1

    def test_zweiter_lauf_aendert_nichts(self, generator, ziel):
        generator._write_with_preservation(ziel, VORLAGE)
        nach_erstem = ziel.read_text(encoding="utf-8")
        outcome = generator._write_with_preservation(ziel, VORLAGE)
        assert outcome.status == "unchanged"
        assert ziel.read_text(encoding="utf-8") == nach_erstem

    def test_testzahl_zaehlt_die_datei_nicht_die_vorlage(self, generator, ziel):
        """`(3 Tests)` fuer eine Datei mit 15 war das einzige Warnsignal."""
        outcome = generator._write_with_preservation(ziel, VORLAGE)
        assert outcome.test_count == len(_namen(ziel.read_text(encoding="utf-8")))
        assert outcome.test_count > len(_namen(VORLAGE)) - 1

    def test_pep8_zwei_leerzeilen_zwischen_funktionen(self, generator, ziel):
        generator._write_with_preservation(ziel, VORLAGE)
        text = ziel.read_text(encoding="utf-8")
        assert "\n\n\ndef test_tc01_start" in text
        assert "\n\n\n\ndef" not in text

    def test_pytest_import_wird_ergaenzt_wenn_er_fehlt(self, generator, tmp_path):
        """Die Ruempfe rufen pytest.skip — ohne Import ein NameError,
        den der Generator selbst eintragen wuerde."""
        ziel = tmp_path / "tests" / "test_ohne_pytest.py"
        ziel.parent.mkdir(parents=True)
        ziel.write_text(
            '"""Ohne pytest."""\nimport json\n\n\n'
            "def test_vorhanden():\n    assert json.dumps({}) == '{}'\n",
            encoding="utf-8",
        )
        generator._write_with_preservation(ziel, VORLAGE)
        text = ziel.read_text(encoding="utf-8")
        ast.parse(text)
        assert "import pytest" in text
        assert text.count("import pytest") == 1


class TestSchutzUndAusweg:
    def test_unlesbare_datei_wird_nicht_angetastet(self, generator, tmp_path):
        ziel = tmp_path / "tests" / "kaputt.py"
        ziel.parent.mkdir(parents=True)
        kaputt = "def test_a(\n    x, y\n\ndef test_b():\n    pass\n"
        ziel.write_text(kaputt, encoding="utf-8")
        outcome = generator._write_with_preservation(ziel, VORLAGE)
        assert outcome.status == "unparsable"
        assert ziel.read_text(encoding="utf-8") == kaputt

    def test_force_sichert_vor_dem_ueberschreiben(self, generator, ziel):
        outcome = generator._write_with_preservation(ziel, VORLAGE, force=True)
        assert outcome.status == "overwritten"
        assert outcome.backup is not None
        assert outcome.backup.read_text(encoding="utf-8") == AUSIMPLEMENTIERT
        assert ziel.read_text(encoding="utf-8") == VORLAGE

    def test_neue_datei_wird_ganz_geschrieben(self, generator, tmp_path):
        ziel = tmp_path / "tests" / "neu" / "test_neu.py"
        outcome = generator._write_with_preservation(ziel, VORLAGE)
        assert outcome.status == "created"
        assert ziel.read_text(encoding="utf-8") == VORLAGE
