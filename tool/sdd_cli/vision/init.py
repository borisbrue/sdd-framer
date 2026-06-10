from __future__ import annotations

from pathlib import Path

from .document import VisionDocument


class VisionAlreadyExistsError(FileExistsError):
    pass


class VisionInitWizard:
    def __init__(self, sdd_dir: Path) -> None:
        self.sdd_dir = sdd_dir

    def run(self, answers: dict | None = None, skip: bool = False) -> None:
        if skip:
            return

        vision_file = self.sdd_dir / "vision.md"
        if vision_file.exists():
            raise VisionAlreadyExistsError(
                f"vision.md existiert bereits: {vision_file}\n"
                "Nutze 'sdd vision edit' um es zu bearbeiten."
            )

        if answers is None:
            answers = {}

        doc = VisionDocument(path=vision_file)
        doc.vision_statement = answers.get("vision_statement", "")
        doc.target_audience = answers.get("target_audience", "")
        doc.tech_stack = answers.get("tech_stack", "")
        doc.competitive_landscape = answers.get("competitive_landscape", "")
        doc.core_problems = answers.get("core_problems", "")
        doc.save()
