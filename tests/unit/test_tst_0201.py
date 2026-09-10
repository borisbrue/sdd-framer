"""TST-0201 – sdd vision init – Wizard und Idempotenz-Guard (Unit)
Spec: SPEC-0046 · Contract: CON-0175
"""

import pytest


class TestVisionInitWizard:
    def test_creates_vision_file_with_answers(self, tmp_path):
        """INV-01/INV-05: Wizard erstellt genau .sdd/vision.md mit Pflicht-Überschriften."""
        from tool.sdd_cli.vision.init import VisionInitWizard

        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        answers = {
            "vision_statement": "Ein CLI für strukturiertes Entwickeln.",
            "target_audience": "Solo-Entwickler",
            "tech_stack": "Python, Typer",
            "competitive_landscape": "GitHub Copilot",
            "core_problems": "Fehlende Struktur vor dem ersten Commit",
        }
        wizard = VisionInitWizard(sdd_dir=sdd_dir)
        wizard.run(answers=answers)

        vision_file = sdd_dir / "vision.md"
        assert vision_file.exists()
        content = vision_file.read_text()
        for heading in ("## Vision", "## Zielgruppe", "## Tech Stack",
                        "## Competitive Landscape", "## Kernprobleme",
                        "## Features", "## Tasks"):
            assert heading in content
        assert "Ein CLI für strukturiertes Entwickeln." in content
        assert "Solo-Entwickler" in content

    def test_only_vision_md_created(self, tmp_path):
        """INV-01: Keine weiteren Dateien außer vision.md."""
        from tool.sdd_cli.vision.init import VisionInitWizard

        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        before = set(sdd_dir.iterdir())
        VisionInitWizard(sdd_dir=sdd_dir).run(answers={})
        after = set(sdd_dir.iterdir())
        new_files = after - before
        assert len(new_files) == 1
        assert next(iter(new_files)).name == "vision.md"

    def test_empty_answers_produce_skeleton(self, tmp_path):
        """INV-03: Leere Felder → gültiges Skelett-Dokument (alle Überschriften, leerer Inhalt)."""
        from tool.sdd_cli.vision.init import VisionInitWizard

        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        VisionInitWizard(sdd_dir=sdd_dir).run(answers={})

        content = (sdd_dir / "vision.md").read_text()
        for heading in ("## Vision", "## Zielgruppe", "## Tech Stack",
                        "## Competitive Landscape", "## Kernprobleme",
                        "## Features", "## Tasks"):
            assert heading in content

    def test_idempotency_guard_raises_when_file_exists(self, tmp_path):
        """INV-02: Existiert vision.md bereits → Fehler, Datei unverändert."""
        from tool.sdd_cli.vision.init import VisionAlreadyExistsError, VisionInitWizard

        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        existing = sdd_dir / "vision.md"
        existing.write_text("# original")

        with pytest.raises(VisionAlreadyExistsError) as exc_info:
            VisionInitWizard(sdd_dir=sdd_dir).run(answers={"vision_statement": "neu"})

        assert "vision.md" in str(exc_info.value)
        assert existing.read_text() == "# original"

    def test_idempotency_guard_error_mentions_path(self, tmp_path):
        """INV-02: Fehlermeldung enthält Pfad zu vision.md."""
        from tool.sdd_cli.vision.init import VisionAlreadyExistsError, VisionInitWizard

        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        (sdd_dir / "vision.md").write_text("# x")

        with pytest.raises(VisionAlreadyExistsError) as exc_info:
            VisionInitWizard(sdd_dir=sdd_dir).run(answers={})

        assert str(sdd_dir / "vision.md") in str(exc_info.value)

    def test_init_skippable_does_not_create_file(self, tmp_path):
        """INV-04: sdd init – Vision-Schritt überspringen hinterlässt keine vision.md."""
        from tool.sdd_cli.vision.init import VisionInitWizard

        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        wizard = VisionInitWizard(sdd_dir=sdd_dir)
        wizard.run(answers=None, skip=True)

        assert not (sdd_dir / "vision.md").exists()

    def test_no_yaml_frontmatter_in_output(self, tmp_path):
        """INV-06 (CON-0179): Kein YAML-Frontmatter-Block in erzeugtem Dokument."""
        from tool.sdd_cli.vision.init import VisionInitWizard

        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        VisionInitWizard(sdd_dir=sdd_dir).run(answers={"vision_statement": "Test"})

        content = (sdd_dir / "vision.md").read_text()
        assert not content.startswith("---")
