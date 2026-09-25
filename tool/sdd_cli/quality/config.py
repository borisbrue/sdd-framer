"""Laden und Prüfen von `.sdd/quality.yaml` (SPEC-0054 FR-01, CON-0192)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .schemas import error_path, validator

QUALITY_FILE = Path(".sdd") / "quality.yaml"
ROLES = ("tests", "deps")
DEFAULT_TIMEOUT = 600


@dataclass(frozen=True)
class Probe:
    name: str
    command: str
    format: str
    role: str | None = None
    metric: str | None = None
    fr_marker: str | None = None
    diff_scoped: bool = False
    timeout_seconds: int = DEFAULT_TIMEOUT
    version_command: str | None = None


@dataclass(frozen=True)
class Normalization:
    good: float
    bad: float


@dataclass
class QualityConfig:
    probes: list[Probe]
    normalization: dict[str, Normalization] = field(default_factory=dict)
    suppressions: dict[str, list[str]] = field(default_factory=dict)
    paths: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    test_paths: list[str] = field(default_factory=list)
    preset: str | None = None

    def probe_for_role(self, role: str) -> Probe | None:
        return next((p for p in self.probes if p.role == role), None)


@dataclass(frozen=True)
class ConfigProblem:
    path: str
    message: str


class QualityConfigError(Exception):
    def __init__(self, problems: list[ConfigProblem]) -> None:
        self.problems = problems
        super().__init__("; ".join(f"{p.path}: {p.message}" for p in problems))


def check_quality_config(raw: object) -> list[ConfigProblem]:
    """Schemaprüfung plus die Regeln, die das Schema nicht ausdrücken kann."""
    problems = [
        ConfigProblem(error_path(e), e.message)
        for e in sorted(validator("quality-config").iter_errors(raw), key=lambda e: list(e.path))
    ]
    if problems or not isinstance(raw, dict):
        return problems
    for role in ROLES:
        namen = [n for n, p in raw["probes"].items() if p.get("role") == role]
        if len(namen) > 1:
            problems.append(ConfigProblem(
                "probes", f"Rolle {role!r} ist mehrfach vergeben: {', '.join(namen)}"))
    for name, grenzen in (raw.get("normalization") or {}).items():
        if grenzen["good"] == grenzen["bad"]:
            problems.append(ConfigProblem(
                f"normalization.{name}", "good und bad dürfen nicht gleich sein"))
    return problems


def parse_quality_config(raw: dict) -> QualityConfig:
    problems = check_quality_config(raw)
    if problems:
        raise QualityConfigError(problems)
    return QualityConfig(
        probes=[Probe(name=n, **p) for n, p in raw["probes"].items()],
        normalization={k: Normalization(float(v["good"]), float(v["bad"]))
                       for k, v in (raw.get("normalization") or {}).items()},
        suppressions=dict(raw.get("suppressions") or {}),
        paths=list(raw.get("paths") or []),
        exclude=list(raw.get("exclude") or []),
        test_paths=list(raw.get("test_paths") or []),
        preset=raw.get("preset"),
    )


def load_quality_config(root: Path) -> QualityConfig:
    """Lädt `.sdd/quality.yaml`. FileNotFoundError, wenn sie fehlt; QualityConfigError, wenn ungültig."""
    pfad = root / QUALITY_FILE
    if not pfad.is_file():
        raise FileNotFoundError(pfad)
    try:
        raw = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise QualityConfigError([ConfigProblem("(Datei)", f"kein gültiges YAML: {exc}")]) from exc
    return parse_quality_config(raw)
