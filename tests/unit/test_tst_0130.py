# TST-0130 | SPEC-0029 | CON-0111
# /sdd-new spec – kein sdd validate nach dem Speichern

from pathlib import Path

SKILL_PATH = Path(__file__).resolve().parents[2] / ".claude" / "commands" / "sdd-new.md"


def _skill_text() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def _spec_section(text: str) -> str:
    start = text.find("## Schritt 2a")
    end = text.find("\n## ", start + 1)
    return text[start:] if end == -1 else text[start:end]


class TestTST0130:
    def test_tc01_no_sdd_validate_in_spec_section(self) -> None:
        section = _spec_section(_skill_text())
        assert "sdd validate" not in section

    def test_tc02_review_hint_after_save_step(self) -> None:
        text = _skill_text()
        save_pos = text.find("# Datei schreiben")
        review_pos = text.find("/sdd-review")
        assert save_pos != -1, "Speicher-Schritt nicht gefunden"
        assert review_pos != -1, "/sdd-review-Hinweis nicht gefunden"
        assert review_pos > save_pos

    def test_tc03_error_case_for_unknown_spec_id(self) -> None:
        section = _spec_section(_skill_text())
        has_error_case = (
            "nicht ermittelbar" in section
            or "nicht ermitteln" in section
            or "Fehlermeldung" in section
        )
        assert has_error_case, "Fehlerfall für nicht ermittelbare SPEC-ID nicht dokumentiert"
