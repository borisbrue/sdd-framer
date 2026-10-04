"""Kontextquellen und Testsonde für Rollenaufrufe (SPEC-0053 FR-03, FR-10).

Quellen stammen nur aus der geschlossenen Liste in `roles.CONTEXT_SOURCES`. `.sdd/holdout/` wird
nie gelesen: die Dateiliste schließt `.sdd/` vollständig aus, Contracts kommen nur aus den
Verweisen der Spec.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from ..compliance import extract_fr_ids
from ..frontmatter import parse_safe
from ..quality.files import collect_files
from ..quality.parsers import TestCase, TestSuiteResult

REPO_MAP_LIMIT = 400


class ContextError(Exception):
    """Spec oder Projektdatei fehlt."""


@dataclass
class ProbeResult:
    """Ergebnis der Testsonde: Testfälle oder ein Grund, warum es keine gibt."""
    cases: list[TestCase]
    reason: str | None = None

    @property
    def ok(self) -> bool:
        return self.reason is None

    def for_file(self, test_file: str) -> list[TestCase]:
        stamm = Path(test_file).name.split(".")[0]
        return [c for c in self.cases
                if (c.file and Path(c.file).as_posix().removeprefix("./") == test_file)
                or (not c.file and stamm and stamm in f"{c.classname}.{c.name}")]

    def failing(self) -> list[TestCase]:
        return [c for c in self.cases if c.status in ("failed", "error")]

    def summary(self) -> dict:
        if not self.ok:
            return {"probe": "tests", "status": "n/a", "reason": self.reason}
        return {"probe": "tests", "status": "ok", "tests": len(self.cases),
                "failed": [f"{c.classname}.{c.name}" for c in self.failing()]}


class ProjectContext:
    def __init__(self, root: Path, spec_id: str) -> None:
        self.root = root
        self.spec_id = spec_id

    @cached_property
    def spec_path(self) -> Path:
        for md in sorted((self.root / ".sdd" / "specs").rglob("*.md")):
            doc = parse_safe(md)
            if doc and doc.frontmatter.get("id") == self.spec_id:
                return md
        raise ContextError(f"Spec {self.spec_id} nicht gefunden")

    @cached_property
    def spec_doc(self):
        doc = parse_safe(self.spec_path)
        if doc is None:
            raise ContextError(f"Spec {self.spec_id} ist nicht lesbar")
        return doc

    @property
    def status(self) -> str:
        return str(self.spec_doc.frontmatter.get("status") or "")

    @cached_property
    def spec_text(self) -> str:
        return self.spec_path.read_text(encoding="utf-8")

    @cached_property
    def spec_frs(self) -> list[str]:
        return extract_fr_ids(self.spec_doc.body)

    @cached_property
    def contracts_text(self) -> str:
        teile = []
        for con_id in self.spec_doc.frontmatter.get("contracts") or []:
            for md in sorted((self.root / ".sdd" / "contracts").rglob(f"{con_id}-*.md")):
                teile.append(md.read_text(encoding="utf-8"))
                doc = parse_safe(md)
                artefakt = doc.frontmatter.get("artifact") if doc else None
                if artefakt and "<" not in str(artefakt):
                    pfad = self.root / str(artefakt)
                    if pfad.is_file() and ".sdd/holdout" not in pfad.as_posix():
                        teile.append(f"### {artefakt}\n\n{pfad.read_text(encoding='utf-8')}")
        return "\n\n".join(teile)

    @cached_property
    def agents_md(self) -> str:
        pfad = self.root / "AGENTS.md"
        return pfad.read_text(encoding="utf-8") if pfad.is_file() else ""

    def repo_map(self) -> str:
        dateien = collect_files(self.root, ["**"], [])
        rest = len(dateien) - REPO_MAP_LIMIT
        zeilen = dateien[:REPO_MAP_LIMIT]
        if rest > 0:
            zeilen.append(f"… {rest} weitere Dateien")
        return "\n".join(zeilen)

    def current_files(self, patterns: list[str], exclude: list[str]) -> str:
        """Inhalt der vorhandenen Dateien, die auf `patterns` passen (HF-0012).

        Für den Implementer: Er liefert Dateien vollständig und muss dafür ihren aktuellen Stand
        kennen. `.sdd/` (und damit Holdouts) und die Testdatei des Tasks gehören nie dazu."""
        dateien = collect_files(self.root, list(patterns),
                                [".sdd/**", "**/holdout/**", *exclude])
        teile = []
        for rel in dateien:
            try:
                inhalt = (self.root / rel).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            teile.append(f"### {rel}\n\n```\n{inhalt}\n```")
        return "\n\n".join(teile)

    def dependency_api(self, tasks: list[dict]) -> str:
        """Öffentliche Schnittstellen der Dateien erledigter Abhängigkeiten (SPEC-0065 FR-02).

        Je vorhandene Datei aus den `allowed_paths` der übergebenen Tasks die Signaturen ohne
        Rümpfe; was öffentlich ist, entscheidet der Extraktor (`signatures`). Testdateien,
        `.sdd/` und Holdouts gehören nie dazu."""
        from .signatures import api_of

        teile, gesehen = [], set()
        for task in tasks:
            tests = [task["test_file"]] if task.get("test_file") else []
            for rel in collect_files(self.root, list(task.get("allowed_paths") or []),
                                     [".sdd/**", "**/holdout/**", *tests]):
                if rel in gesehen:
                    continue
                gesehen.add(rel)
                try:
                    inhalt = (self.root / rel).read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    inhalt = None
                api = api_of(rel, inhalt) if inhalt is not None else "(Datei nicht lesbar)"
                kopf = f"### {rel} ({task.get('id', '?')} {task.get('title', '')})".rstrip()
                teile.append(f"{kopf}\n\n```\n{api}\n```")
        return "\n\n".join(teile)

    def read(self, rel: str) -> str | None:
        pfad = self.root / rel
        return pfad.read_text(encoding="utf-8") if pfad.is_file() else None

    def is_git_repo(self) -> bool:
        try:
            r = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=self.root,
                               capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            return False
        return r.returncode == 0 and r.stdout.strip() == "true"

    # ── Testsonde (SPEC-0054) ──
    def run_tests(self) -> ProbeResult:
        from ..quality.config import QualityConfigError, load_quality_config
        from ..quality.probe import ProbeRun

        try:
            qcfg = load_quality_config(self.root)
        except FileNotFoundError:
            return ProbeResult([], "keine .sdd/quality.yaml – Testsonde fehlt")
        except QualityConfigError as exc:
            return ProbeResult([], f"quality.yaml ungültig: {exc}")
        probe = qcfg.probe_for_role("tests")
        if probe is None:
            return ProbeResult([], "keine Sonde mit role: tests in .sdd/quality.yaml")
        outcome = ProbeRun(self.root, []).execute(probe)
        if not outcome.ok or not isinstance(outcome.result, TestSuiteResult):
            return ProbeResult([], outcome.reason or "Testsonde ohne JUnit-Ergebnis")
        return ProbeResult(list(outcome.result.cases))

    def fr_status(self, probe: ProbeResult) -> list[dict]:
        """Je FR der Spec: zugeordnete Tests und ob sie grün sind (Fakten für S3)."""
        ergebnis = []
        for fr in self.spec_frs:
            faelle = [c for c in probe.cases if fr in c.frs]
            if not faelle:
                status = "ohne Test"
            elif all(c.status == "passed" for c in faelle):
                status = "grün"
            else:
                status = "rot"
            ergebnis.append({"id": fr, "status": status,
                             "tests": [c.file or f"{c.classname}.{c.name}" for c in faelle]})
        return ergebnis
