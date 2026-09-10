"""Lesen und Schreiben von Markdown-Dateien mit YAML-Frontmatter."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

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


_STATUS_LINE_RE = re.compile(r"^(?P<pre>status:[ \t]*)(?P<wert>[^\s#]+)", re.MULTILINE)


def patch_status(path: Path, new_status: str) -> None:
    """Setzt das status-Feld, ohne den Rest der Datei anzufassen.

    Frueher lief das ueber parse() -> frontmatter["status"] = ... -> write(),
    also einen vollstaendigen YAML-Roundtrip. Der schrieb das gesamte Frontmatter
    neu und verlor dabei alle Inline-Kommentare, die Quotes um Strings und die
    Leerzeile nach dem schliessenden ---.

    Zwei Folgen: die Frontmatter-Dokumentation verschwand bei jedem
    Statuswechsel, und der Content-Hash aenderte sich, obwohl
    compute_content_hash die status:-Zeile ausdruecklich herausfiltert. Der
    pre-commit-Hook stufte den gerade gesetzten Status daraufhin zurueck.

    Ersetzt wird deshalb nur die Statuszeile innerhalb des Frontmatter-Blocks;
    alles andere bleibt byte-identisch. Ein etwaiger Kommentar hinter dem Wert
    bleibt stehen.
    """
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return

    fm_alt = match.group("yaml")
    fm_neu, treffer = _STATUS_LINE_RE.subn(
        lambda m: f"{m.group('pre')}{new_status}", fm_alt, count=1
    )
    if not treffer:
        # Kein status-Feld vorhanden: hinten anfuegen, statt still nichts zu tun.
        fm_neu = f"{fm_alt}\nstatus: {new_status}"

    path.write_text(
        text[: match.start("yaml")] + fm_neu + text[match.end("yaml") :],
        encoding="utf-8",
    )
