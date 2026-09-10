"""TST-0203 – sdd vision add-feature und sdd vision add-task (Unit)
Spec: SPEC-0046 · Contract: CON-0177
"""
import pytest

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


class TestAddFeature:
    def test_add_feature_with_description(self, tmp_path):
        """INV-01: Feature als `1. **Titel** – Beschreibung` in ## Features."""
        from tool.sdd_cli.vision.document import VisionDocument

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(SKELETON)
        doc = VisionDocument.from_file(vision_file)

        doc.add_feature("Offline-Modus", "App ohne Internet nutzbar")
        doc.save()

        content = vision_file.read_text()
        assert "1. **Offline-Modus** – App ohne Internet nutzbar" in content

    def test_add_feature_without_description(self, tmp_path):
        """INV-01: Feature ohne Beschreibung nur als `1. **Titel**`."""
        from tool.sdd_cli.vision.document import VisionDocument

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(SKELETON)
        doc = VisionDocument.from_file(vision_file)

        doc.add_feature("Export als PDF")
        doc.save()

        content = vision_file.read_text()
        assert "1. **Export als PDF**" in content

    def test_second_feature_gets_next_index(self, tmp_path):
        """INV-01: Zweites Feature erhält Index 2, erstes bleibt Index 1."""
        from tool.sdd_cli.vision.document import VisionDocument

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(SKELETON)
        doc = VisionDocument.from_file(vision_file)
        doc.add_feature("Erstes Feature")
        doc.add_feature("Zweites Feature")
        doc.save()

        content = vision_file.read_text()
        assert "1. **Erstes Feature**" in content
        assert "2. **Zweites Feature**" in content

    def test_add_feature_empty_title_raises(self, tmp_path):
        """INV-04: Leerer Titel → ValueError."""
        from tool.sdd_cli.vision.document import VisionDocument

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(SKELETON)
        doc = VisionDocument.from_file(vision_file)

        with pytest.raises(ValueError, match="[Tt]itel"):
            doc.add_feature("")

    def test_add_feature_does_not_touch_tasks(self, tmp_path):
        """INV-06: ## Tasks bleibt unverändert."""
        from tool.sdd_cli.vision.document import VisionDocument

        content_with_task = SKELETON + "- [ ] Bestehender Task\n"
        vision_file = tmp_path / "vision.md"
        vision_file.write_text(content_with_task)
        doc = VisionDocument.from_file(vision_file)
        doc.add_feature("Neues Feature")
        doc.save()

        assert "- [ ] Bestehender Task" in vision_file.read_text()

    def test_add_feature_does_not_overwrite_challenge_result(self, tmp_path):
        """INV-06: Bestehendes LLM-Challenge-Ergebnis bleibt erhalten."""
        from tool.sdd_cli.vision.document import VisionDocument

        content = SKELETON.replace(
            "## Features\n",
            "## Features\n\n1. **Alt** – Beschreibung\n   > LLM Challenge: Aufwand: low\n"
        )
        vision_file = tmp_path / "vision.md"
        vision_file.write_text(content)
        doc = VisionDocument.from_file(vision_file)
        doc.add_feature("Neu")
        doc.save()

        result = vision_file.read_text()
        assert "> LLM Challenge: Aufwand: low" in result
        assert "2. **Neu**" in result


class TestAddTask:
    def test_add_task_as_checkbox(self, tmp_path):
        """INV-02: Task als `- [ ] Titel` in ## Tasks."""
        from tool.sdd_cli.vision.document import VisionDocument

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(SKELETON)
        doc = VisionDocument.from_file(vision_file)
        doc.add_task("README aktualisieren")
        doc.save()

        assert "- [ ] README aktualisieren" in vision_file.read_text()

    def test_add_task_empty_title_raises(self, tmp_path):
        """INV-04: Leerer Titel → ValueError."""
        from tool.sdd_cli.vision.document import VisionDocument

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(SKELETON)
        doc = VisionDocument.from_file(vision_file)

        with pytest.raises(ValueError, match="[Tt]itel"):
            doc.add_task("")

    def test_add_task_does_not_touch_features(self, tmp_path):
        """INV-06: ## Features bleibt unverändert."""
        from tool.sdd_cli.vision.document import VisionDocument

        content = SKELETON.replace(
            "## Features\n", "## Features\n\n1. **Bestehendes Feature**\n"
        )
        vision_file = tmp_path / "vision.md"
        vision_file.write_text(content)
        doc = VisionDocument.from_file(vision_file)
        doc.add_task("Neuer Task")
        doc.save()

        assert "1. **Bestehendes Feature**" in vision_file.read_text()

    def test_from_file_raises_when_missing(self, tmp_path):
        """INV-03: from_file wirft Exception wenn vision.md nicht existiert."""
        from tool.sdd_cli.vision.document import VisionDocument, VisionNotFoundError

        with pytest.raises(VisionNotFoundError):
            VisionDocument.from_file(tmp_path / "nonexistent.md")
