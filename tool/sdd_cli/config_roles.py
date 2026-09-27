"""Belegung aus einem Benchmark in `config.yaml` übernehmen (SPEC-0056 FR-11, CON-0224 INV-07).

Je Rolle `llm.roles.<rolle>: {profile: …}`; eine Variante `profil@variante` wird als abgeleitetes
Profil `profil-variante` angelegt, damit keine Rolle `profile` und eigene Parameter zugleich trägt
(CON-0212 INV-01). Geschrieben wird zeilenbasiert wie die Config-Migration (Kommentare bleiben);
ersetzte Rollenblöcke werden auskommentiert. Vor dem Schreiben prüft `role_config_issues`.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path

import yaml

from .config import SddConfig, load_config

PREFIX = "# [apply-roles] "


class ApplyError(Exception):
    """Belegung unbekannt, Profil fehlt oder Ergebnis ungültig."""


@dataclass
class ApplyPlan:
    new_text: str
    diff: str
    roles: dict[str, str]


def _derived_name(ref: str) -> str:
    return ref.replace("@", "-")


def plan_apply(config: SddConfig, records: list[dict], assignment: str) -> ApplyPlan:
    treffer = [r for r in records if r.get("assignment") == assignment]
    if not treffer:
        raise ApplyError(f"Belegung {assignment!r} gibt es im Ergebnisordner nicht.")
    rollen = treffer[0]["roles"]
    pfad = config.root / ".sdd" / "config.yaml"
    text = pfad.read_text(encoding="utf-8")
    daten = yaml.safe_load(text) or {}
    profile = (daten.get("llm") or {}).get("profiles") or {}

    from .pipeline.config_migration import comment_out_block, insert_block

    zeilen = text.splitlines(keepends=True)
    ziel: dict[str, str] = {}
    for rolle, info in sorted(rollen.items()):
        ref = info["profile"]
        if ref == "config":
            continue
        basis, _, variante = ref.partition("@")
        if basis not in profile:
            raise ApplyError(f"Profil {basis!r} fehlt in llm.profiles.")
        name = basis
        if variante:
            name = _derived_name(ref)
            abgeleitet = {**profile[basis], **(info.get("params") or {})}
            abgeleitet = {k: v for k, v in abgeleitet.items() if v is not None}
            if name in profile and profile[name] != abgeleitet:
                raise ApplyError(f"Profil {name!r} existiert bereits mit anderen Werten.")
            if name not in profile:
                insert_block(zeilen, ("llm", "profiles"), {name: abgeleitet})
                profile[name] = abgeleitet
        comment_out_block(zeilen, ("llm", "roles", rolle), PREFIX)
        insert_block(zeilen, ("llm", "roles"), {rolle: {"profile": name}})
        ziel[rolle] = name
    neu = "".join(zeilen)
    _check(config.root, neu)
    diff = "".join(difflib.unified_diff(text.splitlines(keepends=True),
                                        neu.splitlines(keepends=True),
                                        "config.yaml", "config.yaml (neu)"))
    return ApplyPlan(neu, diff, ziel)


def _check(root: Path, text: str) -> None:
    from .pipeline.facade import role_config_issues

    try:
        daten = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise ApplyError(f"Ergebnis ist kein gültiges YAML: {exc}") from exc
    probleme = [f"{pfad}: {text_}" for stufe, pfad, text_ in
                role_config_issues(SddConfig(root=root, raw=daten, raw_basis=daten))
                if stufe == "error"]
    if probleme:
        raise ApplyError("Ergebnis verletzt die Regeln für llm.roles/llm.profiles: "
                         + "; ".join(probleme[:5]))


def write(config: SddConfig, plan: ApplyPlan) -> None:
    (config.root / ".sdd" / "config.yaml").write_text(plan.new_text, encoding="utf-8")


__all__ = ["ApplyError", "ApplyPlan", "load_config", "plan_apply", "write"]
