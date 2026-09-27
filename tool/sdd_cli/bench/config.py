"""Matrix und Suiten laden und expandieren (SPEC-0056 FR-01, FR-03 bis FR-05, CON-0221).

Eine Belegung ordnet Rollen Profilreferenzen `profil[@variante]` zu. Varianten wirken nur im
Benchmark: Aus `profil@variante` entsteht ein abgeleitetes Profil im Speicher, `config.yaml` bleibt
unberührt (CON-0221 INV-02).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..config import SddConfig
from ..pipeline.roles import DEFAULT_ROLES
from ..pipeline.schemas import errors as schema_errors

CLAUDE_PROVIDERS = ("claude-cli", "anthropic")
CONFIG = "config"  # Rolle ohne Eintrag: Belegung aus config.yaml


class BenchError(Exception):
    """Matrix, Suite oder Profilreferenz ungültig (Exit 2)."""


@dataclass(frozen=True)
class Assignment:
    name: str
    roles: dict[str, str]  # Rolle → Profilreferenz


@dataclass
class Matrix:
    path: Path
    data: dict
    assignments: list[Assignment]
    suites: list[str]
    repetitions: int
    top_k: int | None
    budget: dict = field(default_factory=dict)

    @property
    def profile_refs(self) -> list[str]:
        """Profile für die Suite `roles`: `profiles` oder alle referenzierten Profile."""
        if self.data.get("profiles"):
            return list(dict.fromkeys(self.data["profiles"]))
        refs = [r for a in self.assignments for r in a.roles.values() if r != CONFIG]
        return list(dict.fromkeys(refs))


def _load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise BenchError(f"{path}: {exc}") from exc


def _slug(ref: str) -> str:
    return ref.replace("@", "-")


def load_matrix(path: Path, config: SddConfig) -> Matrix:
    daten = _load_yaml(path)
    fehler = schema_errors("bench-matrix", daten, "matrix")
    if fehler:
        raise BenchError(f"{path}: {fehler[0]}")
    belegungen = [Assignment(a["name"], _expand_roles(a["roles"]))
                  for a in daten.get("assignments") or []]
    sweep = daten.get("sweep")
    if sweep:
        basis = dict(belegungen[0].roles) if belegungen else {}
        for ref in sweep["profiles"]:
            belegungen.append(Assignment(f"sweep-{_slug(ref)}", {**basis, sweep["role"]: ref}))
    namen = [a.name for a in belegungen]
    doppelt = sorted({n for n in namen if namen.count(n) > 1})
    if doppelt:
        raise BenchError(f"Belegungen doppelt benannt: {', '.join(doppelt)}")
    matrix = Matrix(path, daten, belegungen, list(daten["suites"]),
                    int(daten.get("repetitions", 3)), daten.get("top_k"),
                    dict(daten.get("budget") or {}))
    for ref in {*matrix.profile_refs, *(r for a in belegungen for r in a.roles.values())}:
        if ref != CONFIG:
            resolve_profile(config, matrix, ref)
    return matrix


def _expand_roles(roles: dict[str, str]) -> dict[str, str]:
    stern = roles.get("*")
    ergebnis = {r: roles.get(r, stern or CONFIG) for r in DEFAULT_ROLES}
    ergebnis.update({r: p for r, p in roles.items() if r != "*"})
    return ergebnis


def resolve_profile(config: SddConfig, matrix: Matrix, ref: str) -> dict:
    """Profil-Dict für `profil[@variante]` (Profil-Parameter plus Variante)."""
    name, _, variante = ref.partition("@")
    profile = (config.raw.get("llm") or {}).get("profiles") or {}
    if name not in profile:
        raise BenchError(f"Profil {name!r} fehlt in llm.profiles.")
    ergebnis = dict(profile[name])
    if variante:
        varianten = matrix.data.get("variants") or {}
        if variante not in varianten:
            raise BenchError(f"Variante {variante!r} fehlt in variants.")
        ergebnis.update(varianten[variante])
    return ergebnis


def overlay(config: SddConfig, matrix: Matrix, roles: dict[str, str]) -> SddConfig:
    """Config im Speicher: abgeleitete Profile und die Belegung als `llm.roles.<rolle>.profile`."""
    raw = copy.deepcopy(config.raw)
    llm = raw.setdefault("llm", {})
    profile = llm.setdefault("profiles", {})
    rollen = llm.setdefault("roles", {})
    for rolle, ref in roles.items():
        if ref == CONFIG:
            continue
        profile[ref] = resolve_profile(config, matrix, ref)
        rollen[rolle] = {"profile": ref}
    return SddConfig(root=config.root, raw=raw, raw_basis=config.raw_basis)


@dataclass
class Suite:
    path: Path
    data: dict

    @property
    def name(self) -> str:
        return self.data["name"]

    @property
    def kind(self) -> str:
        return self.data["kind"]


def load_suite(root: Path, name: str) -> Suite:
    pfad = root / "bench" / "suites" / f"{name}.yaml"
    if not pfad.is_file():
        raise BenchError(f"Suite {name!r} fehlt ({pfad}).")
    daten = _load_yaml(pfad)
    fehler = schema_errors("bench-matrix", daten, "suite")
    if fehler:
        raise BenchError(f"{pfad}: {fehler[0]}")
    if daten["name"] != name:
        raise BenchError(f"{pfad}: name ist {daten['name']!r}, erwartet {name!r}")
    return Suite(pfad, daten)
