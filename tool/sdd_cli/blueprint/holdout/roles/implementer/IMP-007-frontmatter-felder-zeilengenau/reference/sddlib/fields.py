"""Frontmatter-Felder zeilengenau setzen; der Rest der Datei bleibt byte-gleich."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .frontmatter import FRONTMATTER_RE


class FrontmatterError(Exception):
    """Datei ohne Frontmatter."""


def set_frontmatter_fields(path: Path, fields: dict[str, str]) -> None:
    """Setzt einfache Frontmatter-Felder zeilengenau; fehlende werden angehängt."""
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise FrontmatterError(f"{path.name}: kein Frontmatter")
    fm = match.group("yaml")
    for key, value in fields.items():
        zeile = f"{key}: {json.dumps(value, ensure_ascii=False)}"
        fm, treffer = re.subn(rf"(?m)^{re.escape(key)}:.*$", lambda _m, z=zeile: z, fm, count=1)
        if not treffer:
            fm = f"{fm.rstrip()}\n{zeile}"
    start, ende = match.span("yaml")
    path.write_text(text[:start] + fm + text[ende:], encoding="utf-8")
