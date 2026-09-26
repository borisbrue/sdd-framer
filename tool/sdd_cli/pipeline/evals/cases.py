"""Golden Cases einer Rolle (SPEC-0055 FR-01, FR-02, CON-0217).

Sichtbare Fälle liegen unter `<heimat>/cases/<ID>-<slug>/`, Holdout-Fälle unter
`.sdd/holdout/roles/<rolle>/<ID>-<slug>/` – der Ort allein entscheidet. Die „Heimat“ einer Rolle ist
das Projekt (`.sdd/roles/`), außer die Rolle kommt aus dem Blueprint und der Blueprint liegt im
Projekt selbst (sdd-framer); dann sind Rollendatei, Fälle und Baseline die des Blueprints.
"""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ..checks import REGISTRY, check_errors
from ..roles import BLUEPRINT_ROLES, role_path
from ..schemas import errors as schema_errors

BLUEPRINT = BLUEPRINT_ROLES.parent
PREFIX = {"decomposer": "DEC", "test_author": "TAU", "implementer": "IMP", "reviewer": "REV",
          "supervisor": "SUP", "judge": "JDG"}
CASE_FILE = "case.yaml"
PARTS = ("reference", "hidden", "mutants", "expected")
MIN_HOLDOUT = 3


class CaseError(Exception):
    """Fall fehlt, ist ungültig oder die ID ist vergeben."""


@dataclass(frozen=True)
class RoleHome:
    role: str
    role_file: Path
    cases_dir: Path
    holdout_dir: Path

    @property
    def data_dir(self) -> Path:
        return self.role_file.parent / self.role

    @property
    def baseline(self) -> Path:
        return self.data_dir / "baseline.json"

    @property
    def changelog(self) -> Path:
        return self.data_dir / "CHANGELOG.md"

    @property
    def holdout_reports(self) -> Path:
        return self.holdout_dir / "reports"


def role_home(root: Path, role: str) -> RoleHome:
    """Heimat nach FR-08: Projekt, außer die Rolle kommt aus einem Blueprint im Projekt."""
    root = root.resolve()
    datei = role_path(root, role).resolve()
    if datei.is_relative_to(BLUEPRINT_ROLES.resolve()) and BLUEPRINT.resolve().is_relative_to(root):
        return RoleHome(role, datei, BLUEPRINT_ROLES / role / "cases",
                        BLUEPRINT / "holdout" / "roles" / role)
    return RoleHome(role, root / ".sdd" / "roles" / f"{role}.md",
                    root / ".sdd" / "roles" / role / "cases",
                    root / ".sdd" / "holdout" / "roles" / role)


@dataclass(frozen=True)
class Case:
    id: str
    role: str
    dir: Path
    holdout: bool
    data: dict

    @property
    def draft(self) -> bool:
        return bool(self.data.get("draft"))

    @property
    def checks(self) -> list[tuple[str, dict]]:
        return [(name, dict(params or {})) for eintrag in self.data["expect"]["checks"]
                for name, params in eintrag.items()]

    @property
    def rubric(self) -> list[dict]:
        return list(self.data["expect"].get("rubric") or [])

    @property
    def weights(self) -> tuple[float, float]:
        gewichte = self.data.get("weights")
        if gewichte:
            return float(gewichte.get("checks", 0)), float(gewichte.get("rubric", 0))
        return (0.8, 0.2) if self.rubric else (1.0, 0.0)

    @property
    def test_command(self) -> str | None:
        return self.data.get("test_command")

    @property
    def timeout(self) -> int:
        return int(self.data.get("timeout_seconds") or 120)

    def parts(self) -> set[str]:
        return {p for p in PARTS if (self.dir / p).exists()}


def _load(verzeichnis: Path, role: str, holdout: bool) -> Case:
    datei = verzeichnis / CASE_FILE
    try:
        daten = yaml.safe_load(datei.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise CaseError(f"{verzeichnis.name}: {exc}") from exc
    return Case(str(daten.get("id") or verzeichnis.name), role, verzeichnis, holdout, daten)


def case_problems(case: Case) -> list[str]:
    """Fehler eines Falls nach CON-0217; bei Holdout-Fällen ohne Inhalte."""
    fehler = schema_errors("role-case", case.data)
    if fehler:
        return fehler
    if case.data["role"] != case.role:
        fehler.append(f"role ist {case.data['role']!r}, erwartet {case.role!r}")
    if not case.id.startswith(PREFIX.get(case.role, "?") + "-"):
        fehler.append(f"ID {case.id} hat nicht das Präfix {PREFIX.get(case.role)}-")
    if not case.dir.name.startswith(case.id):
        fehler.append(f"Verzeichnis {case.dir.name} passt nicht zur ID {case.id}")
    if not (case.dir / "input").is_dir():
        fehler.append("input/ fehlt")
    gewichte = case.data.get("weights")
    if gewichte and abs(float(gewichte.get("checks", 0)) + float(gewichte.get("rubric", 0))
                        - 1) > 1e-9:
        fehler.append("weights.checks + weights.rubric muss 1 sein")
    vorhanden = case.parts()
    for name, params in case.checks:
        fehler += check_errors(name, params, vorhanden, has_test_command=bool(case.test_command))
    return fehler


def list_cases(home: RoleHome, *, holdout: bool | None = None,
               include_drafts: bool = False) -> list[Case]:
    orte = [(home.cases_dir, False), (home.holdout_dir, True)]
    faelle = []
    for ort, ist_holdout in orte:
        if holdout is not None and holdout != ist_holdout or not ort.is_dir():
            continue
        for verzeichnis in sorted(p for p in ort.iterdir()
                                  if p.is_dir() and (p / CASE_FILE).is_file()):
            fall = _load(verzeichnis, home.role, ist_holdout)
            if include_drafts or not fall.draft:
                faelle.append(fall)
    return faelle


def find_case(home: RoleHome, case_id: str) -> Case:
    for fall in list_cases(home, include_drafts=True):
        if fall.id == case_id:
            return fall
    raise CaseError(f"Fall {case_id} gibt es für {home.role} nicht")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "fall"


def next_case_id(home: RoleHome) -> str:
    praefix = PREFIX[home.role]
    zahlen = [int(m.group(1)) for f in list_cases(home, include_drafts=True)
              if (m := re.match(rf"^{praefix}-(\d+)$", f.id))]
    return f"{praefix}-{max(zahlen, default=0) + 1:03d}"


def new_case(home: RoleHome, title: str, *, holdout: bool, data: dict[str, Any] | None = None,
             inputs: dict[str, str] | None = None) -> Case:
    """Legt einen Fall an (`sdd role case new|capture`); die ID vergibt nur diese Funktion."""
    if home.role not in PREFIX:
        raise CaseError(f"Rolle {home.role!r} hat kein Fall-Präfix")
    case_id = next_case_id(home)
    ziel = (home.holdout_dir if holdout else home.cases_dir) / f"{case_id}-{_slug(title)}"
    (ziel / "input").mkdir(parents=True)
    for rel, inhalt in (inputs or {}).items():
        datei = ziel / "input" / rel
        datei.parent.mkdir(parents=True, exist_ok=True)
        datei.write_text(inhalt, encoding="utf-8")
    daten = {"id": case_id, "role": home.role, "title": title, "origin": "manual",
             "draft": True, "expect": {"checks": [{"json_schema": {}}]}, **(data or {})}
    (ziel / CASE_FILE).write_text(yaml.safe_dump(daten, sort_keys=False, allow_unicode=True),
                                  encoding="utf-8")
    return _load(ziel, home.role, holdout)


def confirm_case(case: Case) -> Case:
    daten = dict(case.data)
    daten.pop("draft", None)
    geprueft = Case(case.id, case.role, case.dir, case.holdout, daten)
    fehler = case_problems(geprueft)
    if fehler:
        raise CaseError(f"{case.id} ist nicht gültig: " + "; ".join(fehler[:5]))
    (case.dir / CASE_FILE).write_text(yaml.safe_dump(daten, sort_keys=False, allow_unicode=True),
                                      encoding="utf-8")
    return geprueft


def install_cases(root: Path) -> list[Path]:
    """Installiert fehlende Blueprint-Fälle ins Projekt (FR-02); vorhandene bleiben unberührt."""
    angelegt = []
    ziele = [(BLUEPRINT_ROLES, root / ".sdd" / "roles", "cases"),
             (BLUEPRINT / "holdout" / "roles", root / ".sdd" / "holdout" / "roles", None)]
    for quelle, ziel, unter in ziele:
        if not quelle.is_dir():
            continue
        for rolle in PREFIX:
            ordner = quelle / rolle / unter if unter else quelle / rolle
            if not ordner.is_dir():
                continue
            for fall in sorted(p for p in ordner.iterdir() if (p / CASE_FILE).is_file()):
                dst = (ziel / rolle / unter if unter else ziel / rolle) / fall.name
                if not dst.exists():
                    shutil.copytree(fall, dst, ignore=shutil.ignore_patterns("__pycache__"))
                    angelegt.append(dst)
    return angelegt


def check_names() -> list[str]:
    return sorted(REGISTRY)
