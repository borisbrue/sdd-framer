"""Implementierungs-Vollständigkeits-Gate (SPEC-0041).

Chain of Responsibility aus ComplianceChecker-Instanzen die strukturelle
Vollständigkeit einer Spec prüfen, bevor finalize/spec_approve durchläuft.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from .frontmatter import Document
from .task_model import Task


# ── Datenmodelle ──────────────────────────────────────────────────────────────

@dataclass
class ComplianceIssue:
    severity: str     # "error" | "warning"
    fr_id: str | None
    message: str
    hint: str = ""


@dataclass
class FrCoverageResult:
    covered: list[str] = field(default_factory=list)
    uncovered: list[str] = field(default_factory=list)


# ── Protokoll ─────────────────────────────────────────────────────────────────

class ComplianceChecker(Protocol):
    def check(self, spec: Document, cfg_raw: dict) -> list[ComplianceIssue]: ...


# ── FR-Extraktion ─────────────────────────────────────────────────────────────

_FR_SECTION_RE = re.compile(
    r"##\s+\d+\.\s+Funktionale Anforderungen\b(.*?)(?=\n##\s|\Z)",
    re.DOTALL | re.IGNORECASE,
)
_FR_ID_RE = re.compile(r"\bFR-\d+\b")


def _extract_fr_ids(body: str) -> list[str]:
    """Extrahiert FR-IDs ausschließlich aus dem Abschnitt 'Funktionale Anforderungen'."""
    match = _FR_SECTION_RE.search(body)
    if not match:
        return []
    ids = _FR_ID_RE.findall(match.group(1))
    return list(dict.fromkeys(ids))  # dedupliziert, reihenfolgestabil


# ── FrCoverageSpecification ───────────────────────────────────────────────────

class FrCoverageSpecification:
    """Specification Pattern: FR-ID → Task.test_ids-Mapping-Regel (CON-0152)."""

    def is_satisfied_by(self, spec: Document, tasks: list[Task]) -> FrCoverageResult:
        if spec.frontmatter.get("status") == "implemented":
            return FrCoverageResult()

        fr_ids = _extract_fr_ids(spec.body)
        if not fr_ids:
            return FrCoverageResult()

        fr_test_map: dict[str, str] = spec.frontmatter.get("fr_test_map") or {}

        covered: list[str] = []
        uncovered: list[str] = []

        for fr in fr_ids:
            if fr in fr_test_map:
                covered.append(fr)
                continue
            task_covers = any(
                fr in t.description and bool(t.test_ids)
                for t in tasks
            )
            if task_covers:
                covered.append(fr)
            else:
                uncovered.append(fr)

        return FrCoverageResult(covered=covered, uncovered=uncovered)


# ── FrCoverageChecker (ComplianceChecker-Wrapper) ────────────────────────────

class FrCoverageChecker:
    """Chain-of-Responsibility-Handler: FR-Abdeckung (FR-01/FR-02)."""

    def __init__(self, tasks: list[Task]) -> None:
        self._tasks = tasks
        self._spec = FrCoverageSpecification()

    def check(self, spec: Document, cfg_raw: dict) -> list[ComplianceIssue]:
        if not (cfg_raw.get("compliance") or {}).get("fr_coverage_check", True):
            return []
        result = self._spec.is_satisfied_by(spec, self._tasks)
        issues = []
        for fr in result.uncovered:
            spec_id = spec.frontmatter.get("id", "SPEC-???")
            issues.append(ComplianceIssue(
                severity="error",
                fr_id=fr,
                message=f"{fr} hat keinen zugeordneten Test",
                hint=(
                    f"Lege einen Test an und trage ihn in "
                    f".sdd/tasks/{spec_id}.json unter test_ids ein, "
                    f"oder nutze fr_test_map im Spec-Frontmatter."
                ),
            ))
        return issues


# ── TypeAwareTestChecker ──────────────────────────────────────────────────────

_TYPE_TAGS = {"webui", "frontend", "api"}
_INTEGRATION_DIRS = {"contract", "integration"}


class TypeAwareTestChecker:
    """Prüft ob Specs mit webui/frontend/api-Tag mind. 1 Integration/Contract-Test haben (FR-03)."""

    def __init__(self, tests_dir: Path) -> None:
        self._tests_dir = tests_dir

    def check(self, spec: Document, cfg_raw: dict) -> list[ComplianceIssue]:
        if not (cfg_raw.get("compliance") or {}).get("type_aware_test_check", True):
            return []

        tags = set(spec.frontmatter.get("tags") or [])
        if not tags & _TYPE_TAGS:
            return []

        test_ids: list[str] = spec.frontmatter.get("tests") or []
        if self._has_qualifying_test(test_ids):
            return []

        spec_id = spec.frontmatter.get("id", "SPEC-???")
        tag_list = ", ".join(sorted(tags & _TYPE_TAGS))
        return [ComplianceIssue(
            severity="error",
            fr_id=None,
            message=(
                f"Spec hat Tag(s) '{tag_list}' aber keinen Test mit "
                f"stufe 'contract' oder 'integration'"
            ),
            hint=(
                f"Lege einen Integration- oder Contract-Test an: "
                f"sdd new test {spec_id} --stufe integration"
            ),
        )]

    def _has_qualifying_test(self, test_ids: list[str]) -> bool:
        for tid in test_ids:
            for sub in _INTEGRATION_DIRS:
                for md in (self._tests_dir / sub).glob("*.md") if (self._tests_dir / sub).exists() else []:
                    if tid in md.name:
                        return True
                # Frontmatter-basierter Fallback
                for md in self._tests_dir.rglob("*.md"):
                    if tid not in md.name:
                        continue
                    text = md.read_text(encoding="utf-8", errors="ignore")
                    if re.search(r"^stufe:\s*(contract|integration)", text, re.MULTILINE):
                        return True
        return False


# ── RouteRegistrationChecker ──────────────────────────────────────────────────

class RouteRegistrationChecker:
    """Prüft ob API-Specs ihre Router in den konfigurierten Entry-Points registriert haben (FR-04)."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root

    def check(self, spec: Document, cfg_raw: dict) -> list[ComplianceIssue]:
        compliance = cfg_raw.get("compliance") or {}
        if not compliance.get("route_registration_check", True):
            return []

        tags = set(spec.frontmatter.get("tags") or [])
        if "api" not in tags:
            return []

        entry_points: list[str] = compliance.get("route_entry_points") or [
            "tool/sdd_cli/web/api/main.py",
            "web/api/main.py",
        ]

        existing = [self._root / ep for ep in entry_points if (self._root / ep).exists()]
        if not existing:
            return []

        for ep_path in existing:
            content = ep_path.read_text(encoding="utf-8", errors="ignore")
            if "include_router" in content:
                return []

        return [ComplianceIssue(
            severity="error",
            fr_id=None,
            message="Spec hat Tag 'api' aber kein include_router in den konfigurierten Entry-Points gefunden",
            hint=(
                f"Prüfe ob dein Router via include_router in einen der "
                f"Entry-Points eingebunden ist: {entry_points}"
            ),
        )]


# ── Checker-Kette ausführen ───────────────────────────────────────────────────

def run_compliance_chain(
    spec: Document,
    tasks: list[Task],
    cfg_raw: dict,
    tests_dir: Path,
    project_root: Path,
) -> list[ComplianceIssue]:
    """Führt die vollständige ComplianceChecker-Kette aus und gibt alle Issues zurück."""
    checkers: list[ComplianceChecker] = [
        FrCoverageChecker(tasks),
        TypeAwareTestChecker(tests_dir),
        RouteRegistrationChecker(project_root),
    ]
    issues: list[ComplianceIssue] = []
    for checker in checkers:
        issues.extend(checker.check(spec, cfg_raw))
    return issues
