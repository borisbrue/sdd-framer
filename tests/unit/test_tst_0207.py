"""TST-0207 – VisionStats Value Object Schema (Unit)
Spec: SPEC-0047 · Contract: CON-0181
"""
import pytest


FULL_VISION = """\
# Projekt – Produktvision

## Vision

Ein tolles Produkt.

## Zielgruppe

Entwickler

## Tech Stack

Python

## Competitive Landscape

Niemand

## Kernprobleme

Chaos

## Features

1. **Offline-Modus** – App offline nutzbar
   > LLM Challenge: Aufwand: high
   > Code Challenge: src/sync.py

2. **Dark Mode**
   > LLM Challenge: Aufwand: low

3. **Export**

## Tasks

- [ ] README aktualisieren
- [x] CI einrichten
- [ ] Docs schreiben
"""

SKELETON = """\
# Projekt – Produktvision

## Vision

## Zielgruppe

## Tech Stack

## Competitive Landscape

## Kernprobleme

## Features

## Tasks
"""


class TestVisionStatsSchema:
    def test_from_document_computes_all_fields(self, tmp_path):
        """Schema: alle 6 Felder korrekt berechnet aus FULL_VISION."""
        from tool.sdd_cli.vision.document import VisionDocument
        from tool.sdd_cli.vision.stats import VisionStats

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(FULL_VISION)
        doc = VisionDocument.from_file(vision_file)
        stats = VisionStats.from_document(doc)

        assert stats.feature_count == 3
        assert stats.task_total == 3
        assert stats.task_done == 1
        assert stats.task_open == 2
        assert stats.llm_challenge_count == 2
        assert stats.code_challenge_count == 1

    def test_from_document_skeleton_all_zeros(self, tmp_path):
        """INV-02: Skelett-Dokument → alle Felder 0."""
        from tool.sdd_cli.vision.document import VisionDocument
        from tool.sdd_cli.vision.stats import VisionStats

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(SKELETON)
        doc = VisionDocument.from_file(vision_file)
        stats = VisionStats.from_document(doc)

        assert stats.feature_count == 0
        assert stats.task_total == 0
        assert stats.task_done == 0
        assert stats.task_open == 0
        assert stats.llm_challenge_count == 0
        assert stats.code_challenge_count == 0

    def test_inv01_task_total_equals_done_plus_open(self, tmp_path):
        """INV-01: task_done + task_open == task_total."""
        from tool.sdd_cli.vision.document import VisionDocument
        from tool.sdd_cli.vision.stats import VisionStats

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(FULL_VISION)
        doc = VisionDocument.from_file(vision_file)
        stats = VisionStats.from_document(doc)

        assert stats.task_done + stats.task_open == stats.task_total

    def test_inv02_all_fields_non_negative(self, tmp_path):
        """INV-02: alle Felder >= 0."""
        from tool.sdd_cli.vision.document import VisionDocument
        from tool.sdd_cli.vision.stats import VisionStats

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(FULL_VISION)
        doc = VisionDocument.from_file(vision_file)
        stats = VisionStats.from_document(doc)

        assert stats.feature_count >= 0
        assert stats.task_total >= 0
        assert stats.task_done >= 0
        assert stats.task_open >= 0
        assert stats.llm_challenge_count >= 0
        assert stats.code_challenge_count >= 0

    def test_inv03_challenges_not_exceed_feature_count(self, tmp_path):
        """INV-03: challenge_count <= feature_count."""
        from tool.sdd_cli.vision.document import VisionDocument
        from tool.sdd_cli.vision.stats import VisionStats

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(FULL_VISION)
        doc = VisionDocument.from_file(vision_file)
        stats = VisionStats.from_document(doc)

        assert stats.llm_challenge_count <= stats.feature_count
        assert stats.code_challenge_count <= stats.feature_count

    def test_inv04_frozen_raises_on_mutation(self, tmp_path):
        """INV-04: frozen dataclass — Setzen eines Felds löst Exception aus."""
        from tool.sdd_cli.vision.document import VisionDocument
        from tool.sdd_cli.vision.stats import VisionStats

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(SKELETON)
        doc = VisionDocument.from_file(vision_file)
        stats = VisionStats.from_document(doc)

        with pytest.raises((AttributeError, TypeError)):
            stats.feature_count = 99

    def test_all_field_types_are_int(self, tmp_path):
        """Schema: alle Felder haben Typ int."""
        from tool.sdd_cli.vision.document import VisionDocument
        from tool.sdd_cli.vision.stats import VisionStats

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(FULL_VISION)
        doc = VisionDocument.from_file(vision_file)
        stats = VisionStats.from_document(doc)

        for field_name in (
            "feature_count", "task_total", "task_done", "task_open",
            "llm_challenge_count", "code_challenge_count"
        ):
            assert isinstance(getattr(stats, field_name), int), f"{field_name} is not int"
