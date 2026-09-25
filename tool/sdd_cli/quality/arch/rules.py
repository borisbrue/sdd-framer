"""Laden von `.sdd/architecture.yaml` und Zuordnung von Dateien zu Schichten (CON-0194)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..files import matches_any
from ..schemas import error_path, validator

ARCH_FILE = Path(".sdd") / "architecture.yaml"
LAYER_FIELDS = ("from", "to_layers", "in", "owners")


def _liste(wert: object) -> list[str]:
    if wert is None:
        return []
    return [wert] if isinstance(wert, str) else list(wert)


@dataclass(frozen=True)
class Rule:
    id: str
    adr: str
    kind: str
    severity: str = "error"
    params: dict = field(default_factory=dict)
    description: str = ""

    def layers(self, key: str) -> list[str]:
        return _liste(self.params.get(key))

    def unknown_layers(self, known: list[str]) -> list[str]:
        genannt = [s for key in LAYER_FIELDS for s in self.layers(key)]
        if self.kind == "allowed_dependencies":
            graph = self.params.get("graph") or {}
            genannt += list(graph) + [z for ziele in graph.values() for z in ziele]
        return [s for s in dict.fromkeys(genannt) if s not in known]


@dataclass
class Architecture:
    layers: dict[str, list[str]]
    rules: list[Rule]


class ArchConfigError(Exception):
    def __init__(self, problems: list[tuple[str, str]]) -> None:
        self.problems = problems
        super().__init__("; ".join(f"{p}: {m}" for p, m in problems))


def layer_of(path: str, layers: dict[str, list[str]]) -> str | None:
    """Erste Schicht in Deklarationsreihenfolge, deren Muster passt (CON-0194 INV-02)."""
    return next((name for name, globs in layers.items() if matches_any(path, globs)), None)


def parse_architecture(raw: object) -> Architecture:
    problems = [(error_path(e), e.message)
                for e in validator("architecture-rules").iter_errors(raw)]
    if problems:
        raise ArchConfigError(problems)
    rules = []
    for r in raw["rules"]:
        params = {k: v for k, v in r.items()
                  if k not in ("id", "adr", "kind", "severity", "description")}
        rules.append(Rule(r["id"], r["adr"], r["kind"], r.get("severity", "error"), params,
                          r.get("description", "")))
    return Architecture(dict(raw["layers"]), rules)


def load_raw(root: Path) -> object:
    pfad = root / ARCH_FILE
    if not pfad.is_file():
        raise FileNotFoundError(pfad)
    try:
        return yaml.safe_load(pfad.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ArchConfigError([("(Datei)", f"kein gültiges YAML: {exc}")]) from exc


def load_architecture(root: Path) -> Architecture:
    return parse_architecture(load_raw(root))
