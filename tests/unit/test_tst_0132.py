# TST-0132 | SPEC-0029 | CON-0113
# /sdd-implement – Vollständiger Auto-Flow im Skill dokumentiert

from pathlib import Path

SKILL_PATH = Path(__file__).resolve().parents[2] / ".claude" / "commands" / "sdd-implement.md"


def _skill_text() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


class TestTST0132:
    def test_tc01_sdd_start_auto_call_documented(self) -> None:
        text = _skill_text()
        assert "sdd start" in text
        auto_context = "automatisch" in text or "approved" in text
        assert auto_context, "Automatischer sdd start-Aufruf bei approved-Status nicht dokumentiert"

    def test_tc02_feature_branch_creation_documented(self) -> None:
        text = _skill_text()
        assert "feat/" in text, "Feature-Branch mit 'feat/'-Prefix nicht dokumentiert"

    def test_tc03_decompose_as_plan_not_distribute(self) -> None:
        text = _skill_text()
        assert "sdd decompose" in text, "sdd decompose nicht dokumentiert"
        decompose_pos = text.find("sdd decompose")
        text[:decompose_pos]
        after_decompose = text[decompose_pos:]
        assert "sdd distribute" not in after_decompose or (
            "kein" in after_decompose[:after_decompose.find("sdd distribute") + 20]
        ), "sdd distribute erscheint als Aktion von /sdd-implement"

    def test_tc04_sdd_finalize_documented(self) -> None:
        assert "sdd finalize" in _skill_text()

    def test_tc05_container_error_documented(self) -> None:
        text = _skill_text()
        has_container_error = (
            "Dev-Container nicht gefunden" in text
            or ("Container" in text and "Fehler" in text)
            or ("Container" in text and "nicht gefunden" in text)
        )
        assert has_container_error, "Container-Fehler-Handling nicht dokumentiert"

    def test_tc06_skip_container_on_third_attempt(self) -> None:
        text = _skill_text()
        assert "--skip-container" in text, "--skip-container nicht dokumentiert"
        has_third = "3" in text or "dritten" in text or "Dritter" in text
        assert has_third, "Dritter Versuch / 3. Attempt nicht dokumentiert"

    def test_tc07_warning_at_skip_container(self) -> None:
        text = _skill_text()
        skip_pos = text.find("--skip-container")
        after_skip = text[skip_pos:]
        has_warning = "⚠" in after_skip or "warning" in after_skip.lower() or "übersprungen" in after_skip
        assert has_warning, "Warnung bei --skip-container-Flow nicht dokumentiert"

    def test_tc08_holdout_isolation_documented(self) -> None:
        text = _skill_text()
        has_holdout_ban = ".sdd/holdout/" in text or "NIEMALS" in text
        assert has_holdout_ban, "Holdout-Isolation-Klausel nicht dokumentiert"

    def test_tc09_distribute_not_called_by_implement(self) -> None:
        text = _skill_text()
        if "sdd distribute" not in text:
            return
        distribute_pos = text.find("sdd distribute")
        context = text[max(0, distribute_pos - 50):distribute_pos + 50]
        assert "kein" in context or "vorbehalten" in context or "nicht" in context, (
            "sdd distribute erscheint als Aktion von /sdd-implement ohne Ausschluss-Kontext"
        )

    def test_tc10_empty_decompose_list_error(self) -> None:
        text = _skill_text()
        has_empty_error = (
            "0 Tasks" in text
            or "leer" in text
            or "Keine Tasks" in text
        )
        assert has_empty_error, "Fehlerfall bei leerer Decompose-Liste nicht dokumentiert"
