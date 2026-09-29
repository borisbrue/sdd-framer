"""`sdd test generate` versteht Gherkin-Sprachen und schreibt nicht in fertige Dateien (#135).

Der Generator kannte nur `Scenario:`. Ein Feature mit `# language: de` und zehn
`Szenario:` galt als leer, und an die handgeschriebene pytest-bdd-Datei kam ein
Skip-Platzhalter, während die Phase `tests-generated` als bestanden galt.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from sdd_cli.test_generator import TestGenerator, _extract_scenarios

DEUTSCH = textwrap.dedent("""\
    # language: de
    Funktionalität: Account-Sperre

      Szenario: Dritter Fehlversuch sperrt den Account
        Angenommen ein Nutzer mit zwei Fehlversuchen
        Wenn er sich erneut falsch anmeldet
        Dann ist der Account gesperrt

      Szenariogrundriss: Sperrdauer nach <versuche> Versuchen
        Dann bleibt der Account <minuten> Minuten gesperrt

        Beispiele:
          | versuche | minuten |
          | 3        | 15      |

      Beispiel: Entsperren durch Admin
        Dann ist der Account wieder frei
""")


class TestSchluesselwoerter:
    def test_deutsch_ueber_language_zeile(self):
        assert _extract_scenarios(DEUTSCH) == [
            "Dritter Fehlversuch sperrt den Account",
            "Sperrdauer nach <versuche> Versuchen",
            "Entsperren durch Admin",
        ]

    def test_beispiele_tabelle_ist_kein_szenario(self):
        """`Beispiele:` (Examples) darf nicht als `Beispiel:` gelten."""
        assert "" not in _extract_scenarios(DEUTSCH)
        assert len(_extract_scenarios(DEUTSCH)) == 3

    def test_ohne_language_zeile_gilt_englisch(self):
        text = "Feature: X\n  Scenario: A\n  Scenario Outline: B\n  Szenario: C\n"
        assert _extract_scenarios(text) == ["A", "B"]

    @pytest.mark.parametrize("sprache, zeile, titel", [
        ("fr", "Scénario: Verrouillage", "Verrouillage"),
        ("es", "Esquema del escenario: Bloqueo", "Bloqueo"),
        ("pt", "Cenário: Bloqueio", "Bloqueio"),
        ("ru", "Сценарий: Блокировка", "Блокировка"),
    ])
    def test_weitere_sprachen(self, sprache, zeile, titel):
        assert _extract_scenarios(f"# language: {sprache}\nFeature: X\n  {zeile}\n") == [titel]

    def test_unbekannte_sprache_faellt_auf_englisch_zurueck(self):
        text = "# language: xx\nFeature: X\n  Scenario: A\n  Szenario: B\n"
        assert _extract_scenarios(text) == ["A"]


# ── generate(): Ende-zu-Ende in einem Projekt unter tmp_path ─────────────────

def _projekt(root: Path, feature: str | None = DEUTSCH, artifact: bool = True) -> None:
    (root / ".sdd" / "contracts" / "behavior").mkdir(parents=True)
    zeile = 'artifact: "contracts/behavior/account-lockout.feature"\n' if artifact else ""
    (root / ".sdd" / "contracts" / "behavior" / "CON-0149-account-lockout.md").write_text(
        "---\nid: CON-0149\ntitle: Account-Sperre\ntype: behavior\nformat: gherkin\n"
        f"spec: SPEC-0073\nversion: 0.1.0\nstatus: approved\n{zeile}---\n\n# Nur Prosa\n",
        encoding="utf-8")
    if feature is not None:
        p = root / "contracts" / "behavior" / "account-lockout.feature"
        p.parent.mkdir(parents=True)
        p.write_text(feature, encoding="utf-8")


PYTEST_BDD = textwrap.dedent('''\
    """Handgeschrieben: bindet das ganze Feature (CON-0149)."""
    from pytest_bdd import given, scenarios, then, when

    scenarios("../../contracts/behavior/account-lockout.feature")


    @given("ein Nutzer mit zwei Fehlversuchen")
    def nutzer():
        return {"versuche": 2}
''')


def _lauf(root: Path):
    result = TestGenerator(root).generate("SPEC-0073", ["CON-0149"])
    (eintrag,) = result.generated_files
    return result, eintrag, root / eintrag["path"]


class TestGenerate:
    def test_deutsches_feature_ergibt_einen_rumpf_je_szenario(self, tmp_path):
        _projekt(tmp_path)
        result, eintrag, pfad = _lauf(tmp_path)
        assert eintrag["status"] == "created" and eintrag["test_count"] == 3
        assert "def test_tc01_dritter_fehlversuch_sperrt_den_account" in pfad.read_text()
        assert "kein Szenario gefunden" not in pfad.read_text()
        assert result.warnings == []

    def test_pytest_bdd_datei_bleibt_unangetastet(self, tmp_path):
        """Der Fall aus dem Issue: fertige Datei, zehn Szenarien, +1 Rumpf."""
        _projekt(tmp_path)
        pfad = TestGenerator(tmp_path)._output_path("CON-0149", {"format": "gherkin"})
        pfad.parent.mkdir(parents=True)
        pfad.write_text(PYTEST_BDD, encoding="utf-8")

        result, eintrag, _ = _lauf(tmp_path)
        assert eintrag["status"] == "unchanged"
        assert "scenarios()" in eintrag["note"]
        assert pfad.read_text(encoding="utf-8") == PYTEST_BDD
        assert result.success

    def test_ohne_szenario_bleibt_bestehende_datei_unangetastet(self, tmp_path):
        _projekt(tmp_path, feature="# language: de\nFunktionalität: nur Prosa\n")
        pfad = TestGenerator(tmp_path)._output_path("CON-0149", {"format": "gherkin"})
        pfad.parent.mkdir(parents=True)
        eigen = "def test_eigen():\n    assert True\n"
        pfad.write_text(eigen, encoding="utf-8")

        result, eintrag, _ = _lauf(tmp_path)
        assert eintrag["status"] == "unchanged"
        assert pfad.read_text(encoding="utf-8") == eigen
        assert result.success
        assert any("kein Szenario gefunden" in w and "unangetastet" in w for w in result.warnings)

    def test_ohne_szenario_und_ohne_datei_entsteht_platzhalter_mit_warnung(self, tmp_path):
        _projekt(tmp_path, feature=None, artifact=False)
        result, eintrag, pfad = _lauf(tmp_path)
        assert eintrag["status"] == "created"
        assert "pytest.skip" in pfad.read_text(encoding="utf-8")
        assert any("nur einen Platzhalter" in w for w in result.warnings)

    def test_unbekannte_sprache_wird_gemeldet(self, tmp_path):
        _projekt(tmp_path, feature="# language: xx\nFeature: X\n  Szenario: A\n")
        result, _, _ = _lauf(tmp_path)
        assert any("`# language: xx` ist dem Generator unbekannt" in w for w in result.warnings)
