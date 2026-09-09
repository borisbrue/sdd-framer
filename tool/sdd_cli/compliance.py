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
# Eine FR gilt als deklariert, wenn ihre ID am Zeilenanfang steht — nach
# optionalem Listenmarker und optionaler Fettung. Im Bestand kommen fuenf
# Schreibweisen vor, alle mit der ID am Zeilenanfang:
#
#     - **FR-01:**    **FR-01**    - **FR-01**    - **FR-01:    - FR-01:
#
# Vorher stand hier \bFR-\d+\b ueber den ganzen Abschnitt. Damit zaehlte jede
# Nennung als eigene Anforderung, auch ein Querverweis im Fliesstext:
#
#     `NotificationContext` … aus SPEC-0016 (FR-18–FR-20) als In-App-Kanal
#
# `sdd spec approve` brach daran mit "FR-24 hat keinen zugeordneten Test" ab,
# obwohl die Spec nur 23 Anforderungen hatte. Jeder Verweis auf eine fremde
# Spec wurde so zum Fehler — obwohl genau solche Verweise das sind, was der
# Regression-Check einfordert.
_FR_ID_RE = re.compile(r"^[ \t]*(?:[-*+][ \t]*)?(?:\*\*)?(FR-\d+)\b", re.MULTILINE)


def _extract_fr_ids(body: str) -> list[str]:
    """Extrahiert deklarierte FR-IDs aus dem Abschnitt 'Funktionale Anforderungen'.

    Querverweise auf FRs anderer Specs zaehlen nicht mit: sie stehen im
    Fliesstext, nicht am Zeilenanfang.
    """
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

# ── TaskCompletionChecker ─────────────────────────────────────────────────────
#
# Das Gate prueft die FR->Test-Abdeckung, aber nicht, ob die Tasks der Spec
# tatsaechlich abgeschlossen sind. `sdd finalize` schaltete deshalb auf
# `implemented`, obwohl saemtliche Tasks auf `pending` standen — gemessen an
# SPEC-0050 mit 7 offenen Tasks und 0 Issues.
#
# task_lifecycle definiert COMMITTED als einzigen Zustand ohne ausgehende
# Uebergaenge. PASSED zaehlt hier mit: finalize committet selbst, ein zu diesem
# Zeitpunkt bestandener Task ist also erledigte Arbeit.

_DONE_STATUSES = {"committed", "passed"}


@dataclass
class TaskCompletionResult:
    done: list[str] = field(default_factory=list)
    open_: list[tuple[str, str]] = field(default_factory=list)  # (titel, status)
    decomposed: bool = True


class TaskCompletionSpecification:
    """Specification Pattern: alle Tasks der Spec muessen abgeschlossen sein."""

    def is_satisfied_by(self, spec: Document, tasks: list[Task]) -> TaskCompletionResult:
        if spec.frontmatter.get("status") == "implemented":
            # Wie bei FrCoverage: eine bereits abgeschlossene Spec wird nicht
            # ruecklaeufig blockiert.
            return TaskCompletionResult()
        if not tasks:
            return TaskCompletionResult(decomposed=False)

        result = TaskCompletionResult()
        for t in tasks:
            status = getattr(t.status, "value", t.status)
            if str(status) in _DONE_STATUSES:
                result.done.append(t.title)
            else:
                result.open_.append((t.title, str(status)))
        return result


class TaskCompletionChecker:
    """Chain-of-Responsibility-Handler: Task-Status (Issue #34).

    `strict` trennt Gate von Bericht: `sdd finalize` und `sdd spec approve`
    entscheiden ueber einen Statuswechsel und blockieren deshalb (error);
    `sdd validate` ist ein Gesundheitsbericht und meldet dasselbe als Warnung.

    Ohne diese Trennung faellt `sdd validate` im eigenen Repo mit 18 Fehlern aus
    — SPEC-0049 steht auf in-progress mit 9 offenen Tasks, obwohl die Arbeit
    laengst gemerged ist. Ein Werkzeug, das wegen veralteter Buchfuehrung nicht
    mehr durchlaeuft, waere schlimmer als die Buchfuehrung selbst.
    """

    def __init__(self, tasks: list[Task], strict: bool = False) -> None:
        self._tasks = tasks
        self._strict = strict
        self._spec = TaskCompletionSpecification()

    def check(self, spec: Document, cfg_raw: dict) -> list[ComplianceIssue]:
        if not (cfg_raw.get("compliance") or {}).get("task_completion_check", True):
            return []

        spec_id = spec.frontmatter.get("id", "SPEC-???")
        result = self._spec.is_satisfied_by(spec, self._tasks)

        if not result.decomposed:
            # Bewusst nur eine Warnung: in diesem Repo haben 46 von 48
            # implemented-Specs gar keine Task-Datei. Ein Fehler wuerde finalize
            # praktisch ueberall blockieren, obwohl die Arbeit ueber PRs lief.
            # Sichtbar muss die Luecke trotzdem sein — sonst prueft die Regel
            # genau dort nicht, wo nie dekomponiert wurde.
            return [ComplianceIssue(
                severity="warning",
                fr_id=None,
                message=f"{spec_id}: keine Tasks dekomponiert – Task-Status ungeprueft",
                hint=f"Erwartet unter .sdd/tasks/{spec_id}.json (sdd decompose).",
            )]

        issues: list[ComplianceIssue] = []
        for title, status in result.open_:
            issues.append(ComplianceIssue(
                severity="error" if self._strict else "warning",
                fr_id=None,
                message=f"Task nicht abgeschlossen ({status}): {title[:70]}",
                hint=(
                    f"Alle Tasks in .sdd/tasks/{spec_id}.json muessen "
                    f"{' oder '.join(sorted(_DONE_STATUSES))} sein, bevor die Spec "
                    f"als implementiert gilt."
                ),
            ))
        return issues


def run_compliance_chain(
    spec: Document,
    tasks: list[Task],
    cfg_raw: dict,
    tests_dir: Path,
    project_root: Path,
    strict: bool = False,
) -> list[ComplianceIssue]:
    """Führt die vollständige ComplianceChecker-Kette aus und gibt alle Issues zurück.

    strict=True fuer Aufrufer, die ueber einen Statuswechsel entscheiden
    (finalize, spec approve). strict=False fuer berichtende Aufrufer (validate).
    """
    checkers: list[ComplianceChecker] = [
        FrCoverageChecker(tasks),
        TaskCompletionChecker(tasks, strict=strict),
        TypeAwareTestChecker(tests_dir),
        RouteRegistrationChecker(project_root),
    ]
    issues: list[ComplianceIssue] = []
    for checker in checkers:
        issues.extend(checker.check(spec, cfg_raw))
    return issues
