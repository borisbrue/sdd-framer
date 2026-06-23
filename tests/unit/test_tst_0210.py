"""TST-0210 – PatternRegistry.catalog_summary() Ausgabeformat (Unit)
Spec: SPEC-0048 · Contract: CON-0183
"""
from __future__ import annotations

import json
from pathlib import Path

from sdd_cli.pattern import PatternRegistry


class TestCatalogSummary:
    def test_empty_catalog_returns_empty_string(self, tmp_path):
        registry = PatternRegistry(tmp_path)
        assert registry.catalog_summary() == ""

    def test_single_entry_format(self, tmp_path):
        registry = PatternRegistry(tmp_path)
        registry.accept("SPEC-0034", "Observer", "Entkoppelt Sender von Empfaenger.")
        summary = registry.catalog_summary()
        assert summary == "- Observer (SPEC-0034): Entkoppelt Sender von Empfaenger."

    def test_reason_truncated_at_120_chars(self, tmp_path):
        registry = PatternRegistry(tmp_path)
        long_reason = "X" * 200
        registry.accept("SPEC-0034", "Observer", long_reason)
        summary = registry.catalog_summary()
        line = summary.splitlines()[0]
        reason_part = line.split(": ", 1)[1]
        assert reason_part.endswith("…")
        assert len(reason_part) - 1 == 120

    def test_short_reason_not_truncated(self, tmp_path):
        registry = PatternRegistry(tmp_path)
        registry.accept("SPEC-0034", "Observer", "Kurz.")
        summary = registry.catalog_summary()
        assert "…" not in summary

    def test_max_entries_limits_and_orders_newest_first(self, tmp_path):
        registry = PatternRegistry(tmp_path)
        for i in range(15):
            registry.accept(f"SPEC-{i:04d}", f"Pattern{i}", f"Grund {i}")
        summary = registry.catalog_summary(max_entries=10)
        lines = summary.splitlines()
        assert len(lines) == 10
        assert "Pattern14" in lines[0]
        assert "Pattern5" in lines[9]

    def test_exclude_spec_id_filters_own_entries(self, tmp_path):
        registry = PatternRegistry(tmp_path)
        registry.accept("SPEC-0048", "Strategy", "Eigene Entscheidung.")
        registry.accept("SPEC-0034", "Observer", "Fremde Entscheidung.")
        summary = registry.catalog_summary(exclude_spec_id="SPEC-0048")
        assert "Strategy" not in summary
        assert "Observer" in summary

    def test_exclude_spec_id_does_not_count_against_limit(self, tmp_path):
        registry = PatternRegistry(tmp_path)
        registry.accept("SPEC-0048", "Strategy", "Eigene.")
        for i in range(10):
            registry.accept(f"SPEC-{i:04d}", f"Pattern{i}", f"Grund {i}")
        summary = registry.catalog_summary(max_entries=10, exclude_spec_id="SPEC-0048")
        lines = summary.splitlines()
        assert len(lines) == 10
        assert "Strategy" not in summary

    def test_only_own_spec_in_catalog_returns_empty(self, tmp_path):
        registry = PatternRegistry(tmp_path)
        registry.accept("SPEC-0048", "Strategy", "Eigene.")
        summary = registry.catalog_summary(exclude_spec_id="SPEC-0048")
        assert summary == ""

    def test_corrupt_catalog_returns_empty_string(self, tmp_path):
        patterns_dir = tmp_path / ".sdd" / "patterns"
        patterns_dir.mkdir(parents=True)
        (patterns_dir / "_catalog.json").write_text("NOT JSON", encoding="utf-8")
        registry = PatternRegistry(tmp_path)
        assert registry.catalog_summary() == ""

    def test_missing_catalog_file_returns_empty_string(self, tmp_path):
        registry = PatternRegistry(tmp_path)
        assert not (tmp_path / ".sdd" / "patterns" / "_catalog.json").exists()
        assert registry.catalog_summary() == ""
