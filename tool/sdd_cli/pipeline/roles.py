"""Rollen als Daten: `.sdd/roles/<rolle>.md` (SPEC-0053 FR-01 bis FR-03, CON-0199).

Die Frontmatter ist der Vertrag der Rolle, der Body ihr System-Prompt. Fehlt die Datei im
Projekt, gilt die mitgelieferte Default-Rolle aus dem Blueprint.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .schemas import errors

BLUEPRINT_ROLES = Path(__file__).resolve().parents[1] / "blueprint" / "roles"
DEFAULT_ROLES = ("decomposer", "test_author", "implementer", "reviewer", "supervisor")
# Rollen außerhalb des Pipeline-Ablaufs; `judge` bewertet Rubriken (SPEC-0055 FR-12).
ALL_ROLES = (*DEFAULT_ROLES, "judge")

# Geschlossene Liste der Kontextquellen (FR-03, CON-0199 INV-01); `.sdd/holdout/` ist keine.
CONTEXT_SOURCES = ("spec", "contracts", "agents_md", "repo_map", "task", "test_file",
                   "test_output", "diff", "gate_results", "review", "history")
DEFAULT_BUDGET = 4000  # Tokens je Quelle, wenn die Rolle kein Budget nennt


class RoleError(Exception):
    """Rollendatei fehlt oder verletzt CON-0199."""


@dataclass(frozen=True)
class RoleDefinition:
    role: str
    version: str
    purpose: str
    inputs: tuple[str, ...]
    output_schema: str
    checks: tuple[str, ...]
    legacy_component: str
    prompt: str
    defaults: dict = field(default_factory=dict)
    input_budgets: dict = field(default_factory=dict)
    source: Path | None = None

    def budget(self, quelle: str) -> int:
        return int(self.input_budgets.get(quelle, DEFAULT_BUDGET))

    @property
    def prompt_hash(self) -> str:
        return hashlib.sha256(self.prompt.encode("utf-8")).hexdigest()[:16]

    def schema_ref(self) -> tuple[str, str | None]:
        """(Paketschema, $defs-Eintrag) aus `output_schema`.

        Akzeptiert `role-outputs#/$defs/decomposer` ebenso wie einen Contract-Pfad wie
        `contracts/data/role-outputs.schema.json#/$defs/decomposer`.
        """
        pfad, _, fragment = self.output_schema.partition("#")
        name = Path(pfad).name.removesuffix(".json").removesuffix(".schema")
        definition = fragment.rsplit("/", 1)[-1] if fragment.startswith("/$defs/") else None
        return name, definition


def split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        raise RoleError("Rollendatei ohne Frontmatter")
    _, kopf, body = text.split("---", 2)
    daten = yaml.safe_load(kopf) or {}
    if not isinstance(daten, dict):
        raise RoleError("Frontmatter ist kein Objekt")
    return daten, body.strip()


def role_path(root: Path, role: str) -> Path:
    projekt = root / ".sdd" / "roles" / f"{role}.md"
    return projekt if projekt.is_file() else BLUEPRINT_ROLES / f"{role}.md"


def load_role(root: Path, role: str) -> RoleDefinition:
    pfad = role_path(root, role)
    if not pfad.is_file():
        raise RoleError(f"Rolle {role!r} nicht gefunden (.sdd/roles/{role}.md)")
    return load_role_file(pfad, role)


def load_blueprint_role(role: str) -> RoleDefinition:
    """Default-Rolle aus dem Blueprint, unabhängig vom Projekt (z. B. bei altem `judge.md`)."""
    return load_role_file(BLUEPRINT_ROLES / f"{role}.md", role)


def load_role_file(pfad: Path, role: str) -> RoleDefinition:
    daten, prompt = split_frontmatter(pfad.read_text(encoding="utf-8"))
    fehler = errors("role-definition", daten)
    if fehler:
        raise RoleError(f"{pfad.name}: " + "; ".join(fehler))
    if daten["role"] != role:
        raise RoleError(f"{pfad.name}: role ist {daten['role']!r}, erwartet {role!r}")
    if not prompt:
        raise RoleError(f"{pfad.name}: System-Prompt fehlt")
    return RoleDefinition(
        role=daten["role"], version=daten["version"], purpose=daten["purpose"],
        inputs=tuple(daten["inputs"]), output_schema=daten["output_schema"],
        checks=tuple(daten["checks"]), legacy_component=daten["legacy_component"],
        prompt=prompt, defaults=dict(daten.get("defaults") or {}),
        input_budgets=dict(daten.get("input_budgets") or {}), source=pfad,
    )


def install_roles(root: Path) -> tuple[list[Path], list[Path], list[Path]]:
    """Installiert die Default-Rollen (FR-02).

    Fehlende Rollen werden angelegt, identische übersprungen. Eine lokal abweichende Rolle bleibt
    unangetastet; die neue Version landet als `<rolle>.md.new` daneben.
    Gibt (angelegt, als .new abgelegt, übersprungen) zurück.
    """
    ziel = root / ".sdd" / "roles"
    ziel.mkdir(parents=True, exist_ok=True)
    angelegt: list[Path] = []
    neu: list[Path] = []
    gleich: list[Path] = []
    for quelle in sorted(BLUEPRINT_ROLES.glob("*.md")):
        inhalt = quelle.read_text(encoding="utf-8")
        datei = ziel / quelle.name
        if not datei.exists():
            datei.write_text(inhalt, encoding="utf-8")
            angelegt.append(datei)
        elif datei.read_text(encoding="utf-8") == inhalt:
            gleich.append(datei)
        else:
            kandidat = datei.with_name(datei.name + ".new")
            kandidat.write_text(inhalt, encoding="utf-8")
            neu.append(kandidat)
    return angelegt, neu, gleich
