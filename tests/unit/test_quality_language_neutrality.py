"""SPEC-0054 Erfolgskriterium 1 und NFR Sprachneutralität.

Weder der Kern (`tool/sdd_cli/quality/`, `tool/sdd_cli/stacks/`) noch die CLI-Dateien
(`quality_cli.py`, `stack_cli.py`) nennen Sprach- oder Werkzeugnamen. Sprachwissen liegt
ausschließlich in Stack-Vorlagen unter `tool/sdd_cli/blueprint/stacks/` (SPEC-0057).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[2] / "tool/sdd_cli"
NAMEN = ["python", "pytest", "ruff", "mypy", "pyright", "lizard", "flake8", "pylint", "rust",
         "cargo", "clippy", "nodejs", "deno", "npm", "eslint", "jest", "golang", "java", "maven", "gradle"]
MUSTER = re.compile(r"\b(" + "|".join(NAMEN) + r")\b", re.IGNORECASE)
DATEIEN = sorted([*(TOOL / "quality").rglob("*.py"), *(TOOL / "stacks").rglob("*.py"),
                  TOOL / "quality_cli.py", TOOL / "stack_cli.py"])


def test_es_gibt_kerndateien():
    assert len(DATEIEN) > 10


@pytest.mark.parametrize("datei", DATEIEN, ids=lambda p: str(p.relative_to(TOOL)))
def test_keine_sprach_oder_werkzeugnamen(datei):
    treffer = [f"{i}: {z.strip()}" for i, z in enumerate(datei.read_text().splitlines(), 1)
               if MUSTER.search(z)]
    assert treffer == [], f"{datei.name} nennt Sprach-/Werkzeugnamen:\n" + "\n".join(treffer)
