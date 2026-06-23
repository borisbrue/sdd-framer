# TST-0213 – Sichtbare LLM-Fehler in pattern/solid statt stiller Degradierung
# Spec: SPEC-0050 · Contract: CON-0187
from sdd_cli.pattern import PatternSuggester
from sdd_cli.solid import SolidAnalyzer, BatchLlmSolidChecker


class _RaisingProvider:
    def complete(self, *args, **kwargs):
        raise RuntimeError("claude CLI nicht gefunden")


class _OkProvider:
    def __init__(self, text: str) -> None:
        self._text = text

    def complete(self, *args, **kwargs):
        class _Result:
            pass
        r = _Result()
        r.text = self._text
        r.usage = None
        return r


class TestTST0213:
    def test_pattern_suggest_surfaces_llm_error(self) -> None:
        # FR-03 / INV-01: LLM-Fehler wird sichtbar (llm_error gesetzt), nicht still []
        result = PatternSuggester(_RaisingProvider()).suggest("text", "SPEC-9999", "spec")
        assert result.llm_error is not None
        assert "claude CLI" in result.llm_error
        assert result.pattern_suggestions == []

    def test_pattern_genuine_empty_has_no_error(self) -> None:
        # Echte 0 Vorschläge sind von einem LLM-Fehler unterscheidbar
        result = PatternSuggester(_OkProvider('{"pattern_suggestions": []}')).suggest(
            "text", "SPEC-9999", "spec"
        )
        assert result.llm_error is None

    def test_solid_check_surfaces_llm_error(self) -> None:
        # FR-04 / INV-02: LLM-Fehler im SOLID-Check ist als had_llm_error sichtbar
        report = SolidAnalyzer([BatchLlmSolidChecker(_RaisingProvider())]).analyze(
            "text", "SPEC-9999", "spec"
        )
        assert report.had_llm_error is True

    def test_solid_happy_path_no_error(self) -> None:
        # INV-03: funktionierender Provider → kein had_llm_error
        report = SolidAnalyzer([BatchLlmSolidChecker(_OkProvider("{}"))]).analyze(
            "text", "SPEC-9999", "spec"
        )
        assert report.had_llm_error is False
