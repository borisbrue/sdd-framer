"""TST-0211 – Pattern-Katalog-Kontext: Prompt-Aufbau und Skill-Kontextladen (Unit)
Spec: SPEC-0048 · Contract: CON-0182
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from sdd_cli.pattern import PatternSuggester, _build_pattern_prompt

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestBuildPatternPromptCatalogContext:
    def test_empty_catalog_context_omits_section(self):
        prompt = _build_pattern_prompt("content", "SPEC-0001", "spec", 3, catalog_context="")
        assert "BEREITS AKZEPTIERTE PATTERNS IM PROJEKT" not in prompt

    def test_nonempty_catalog_context_includes_section(self):
        ctx = "- Observer (SPEC-0034): Entkoppelt Sender von Empfaenger."
        prompt = _build_pattern_prompt("content", "SPEC-0001", "spec", 3, catalog_context=ctx)
        assert "BEREITS AKZEPTIERTE PATTERNS IM PROJEKT" in prompt
        assert ctx in prompt

    def test_catalog_context_appears_before_output_format(self):
        ctx = "- Observer (SPEC-0034): Entkoppelt Sender von Empfaenger."
        prompt = _build_pattern_prompt("content", "SPEC-0001", "spec", 3, catalog_context=ctx)
        assert prompt.index(ctx) < prompt.index("AUSGABE-FORMAT")

    def test_default_catalog_context_is_empty(self):
        prompt = _build_pattern_prompt("content", "SPEC-0001", "spec", 3)
        assert "BEREITS AKZEPTIERTE PATTERNS IM PROJEKT" not in prompt


class TestPatternSuggesterCatalogWiring:
    def test_suggest_calls_catalog_summary_with_exclude_spec_id(self):
        provider = MagicMock()
        provider.complete.return_value = MagicMock(
            text=json.dumps({"pattern_suggestions": []})
        )
        registry = MagicMock()
        registry.catalog_summary.return_value = ""

        suggester = PatternSuggester(provider, registry=registry)
        suggester.suggest("spec text", "SPEC-0048", artifact_type="spec")

        registry.catalog_summary.assert_called_once()
        _, kwargs = registry.catalog_summary.call_args
        assert kwargs.get("exclude_spec_id") == "SPEC-0048"

    def test_suggest_without_registry_does_not_fail(self):
        provider = MagicMock()
        provider.complete.return_value = MagicMock(
            text=json.dumps({"pattern_suggestions": []})
        )
        suggester = PatternSuggester(provider)
        result = suggester.suggest("spec text", "SPEC-0048")
        assert result.artifact_id == "SPEC-0048"


class TestSddImplementSkillCatalogStep:
    def test_skill_mentions_project_wide_pattern_summary(self):
        skill_path = REPO_ROOT / ".claude" / "commands" / "sdd-implement.md"
        content = skill_path.read_text(encoding="utf-8")
        assert "Etablierte Patterns im Projekt" in content

    def test_skill_references_global_catalog_file(self):
        skill_path = REPO_ROOT / ".claude" / "commands" / "sdd-implement.md"
        content = skill_path.read_text(encoding="utf-8")
        assert "_catalog.json" in content
