"""Unit-Tests für pattern.py – Design-Pattern-Registry und Suggester (SPEC-0015)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sdd_cli.pattern import (
    PatternSuggestion,
    PatternSuggestionResult,
    PatternSuggester,
    PatternRegistry,
    _parse_pattern_response,
    _extract_json,
    _build_pattern_prompt,
    _find_pattern,
    REFACTORING_GURU_BASE,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _valid_item(**overrides) -> dict:
    base = {
        "pattern_name": "Strategy",
        "category": "Behavioral",
        "refactoring_guru_url": "https://refactoring.guru/design-patterns/strategy",
        "applies_to": "Handler-Auswahl",
        "rationale": "Ermöglicht austauschbare Algorithmen ohne if-else-Kaskaden.",
        "alternative": "Factory Method wurde abgelehnt, da kein Objekt erstellt wird.",
        "effort": "medium",
        "priority": "recommended",
    }
    base.update(overrides)
    return base


# ─── PatternSuggestion ────────────────────────────────────────────────────────

class TestPatternSuggestion:
    def test_to_dict_has_all_fields(self):
        s = PatternSuggestion(
            pattern_name="Observer",
            category="Behavioral",
            refactoring_guru_url="https://refactoring.guru/design-patterns/observer",
            applies_to="Event-System",
            rationale="Entkoppelt Sender von Empfänger.",
            alternative="Polling wäre einfacher aber ineffizient.",
            effort="low",
            priority="recommended",
        )
        d = s.to_dict()
        assert d["pattern_name"] == "Observer"
        assert d["effort"] == "low"
        assert "refactoring_guru_url" in d


# ─── PatternSuggestionResult ──────────────────────────────────────────────────

class TestPatternSuggestionResult:
    def test_to_dict_structure(self):
        r = PatternSuggestionResult(
            artifact_id="SPEC-0001",
            artifact_type="spec",
            generated_at="2026-01-01T00:00:00Z",
            pattern_suggestions=[],
        )
        d = r.to_dict()
        assert d["artifact_id"] == "SPEC-0001"
        assert d["pattern_suggestions"] == []


# ─── PatternSuggester ─────────────────────────────────────────────────────────

class TestPatternSuggester:
    def _make_provider(self, items: list[dict]) -> MagicMock:
        payload = json.dumps({"pattern_suggestions": items})
        provider = MagicMock()
        provider.complete.return_value = MagicMock(text=payload)
        return provider

    def test_suggests_up_to_max(self):
        items = [_valid_item(pattern_name=f"P{i}") for i in range(4)]
        provider = self._make_provider(items)
        suggester = PatternSuggester(provider, max_suggestions=2)
        result = suggester.suggest("spec text", "SPEC-0001")
        assert len(result.pattern_suggestions) == 2

    def test_max_clamped_to_1_4(self):
        suggester_low = PatternSuggester(MagicMock(), max_suggestions=0)
        assert suggester_low._max == 1
        suggester_high = PatternSuggester(MagicMock(), max_suggestions=99)
        assert suggester_high._max == 4

    def test_provider_exception_returns_empty(self):
        provider = MagicMock()
        provider.complete.side_effect = RuntimeError("network down")
        suggester = PatternSuggester(provider)
        result = suggester.suggest("text", "SPEC-0001")
        assert result.pattern_suggestions == []
        assert result.artifact_id == "SPEC-0001"

    def test_result_has_generated_at(self):
        provider = self._make_provider([_valid_item()])
        suggester = PatternSuggester(provider)
        result = suggester.suggest("text", "SPEC-0001", artifact_type="contract")
        assert result.artifact_type == "contract"
        assert "T" in result.generated_at  # ISO 8601


# ─── PatternRegistry ──────────────────────────────────────────────────────────

class TestPatternRegistry:
    def test_load_missing_spec_returns_empty(self, tmp_path):
        registry = PatternRegistry(tmp_path)
        data = registry.load("SPEC-0001")
        assert data["spec_id"] == "SPEC-0001"
        assert data["patterns"] == []

    def test_accept_creates_file(self, tmp_path):
        registry = PatternRegistry(tmp_path)
        registry.accept("SPEC-0001", "Strategy", "Passt gut wegen Austauschbarkeit.")
        path = tmp_path / ".sdd" / "patterns" / "SPEC-0001-patterns.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert len(data["patterns"]) == 1
        assert data["patterns"][0]["status"] == "accepted"

    def test_reject_creates_file_with_rejected_status(self, tmp_path):
        registry = PatternRegistry(tmp_path)
        registry.reject("SPEC-0001", "Singleton", "Zu eng gekoppelt für dieses Modul.")
        data = registry.load("SPEC-0001")
        assert data["patterns"][0]["status"] == "rejected"
        assert data["patterns"][0]["rejection_reason"] == "Zu eng gekoppelt für dieses Modul."

    def test_accept_idempotent_updates_existing_entry(self, tmp_path):
        registry = PatternRegistry(tmp_path)
        registry.accept("SPEC-0001", "Strategy", "Grund A")
        registry.accept("SPEC-0001", "Strategy", "Grund B")
        data = registry.load("SPEC-0001")
        assert len(data["patterns"]) == 1
        assert data["patterns"][0]["acceptance_reason"] == "Grund B"

    def test_accept_clears_rejection_reason(self, tmp_path):
        registry = PatternRegistry(tmp_path)
        registry.reject("SPEC-0001", "Observer", "Zu komplex")
        registry.accept("SPEC-0001", "Observer", "Jetzt doch sinnvoll.")
        data = registry.load("SPEC-0001")
        entry = data["patterns"][0]
        assert entry["status"] == "accepted"
        assert entry["rejection_reason"] is None

    def test_reject_clears_acceptance_reason(self, tmp_path):
        registry = PatternRegistry(tmp_path)
        registry.accept("SPEC-0001", "Factory", "Gut")
        registry.reject("SPEC-0001", "Factory", "Doch nicht passend.")
        data = registry.load("SPEC-0001")
        entry = data["patterns"][0]
        assert entry["status"] == "rejected"
        assert entry["acceptance_reason"] is None

    def test_list_patterns_by_spec(self, tmp_path):
        registry = PatternRegistry(tmp_path)
        registry.accept("SPEC-0001", "Strategy", "Gut")
        registry.accept("SPEC-0001", "Observer", "Auch gut")
        patterns = registry.list_patterns("SPEC-0001")
        assert len(patterns) == 2
        assert all(p["spec_id"] == "SPEC-0001" for p in patterns)

    def test_list_patterns_all(self, tmp_path):
        registry = PatternRegistry(tmp_path)
        registry.accept("SPEC-0001", "Strategy", "Gut")
        registry.accept("SPEC-0002", "Observer", "Auch gut")
        patterns = registry.list_patterns()
        assert len(patterns) == 2

    def test_list_patterns_empty_dir(self, tmp_path):
        registry = PatternRegistry(tmp_path)
        assert registry.list_patterns() == []

    def test_accept_updates_catalog(self, tmp_path):
        registry = PatternRegistry(tmp_path)
        registry.accept("SPEC-0001", "Strategy", "Gut",
                        url="https://refactoring.guru/design-patterns/strategy")
        catalog_path = tmp_path / ".sdd" / "patterns" / "_catalog.json"
        catalog = json.loads(catalog_path.read_text())
        assert len(catalog["accepted_patterns"]) == 1
        assert catalog["accepted_patterns"][0]["pattern_name"] == "Strategy"

    def test_reject_removes_from_catalog(self, tmp_path):
        registry = PatternRegistry(tmp_path)
        registry.accept("SPEC-0001", "Strategy", "Gut")
        registry.reject("SPEC-0001", "Strategy", "Doch nicht.")
        catalog_path = tmp_path / ".sdd" / "patterns" / "_catalog.json"
        catalog = json.loads(catalog_path.read_text())
        assert catalog["accepted_patterns"] == []

    def test_load_corrupt_file_returns_empty(self, tmp_path):
        registry = PatternRegistry(tmp_path)
        patterns_dir = tmp_path / ".sdd" / "patterns"
        patterns_dir.mkdir(parents=True)
        corrupt = patterns_dir / "SPEC-0001-patterns.json"
        corrupt.write_text("NOT JSON", encoding="utf-8")
        data = registry.load("SPEC-0001")
        assert data["patterns"] == []


# ─── _parse_pattern_response ──────────────────────────────────────────────────

class TestParsePatternResponse:
    def test_valid_response_returns_suggestions(self):
        payload = json.dumps({"pattern_suggestions": [_valid_item()]})
        suggestions = _parse_pattern_response(payload, "SPEC-0001")
        assert len(suggestions) == 1
        assert suggestions[0].pattern_name == "Strategy"

    def test_invalid_json_returns_empty(self):
        assert _parse_pattern_response("NOT JSON", "SPEC-0001") == []

    def test_duplicate_names_deduplicated(self):
        payload = json.dumps({
            "pattern_suggestions": [_valid_item(), _valid_item()]
        })
        suggestions = _parse_pattern_response(payload, "SPEC-0001")
        assert len(suggestions) == 1

    def test_invalid_category_defaults_to_behavioral(self):
        item = _valid_item(category="Unknown")
        payload = json.dumps({"pattern_suggestions": [item]})
        suggestions = _parse_pattern_response(payload, "SPEC-0001")
        assert suggestions[0].category == "Behavioral"

    def test_invalid_effort_defaults_to_medium(self):
        item = _valid_item(effort="extreme")
        payload = json.dumps({"pattern_suggestions": [item]})
        suggestions = _parse_pattern_response(payload, "SPEC-0001")
        assert suggestions[0].effort == "medium"

    def test_invalid_priority_defaults_to_optional(self):
        item = _valid_item(priority="urgent")
        payload = json.dumps({"pattern_suggestions": [item]})
        suggestions = _parse_pattern_response(payload, "SPEC-0001")
        assert suggestions[0].priority == "optional"

    def test_short_rationale_skipped(self):
        item = _valid_item(rationale="short")
        payload = json.dumps({"pattern_suggestions": [item]})
        suggestions = _parse_pattern_response(payload, "SPEC-0001")
        assert suggestions == []

    def test_short_alternative_skipped(self):
        item = _valid_item(alternative="x")
        payload = json.dumps({"pattern_suggestions": [item]})
        suggestions = _parse_pattern_response(payload, "SPEC-0001")
        assert suggestions == []

    def test_invalid_guru_url_replaced_with_slug(self):
        item = _valid_item(pattern_name="Decorator", refactoring_guru_url="http://other.com/x")
        payload = json.dumps({"pattern_suggestions": [item]})
        suggestions = _parse_pattern_response(payload, "SPEC-0001")
        assert suggestions[0].refactoring_guru_url.startswith(REFACTORING_GURU_BASE)
        assert "decorator" in suggestions[0].refactoring_guru_url

    def test_max_four_items_returned(self):
        items = [_valid_item(pattern_name=f"P{i}") for i in range(6)]
        payload = json.dumps({"pattern_suggestions": items})
        suggestions = _parse_pattern_response(payload, "SPEC-0001")
        assert len(suggestions) <= 4

    def test_markdown_json_block_extracted(self):
        payload = '```json\n' + json.dumps({"pattern_suggestions": [_valid_item()]}) + '\n```'
        suggestions = _parse_pattern_response(payload, "SPEC-0001")
        assert len(suggestions) == 1


# ─── _extract_json ────────────────────────────────────────────────────────────

class TestExtractJson:
    def test_markdown_block(self):
        text = '```json\n{"key": 1}\n```'
        assert _extract_json(text) == '{"key": 1}'

    def test_bare_object(self):
        text = 'prefix {"key": 1} suffix'
        assert _extract_json(text) == '{"key": 1}'

    def test_plain_text(self):
        assert _extract_json("  hello  ") == "hello"


# ─── _build_pattern_prompt ────────────────────────────────────────────────────

class TestBuildPatternPrompt:
    def test_contains_artifact_id_and_type(self):
        prompt = _build_pattern_prompt("content", "SPEC-0001", "spec", 3)
        assert "SPEC-0001" in prompt
        assert "spec" in prompt

    def test_contains_refactoring_guru_reference(self):
        prompt = _build_pattern_prompt("content", "SPEC-0001", "spec", 3)
        assert "refactoring.guru" in prompt

    def test_max_suggestions_in_prompt(self):
        prompt = _build_pattern_prompt("content", "SPEC-0001", "spec", 3)
        assert "3" in prompt


# ─── _find_pattern ────────────────────────────────────────────────────────────

class TestFindPattern:
    def test_found(self):
        patterns = [{"pattern_name": "Strategy"}, {"pattern_name": "Observer"}]
        result = _find_pattern(patterns, "Observer")
        assert result is not None
        assert result["pattern_name"] == "Observer"

    def test_not_found_returns_none(self):
        patterns = [{"pattern_name": "Strategy"}]
        assert _find_pattern(patterns, "Factory") is None

    def test_empty_list_returns_none(self):
        assert _find_pattern([], "Strategy") is None
