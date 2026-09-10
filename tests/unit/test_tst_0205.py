"""TST-0205 – .sdd/vision.md Dokumentstruktur und Schema (Unit)
Spec: SPEC-0046 · Contract: CON-0179
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

Chaos ohne Struktur

## Features

1. **Offline-Modus** – App ohne Internet nutzbar
   > LLM Challenge: Aufwand: high · Sync-Komplexität
   > Code Challenge: src/sync.py

2. **Dark Mode**

## Tasks

- [ ] README aktualisieren
- [x] CI einrichten
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


class TestVisionDocumentSchema:
    def test_parse_full_document(self, tmp_path):
        """INV-02–05: Vollständiges Dokument korrekt geparst."""
        from tool.sdd_cli.vision.document import VisionDocument

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(FULL_VISION)
        doc = VisionDocument.from_file(vision_file)

        assert doc.vision_statement == "Ein tolles Produkt."
        assert len(doc.features) == 2
        assert doc.features[0].title == "Offline-Modus"
        assert doc.features[1].title == "Dark Mode"
        assert len(doc.tasks) == 2

    def test_all_required_headings_present_in_skeleton(self, tmp_path):
        """INV-02: Skelett-Dokument hat alle 7 Pflicht-Überschriften."""
        from tool.sdd_cli.vision.document import VisionDocument

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(SKELETON)
        doc = VisionDocument.from_file(vision_file)

        assert doc.validate() is True

    def test_validate_fails_when_heading_missing(self, tmp_path):
        """INV-02: Fehlende Pflicht-Überschrift → validate() False oder Exception."""
        from tool.sdd_cli.vision.document import VisionDocument

        incomplete = SKELETON.replace("## Features\n", "")
        vision_file = tmp_path / "vision.md"
        vision_file.write_text(incomplete)
        doc = VisionDocument.from_file(vision_file)

        assert doc.validate() is False

    def test_feature_parsed_with_challenge_results(self, tmp_path):
        """INV-04: Feature-Einträge mit Blockquote-Ergebnissen korrekt geparst."""
        from tool.sdd_cli.vision.document import VisionDocument

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(FULL_VISION)
        doc = VisionDocument.from_file(vision_file)

        feature = doc.features[0]
        assert feature.llm_challenge is not None
        assert "high" in feature.llm_challenge
        assert feature.code_challenge is not None
        assert "src/sync.py" in feature.code_challenge

    def test_tasks_parsed_as_checkboxes(self, tmp_path):
        """INV-05: Tasks als done/undone korrekt geparst."""
        from tool.sdd_cli.vision.document import VisionDocument

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(FULL_VISION)
        doc = VisionDocument.from_file(vision_file)

        assert doc.tasks[0].title == "README aktualisieren"
        assert doc.tasks[0].done is False
        assert doc.tasks[1].title == "CI einrichten"
        assert doc.tasks[1].done is True

    def test_no_frontmatter_in_serialized_output(self, tmp_path):
        """INV-06: Serialisiertes Dokument hat keinen YAML-Frontmatter-Block."""
        from tool.sdd_cli.vision.document import VisionDocument

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(SKELETON)
        doc = VisionDocument.from_file(vision_file)
        doc.save()

        content = vision_file.read_text()
        assert not content.startswith("---")

    def test_from_file_raises_when_missing(self, tmp_path):
        """INV-01 (via CON-0175): Exception wenn Datei nicht existiert."""
        from tool.sdd_cli.vision.document import VisionDocument, VisionNotFoundError

        with pytest.raises(VisionNotFoundError):
            VisionDocument.from_file(tmp_path / "nonexistent.md")

    def test_freetext_sections_accept_arbitrary_markdown(self, tmp_path):
        """INV-03: Freitext-Abschnitte akzeptieren beliebigen Markdown-Inhalt."""
        from tool.sdd_cli.vision.document import VisionDocument

        content = SKELETON.replace(
            "## Vision\n",
            "## Vision\n\n**Fett**, *kursiv*, [Link](https://example.com), "
            "`code`, > Zitat\n"
        )
        vision_file = tmp_path / "vision.md"
        vision_file.write_text(content)
        doc = VisionDocument.from_file(vision_file)

        assert doc.validate() is True
        assert "**Fett**" in doc.vision_statement
