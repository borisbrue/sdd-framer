from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .document import VisionNotFoundError  # re-exported for callers


class VisionEditor:
    def __init__(self, sdd_dir: Path) -> None:
        self._vision_file = sdd_dir / "vision.md"

    def open(self) -> None:
        if not self._vision_file.exists():
            raise VisionNotFoundError(
                "vision.md nicht gefunden. Nutze 'sdd vision init' um eine Vision zu erstellen."
            )
        editor = os.environ.get("EDITOR")
        if editor:
            subprocess.Popen([editor, str(self._vision_file)])
        else:
            print(str(self._vision_file))


__all__ = ["VisionEditor", "VisionNotFoundError"]
