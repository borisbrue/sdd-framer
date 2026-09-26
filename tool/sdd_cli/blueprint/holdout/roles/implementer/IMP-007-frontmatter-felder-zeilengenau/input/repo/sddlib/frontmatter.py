"""Frontmatter-Erkennung für Markdown-Artefakte."""
from __future__ import annotations

import re

# Frontmatter: erste Zeile '---', YAML-Block, schließende Zeile '---', danach der Rumpf.
FRONTMATTER_RE = re.compile(
    r"^---\s*\n(?P<yaml>.*?)\n---\s*\n(?P<body>.*)$",
    re.DOTALL,
)


def has_frontmatter(text: str) -> bool:
    return FRONTMATTER_RE.match(text) is not None
