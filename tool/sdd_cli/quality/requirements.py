"""Anforderungserfüllung (SPEC-0054 FR-03/FR-04, CON-0195, CON-0196).

Je FR werden die Testfälle aus `fr_test_map`, `Task.fr_ids` und den FR-Markierungen im
JUnit-Ergebnis zusammengeführt. Der Status beruht auf ausgeführten Tests.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..compliance import extract_fr_ids
from ..frontmatter import parse_safe
from .parsers import TestCase
from .score import MetricLeaf, ScoreNode
from .settings import QualitySettings

TST_RE = re.compile(r"^TST-\d+$")
REASON_NO_FR = "Spec ohne FR"


@dataclass
class FrResult:
    id: str
    status: str
    tests: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"id": self.id, "status": self.status, "tests": self.tests}


@dataclass
class RequirementsResult:
    node: ScoreNode
    frs: list[FrResult]
    holdout_rate: float | None
    holdout_reason: str | None = None


def find_spec(root: Path, spec_id: str):
    for md in sorted((root / ".sdd" / "specs").rglob(f"{spec_id}-*.md")):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == spec_id:
            return doc
    return None


def _tst_artifact(root: Path, tst_id: str) -> str | None:
    for md in (root / ".sdd" / "tests").rglob(f"{tst_id}-*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == tst_id:
            return str(doc.frontmatter.get("artifact") or "").strip() or None
    return None


def _in_datei(case: TestCase, datei: str) -> bool:
    if case.file:
        return case.file == datei
    modul = datei.removesuffix(".py").replace("/", ".")
    return case.classname == modul or case.classname.startswith(modul + ".")


def _task_zuordnung(root: Path, spec_id: str) -> dict[str, list[str]]:
    pfad = root / ".sdd" / "tasks" / f"{spec_id}.json"
    try:
        tasks = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    zuordnung: dict[str, list[str]] = {}
    for t in tasks if isinstance(tasks, list) else []:
        for fr in t.get("fr_ids") or []:
            if t.get("test_file"):
                zuordnung.setdefault(fr, []).append(t["test_file"])
    return zuordnung


def _status(tests: list[dict]) -> str:
    relevant = [t["status"] for t in tests if t["status"] != "skipped"]
    gruen = sum(1 for s in relevant if s == "passed")
    if gruen == 0:
        return "fehlt"
    return "erfüllt" if gruen == len(relevant) else "teilweise"


def _tests_fuer(fr: str, cases: list[TestCase], fr_map: dict, task_map: dict, root: Path,
                marker_source: str) -> list[dict]:
    tests: list[dict] = []
    gesehen: set[str] = set()

    def add(name: str, status: str, source: str) -> None:
        if name not in gesehen:
            gesehen.add(name)
            tests.append({"name": name, "status": status, "source": source})

    for eintrag in fr_map.get(fr) or []:
        eintrag = str(eintrag)
        if TST_RE.match(eintrag):
            datei = _tst_artifact(root, eintrag)
            passende = [c for c in cases if datei and _in_datei(c, datei)]
            for c in passende:
                add(c.name, c.status, "fr_test_map")
            if not passende:
                add(eintrag, "not_run", "fr_test_map")
        else:
            treffer = [c for c in cases if c.name == eintrag]
            for c in treffer:
                add(c.name, c.status, "fr_test_map")
            if not treffer:
                add(eintrag, "not_run", "fr_test_map")
    for datei in task_map.get(fr) or []:
        for c in cases:
            if _in_datei(c, datei):
                add(c.name, c.status, "task_fr_ids")
    for c in cases:
        if fr in c.frs:
            add(c.name, c.status, marker_source)
    return tests


def holdout_pass_rate(root: Path, contracts: list[str]) -> float | None:
    """Jüngste gültige Evaluator-Datei mit Szenarien der Contracts; skip/error zählen nicht."""
    if not contracts:
        return None
    verzeichnis = root / ".sdd" / "evaluations"
    for datei in sorted(verzeichnis.glob("*.json"), reverse=True) if verzeichnis.is_dir() else []:
        try:
            daten = json.loads(datei.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        bestanden = gewertet = 0
        for s in daten.get("scenarios") or [] if isinstance(daten, dict) else []:
            if s.get("contract") not in contracts:
                continue
            urteile = [r.get("llm_verdict") for r in s.get("runs") or []]
            if "skip" in urteile or (urteile and all(u == "error" for u in urteile)):
                continue
            gewertet += 1
            bestanden += bool(s.get("passed"))
        if gewertet:
            return bestanden / gewertet
    return None


def evaluate_requirements(root: Path, spec_id: str, cases: list[TestCase] | None, *,
                          fr_marker: str | None, settings: QualitySettings,
                          na_reason: str | None = None) -> RequirementsResult:
    doc = find_spec(root, spec_id)
    fr_ids = extract_fr_ids(doc.body) if doc else []
    fm = doc.frontmatter if doc else {}
    marker_source = "junit_name" if fr_marker == "name" else "junit_property"
    if cases is None:
        frs = [FrResult(fr, "unbekannt") for fr in fr_ids]
    else:
        fr_map, task_map = fm.get("fr_test_map") or {}, _task_zuordnung(root, spec_id)
        frs = []
        for fr in fr_ids:
            tests = _tests_fuer(fr, cases, fr_map, task_map, root, marker_source)
            frs.append(FrResult(fr, _status(tests), tests))

    if not fr_ids:
        anteil, grund = None, REASON_NO_FR if doc else f"Spec {spec_id} nicht gefunden"
    elif cases is None:
        anteil, grund = None, f"Testsonde ausgefallen: {na_reason or 'kein Ergebnis'}"
    else:
        anteil, grund = sum(f.status == "erfüllt" for f in frs) / len(frs), None

    rate = holdout_pass_rate(root, list(fm.get("contracts") or []))
    h = settings.holdout_weight
    kinder = [MetricLeaf("fr_fulfilled", anteil, anteil, weight=(1 - h) if rate is not None else 1.0,
                         good=1.0, bad=0.0, reason=grund)]
    if rate is not None:
        kinder.append(MetricLeaf("holdout_pass_rate", rate, rate, weight=h, good=1.0, bad=0.0))
    node = ScoreNode("requirements", settings.root_weights["requirements"], kinder,
                     policy="strict")
    return RequirementsResult(node, frs, rate,
                              None if rate is not None else "keine gültige Holdout-Auswertung")
