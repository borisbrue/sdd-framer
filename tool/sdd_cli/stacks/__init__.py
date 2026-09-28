"""Stack-Vorlagen: Projekte für Testbarkeit und Qualitätsmessung aufsetzen (SPEC-0057).

Eine Vorlage ist Daten (Prototype): `stack.yaml`, `files/` und optional `agents-md/`. Gesucht wird
in der Quellenkette Projekt → Nutzer → Blueprint (Chain of Responsibility). `apply` hält die
angewendete Version mit Datei-Hashes in `config.yaml` fest (Memento), `diff` vergleicht dagegen.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

BLUEPRINT_STACKS = Path(__file__).resolve().parents[1] / "blueprint" / "stacks"
SOURCES = ("project", "user", "blueprint")
PLACEHOLDER = re.compile(r"\{\{([a-z][a-z0-9_]*)\}\}")
QUALITY_ONLY = (".sdd/quality.yaml", ".sdd/quality/")


class StackError(Exception):
    """Vorlage fehlt oder verletzt CON-0227 (Exit 2)."""


@cache
def _schema() -> dict:
    return json.loads((Path(__file__).with_name("stack.schema.json")).read_text(encoding="utf-8"))


def errors(definition: str, instance: object) -> list[str]:
    schema = _schema()
    validator = Draft202012Validator({"$ref": f"#/$defs/{definition}", "$defs": schema["$defs"]})
    return [f"{'.'.join(map(str, e.absolute_path)) or '(Wurzel)'}: {e.message}"
            for e in sorted(validator.iter_errors(instance), key=lambda e: list(e.path))]


def user_dir() -> Path:
    return Path(os.environ.get("SDD_STACKS_HOME") or Path.home() / ".config" / "sdd" / "stacks")


def source_dirs(root: Path) -> list[tuple[str, Path]]:
    return [("project", root / ".sdd" / "stacks"), ("user", user_dir()),
            ("blueprint", BLUEPRINT_STACKS)]


def sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Stack:
    name: str
    dir: Path
    source: str
    data: dict

    @property
    def version(self) -> str:
        return str(self.data["version"])

    @property
    def files_dir(self) -> Path:
        return self.dir / "files"

    def files(self) -> list[Path]:
        if not self.files_dir.is_dir():
            return []
        return sorted(p for p in self.files_dir.rglob("*")
                      if p.is_file() and "__pycache__" not in p.parts)

    def agents_sections(self) -> list[Path]:
        ordner = self.dir / "agents-md"
        return sorted(ordner.glob("*.md")) if ordner.is_dir() else []

    def placeholders(self) -> dict[str, dict]:
        return {p["name"]: p for p in self.data.get("placeholders") or []}


def load(ordner: Path, source: str) -> Stack:
    datei = ordner / "stack.yaml"
    try:
        daten = yaml.safe_load(datei.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise StackError(f"{datei}: {exc}") from exc
    fehler = errors("stack", daten)
    if fehler:
        raise StackError(f"{datei}: {fehler[0]}")
    stack = Stack(daten["name"], ordner, source, daten)
    if stack.name != ordner.name:
        raise StackError(f"{datei}: name ist {stack.name!r}, Verzeichnis {ordner.name!r}")
    if not stack.files_dir.is_dir():
        raise StackError(f"{ordner}: files/ fehlt")
    deklariert = set(stack.placeholders())
    genutzt = set()
    for pfad in [*stack.files(), *stack.agents_sections()]:
        genutzt |= set(PLACEHOLDER.findall(str(pfad.relative_to(ordner))))
        genutzt |= set(PLACEHOLDER.findall(pfad.read_text(encoding="utf-8", errors="replace")))
    for eintrag in daten.get("verify") or []:
        genutzt |= set(PLACEHOLDER.findall(eintrag["command"]))
    fehlend = sorted(genutzt - deklariert)
    if fehlend:
        raise StackError(f"{datei}: Platzhalter nicht deklariert: {', '.join(fehlend)}")
    return stack


@dataclass(frozen=True)
class Listed:
    stack: Stack | None
    source: str
    name: str
    shadowed: bool
    error: str | None = None


def list_all(root: Path) -> list[Listed]:
    """Alle Vorlagen aller Quellen; spätere mit gleichem Namen sind verdeckt (CON-0228 INV-01)."""
    gesehen: set[str] = set()
    ergebnis: list[Listed] = []
    for quelle, ordner in source_dirs(root):
        if not ordner.is_dir():
            continue
        for kandidat in sorted(p for p in ordner.iterdir() if (p / "stack.yaml").is_file()):
            try:
                stack = load(kandidat, quelle)
                ergebnis.append(Listed(stack, quelle, stack.name, stack.name in gesehen))
            except StackError as exc:
                ergebnis.append(Listed(None, quelle, kandidat.name, kandidat.name in gesehen,
                                       str(exc)))
            gesehen.add(kandidat.name)
    return ergebnis


def find(root: Path, name: str) -> Stack:
    for quelle, ordner in source_dirs(root):
        kandidat = ordner / name
        if (kandidat / "stack.yaml").is_file():
            return load(kandidat, quelle)
    raise StackError(f"Vorlage {name!r} gibt es in keiner Quelle.")


def preset_alias(preset: str) -> str:
    """Vorlage, die ein früheres Preset ersetzt (CON-0229 INV-08); unbekannt: der Name selbst."""
    try:
        daten = yaml.safe_load((BLUEPRINT_STACKS / "preset-aliases.yaml").read_text(
            encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        daten = {}
    return str(daten.get(preset, preset))


def applied(config_raw: dict) -> list[dict]:
    eintraege = config_raw.get("stack") or []
    return eintraege if isinstance(eintraege, list) else []
