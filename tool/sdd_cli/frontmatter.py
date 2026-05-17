"""Lesen und Schreiben von Markdown-Dateien mit YAML-Frontmatter."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import yaml


FRONTMATTER_RE = re.compile(
    r"^---\s*\n(?P<yaml>.*?)\n---\s*\n(?P<body>.*)$",
    re.DOTALL,
)


@dataclass
class Document:
    """Markdown-Dokument mit Frontmatter."""
    path: Path
    frontmatter: dict
    body: str

    def dump(self) -> str:
        yaml_text = yaml.safe_dump(
            self.frontmatter, sort_keys=False, allow_unicode=True
        ).rstrip("\n")
        return f"---\n{yaml_text}\n---\n{self.body}"

    def write(self) -> None:
        self.path.write_text(self.dump(), encoding="utf-8")


def parse(path: Path) -> Document:
    """Liest eine Markdown-Datei und extrahiert Frontmatter + Body."""
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return Document(path=path, frontmatter={}, body=text)
    fm = yaml.safe_load(match.group("yaml")) or {}
    return Document(path=path, frontmatter=fm, body=match.group("body"))


def parse_safe(path: Path) -> Document | None:
    """Wie parse(), gibt aber None zurück, wenn die Datei nicht lesbar ist."""
    try:
        return parse(path)
    except Exception:
        return None


def patch_status(path: Path, new_status: str) -> None:
    """Setzt das status-Feld im Frontmatter einer Markdown-Datei."""
    doc = parse(path)
    doc.frontmatter["status"] = new_status
    doc.write()
