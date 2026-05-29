# TST-0131 | SPEC-0029 | CON-0112
# /sdd-review – Alle drei Review-Schritte dokumentiert

from pathlib import Path

SKILL_PATH = Path(__file__).resolve().parents[2] / ".claude" / "commands" / "sdd-review.md"


def _skill_text() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


class TestTST0131:
    def test_tc01_solid_check_present(self) -> None:
        assert "sdd solid-check" in _skill_text()

    def test_tc02_pattern_suggest_present(self) -> None:
        assert "sdd pattern-suggest" in _skill_text()

    def test_tc03_regression_check_present(self) -> None:
        assert "sdd regression-check" in _skill_text()

    def test_tc04_order_solid_pattern_regression(self) -> None:
        text = _skill_text()
        pos_solid = text.find("sdd solid-check")
        pos_pattern = text.find("sdd pattern-suggest")
        pos_regression = text.find("sdd regression-check")
        assert pos_solid < pos_pattern < pos_regression

    def test_tc05_interactive_confirmation_for_patterns(self) -> None:
        text = _skill_text()
        assert "Annehmen" in text or "annehmen" in text or "ja/nein" in text

    def test_tc06_error_severity_handling(self) -> None:
        text = _skill_text()
        regression_pos = text.find("sdd regression-check")
        after_regression = text[regression_pos:]
        has_error_handling = "error" in after_regression and (
            "Nutzerentscheidung" in after_regression
            or "Weiter" in after_regression
            or "ja/nein" in after_regression
        )
        assert has_error_handling, "error-Severity-Handling + Nutzerentscheidung nicht dokumentiert"

    def test_tc07_warn_fallback_for_missing_regression_check(self) -> None:
        text = _skill_text()
        assert "[WARN]" in text, "[WARN]-Fallback für fehlenden sdd regression-check nicht vorhanden"

    def test_tc08_all_three_steps_present(self) -> None:
        text = _skill_text()
        missing = [
            cmd for cmd in ("sdd solid-check", "sdd pattern-suggest", "sdd regression-check")
            if cmd not in text
        ]
        assert not missing, f"Pflichtschritte fehlen: {missing}"
