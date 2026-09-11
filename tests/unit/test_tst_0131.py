# TST-0131 | SPEC-0029 | CON-0112
# /sdd-review – Alle drei Review-Schritte dokumentiert

from pathlib import Path

SKILL_PATH = Path(__file__).resolve().parents[2] / ".claude" / "commands" / "sdd-review.md"


def _skill_text() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


# SPEC-0044 hat die drei Befehle umbenannt bzw. entfernt. Die Skill-Datei ist
# laengst nachgezogen; der Test pruefte weiter auf die alten Namen. TC-01 und
# TC-02 bestanden dabei nur, weil ein erklaerender Satz ("existieren seit
# SPEC-0044 nicht mehr") die alten Namen enthaelt — gruen aus dem falschen
# Grund (#102).
#
#   sdd solid-check     -> sdd review spec / sdd review contract (Schritt 2)
#   sdd pattern-suggest -> Teil derselben Ausgabe
#   sdd regression-check -> sdd spec regression (Schritt 4)

_SOLID_UND_PATTERN = "sdd review spec"
# Seit #90 ueber die CLI; vorher ein `python3 -c`-Einzeiler auf PatternRegistry.
_PATTERN_PERSISTENZ = "sdd review pattern accept"
_REGRESSION = "sdd spec regression"


class TestTST0131:
    def test_tc01_solid_analyse_present(self) -> None:
        assert _SOLID_UND_PATTERN in _skill_text()

    def test_tc02_pattern_vorschlaege_present(self) -> None:
        """Die Vorschlaege entstehen in derselben Ausgabe wie die SOLID-Analyse."""
        text = _skill_text()
        assert "Pattern-Vorschläge" in text

    def test_tc03_regression_check_present(self) -> None:
        assert _REGRESSION in _skill_text()

    def test_tc04_order_solid_pattern_regression(self) -> None:
        # Seit #134 steht vor Schritt 1 eine Tabelle der Gate-Kette, die alle
        # Befehle nennt. Die Reihenfolge der Schritte beginnt bei "## Schritt 1".
        text = _skill_text()
        text = text[text.find("## Schritt 1"):]
        pos_solid = text.find(_SOLID_UND_PATTERN)
        pos_pattern = text.find(_PATTERN_PERSISTENZ)
        pos_regression = text.find(_REGRESSION)
        assert -1 not in (pos_solid, pos_pattern, pos_regression)
        assert pos_solid < pos_pattern < pos_regression

    def test_tc05_interactive_confirmation_for_patterns(self) -> None:
        text = _skill_text()
        assert "Annehmen" in text or "annehmen" in text or "ja/nein" in text

    def test_tc06_error_severity_handling(self) -> None:
        text = _skill_text()
        regression_pos = text.find(_REGRESSION)
        after_regression = text[regression_pos:]
        has_error_handling = "error" in after_regression and (
            "Nutzerentscheidung" in after_regression
            or "Weiter" in after_regression
            or "ja/nein" in after_regression
        )
        assert has_error_handling, "error-Severity-Handling + Nutzerentscheidung nicht dokumentiert"

    def test_tc07_warn_fallback_for_missing_regression_check(self) -> None:
        text = _skill_text()
        assert "[WARN]" in text, f"[WARN]-Fallback für fehlenden {_REGRESSION} nicht vorhanden"

    def test_tc08_all_three_steps_present(self) -> None:
        text = _skill_text()
        missing = [
            marker for marker in (_SOLID_UND_PATTERN, _PATTERN_PERSISTENZ, _REGRESSION)
            if marker not in text
        ]
        assert not missing, f"Pflichtschritte fehlen: {missing}"

    def test_tc09_keine_entfernten_befehle_als_anweisung(self) -> None:
        """Der Grund fuer TC-01/TC-02, die aus dem falschen Grund gruen waren:
        in einem ```bash-Block darf kein entfernter Befehl mehr stehen."""
        entfernt = ("sdd solid-check", "sdd pattern-suggest", "sdd regression-check",
                    "PatternRegistry(")
        in_bash = False
        treffer: list[str] = []
        for nr, zeile in enumerate(_skill_text().splitlines(), start=1):
            if zeile.startswith("```bash"):
                in_bash = True
                continue
            if zeile.startswith("```"):
                in_bash = False
                continue
            if in_bash:
                treffer += [f"Zeile {nr}: {c}" for c in entfernt if c in zeile]
        assert not treffer, "entfernte Befehle als Anweisung: " + ", ".join(treffer)
