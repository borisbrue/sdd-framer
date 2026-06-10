from __future__ import annotations

from pathlib import Path

from .document import VisionNotFoundError  # re-exported for callers


class VisionReader:
    def __init__(self, sdd_dir: Path) -> None:
        self._vision_file = sdd_dir / "vision.md"

    def show(self) -> None:
        if not self._vision_file.exists():
            raise VisionNotFoundError(
                f"vision.md nicht gefunden. Nutze 'sdd vision init' um eine Vision zu erstellen."
            )
        print(self._vision_file.read_text(), end="")


__all__ = ["VisionReader", "VisionNotFoundError"]
