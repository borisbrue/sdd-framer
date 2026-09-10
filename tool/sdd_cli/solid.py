"""SOLID-Analyse-Engine – SPEC-0015.

Architekturmuster (SPEC-0015, Abschnitt 3):
  - Strategy:         SolidChecker Protocol – jedes Prinzip austauschbar
  - Chain of Resp.:   SolidAnalyzer führt Checker-Kette aus
  - Null Object:      NullSolidChecker für solid_gate.enabled: false
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .config import SddConfig

PRINCIPLE_LABELS: dict[str, str] = {
    "S": "Single Responsibility",
    "O": "Open/Closed",
    "L": "Liskov Substitution",
    "I": "Interface Segregation",
    "D": "Dependency Inversion",
}

_VALID_SEVERITIES = frozenset({"info", "warn", "violation"})
_VALID_SCORES = frozenset({"compliant", "warn", "violation"})


# ─────────────────────────────────────────────────────────────────────────────
# Data Structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SolidFinding:
    principle: str    # S|O|L|I|D
    severity: str     # info|warn|violation
    location: str
    description: str
    suggestion: str

    def to_dict(self) -> dict:
        return {
            "principle": self.principle,
            "severity": self.severity,
            "location": self.location,
            "description": self.description,
            "suggestion": self.suggestion,
        }


@dataclass
class SolidReport:
    artifact_id: str
    artifact_type: str  # spec|contract
    findings: list[SolidFinding] = field(default_factory=list)
    overall_solid_score: str = "compliant"
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "solid_findings": [f.to_dict() for f in self.findings],
            "overall_solid_score": self.overall_solid_score,
            "summary": self.summary,
        }

    def has_violations(self) -> bool:
        return any(f.severity == "violation" for f in self.findings)

    @property
    def had_llm_error(self) -> bool:
        """True, wenn ein Checker-Fehler (z.B. LLM nicht erreichbar) auftrat.

        Macht eine LLM-Infrastruktur-Störung sichtbar, statt sie als 'compliant'
        zu tarnen (SPEC-0050 / CON-0187).
        """
        return any(f.location == "Checker-Fehler" for f in self.findings)


# ─────────────────────────────────────────────────────────────────────────────
# Strategy: SolidChecker Protocol + Implementations
# ─────────────────────────────────────────────────────────────────────────────

@runtime_checkable
class SolidChecker(Protocol):
    """Strategy-Interface – eine Implementierung prüft genau ein SOLID-Prinzip."""

    principle: str  # S|O|L|I|D

    def check(self, artifact_text: str, artifact_id: str) -> list[SolidFinding]:
        """Analysiert das Artefakt auf das zugehörige Prinzip."""
        ...


class NullSolidChecker:
    """Null Object – gibt immer leere Finding-Liste zurück (solid_gate.enabled: false)."""

    principle = "ALL"

    def check(self, artifact_text: str, artifact_id: str) -> list[SolidFinding]:
        return []


class LlmSolidChecker:
    """LLM-basierter Checker für EIN SOLID-Prinzip (Strategy)."""

    def __init__(self, principle: str, provider: object) -> None:
        if principle not in PRINCIPLE_LABELS:
            raise ValueError(f"Unbekanntes SOLID-Prinzip: {principle!r}")
        self.principle = principle
        self._provider = provider

    def check(self, artifact_text: str, artifact_id: str) -> list[SolidFinding]:
        label = PRINCIPLE_LABELS[self.principle]
        prompt = _build_single_principle_prompt(artifact_text, artifact_id, self.principle, label)
        try:
            result = self._provider.complete(prompt, max_tokens=4096)
            findings, _, _ = _parse_llm_response(result.text)
            return [f for f in findings if f.principle == self.principle] or findings
        except Exception as exc:
            return [_checker_error_finding(self.principle, exc)]


class BatchLlmSolidChecker:
    """Prüft alle 5 Prinzipien in EINEM LLM-Aufruf (Performance < 15 s)."""

    principle = "ALL"

    def __init__(self, provider: object, principle_filter: str | None = None) -> None:
        self._provider = provider
        self._filter = principle_filter

    def check(self, artifact_text: str, artifact_id: str) -> list[SolidFinding]:
        prompt = _build_batch_prompt(artifact_text, artifact_id, self._filter)
        try:
            result = self._provider.complete(prompt, max_tokens=6144)
            findings, _, _ = _parse_llm_response(result.text)
            if self._filter:
                findings = [f for f in findings if f.principle == self._filter]
            return findings
        except Exception as exc:
            return [_checker_error_finding("S", exc)]


# Named factory functions matching the spec's class-alias pattern
def SrpChecker(provider: object) -> LlmSolidChecker:
    return LlmSolidChecker("S", provider)


def OcpChecker(provider: object) -> LlmSolidChecker:
    return LlmSolidChecker("O", provider)


def LspChecker(provider: object) -> LlmSolidChecker:
    return LlmSolidChecker("L", provider)


def IspChecker(provider: object) -> LlmSolidChecker:
    return LlmSolidChecker("I", provider)


def DipChecker(provider: object) -> LlmSolidChecker:
    return LlmSolidChecker("D", provider)


# ─────────────────────────────────────────────────────────────────────────────
# Chain of Responsibility: SolidAnalyzer
# ─────────────────────────────────────────────────────────────────────────────

class SolidAnalyzer:
    """Orchestriert eine geordnete Liste von SolidChecker-Instanzen.

    Implementiert Chain of Responsibility: jeder Checker kann Findings hinzufügen,
    ein Checker-Fehler unterbricht die Kette nicht (CON-0045 INV-04).
    """

    def __init__(self, checkers: list[object]) -> None:
        self._checkers = checkers

    def analyze(
        self,
        artifact_text: str,
        artifact_id: str,
        artifact_type: str = "spec",
    ) -> SolidReport:
        all_findings: list[SolidFinding] = []
        for checker in self._checkers:
            try:
                findings = checker.check(artifact_text, artifact_id)
                all_findings.extend(findings)
            except Exception as exc:
                principle = getattr(checker, "principle", "S")
                if principle == "ALL":
                    principle = "S"
                all_findings.append(_checker_error_finding(principle, exc))

        score = _compute_score(all_findings)
        return SolidReport(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            findings=all_findings,
            overall_solid_score=score,
            summary=_build_summary(all_findings, score),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────────────────────────────────────

def create_analyzer(config: SddConfig, principle_filter: str | None = None) -> SolidAnalyzer:
    """Erstellt den konfigurierten SolidAnalyzer aus der Projektkonfiguration."""
    if not config.solid_gate_enabled():
        return SolidAnalyzer([NullSolidChecker()])

    from .llm.factory import get_completion_provider
    provider = get_completion_provider(config, "completion")

    if principle_filter and principle_filter in PRINCIPLE_LABELS:
        checker: object = LlmSolidChecker(principle_filter, provider)
    else:
        checker = BatchLlmSolidChecker(provider, principle_filter=principle_filter)

    return SolidAnalyzer([checker])


# ─────────────────────────────────────────────────────────────────────────────
# Artifact Discovery
# ─────────────────────────────────────────────────────────────────────────────

def find_artifact(config: SddConfig, artifact_id: str) -> tuple[str, str] | None:
    """Sucht Spec oder Contract nach ID. Gibt (text, artifact_type) oder None zurück."""
    from .frontmatter import parse_safe

    for md in _iter_docs(config.specs_dir):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == artifact_id:
            return md.read_text(encoding="utf-8"), "spec"

    for md in _iter_docs(config.contracts_dir):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == artifact_id:
            return md.read_text(encoding="utf-8"), "contract"

    return None


def _iter_docs(base: Path):
    if base.exists():
        yield from sorted(base.rglob("*.md"))


# ─────────────────────────────────────────────────────────────────────────────
# Prompt Construction
# ─────────────────────────────────────────────────────────────────────────────

def _build_batch_prompt(text: str, artifact_id: str, principle_filter: str | None) -> str:
    if principle_filter and principle_filter in PRINCIPLE_LABELS:
        scope = (
            f"nur Prinzip '{principle_filter}' "
            f"({PRINCIPLE_LABELS[principle_filter]})"
        )
    else:
        scope = "alle 5 SOLID-Prinzipien (S, O, L, I, D)"

    return (
        "Du bist ein Software-Architekt der SOLID-Prinzipien auf Spezifikations- und "
        "Contract-Ebene prüft (kein Code-Review).\n"
        f"Analysiere das folgende Artefakt auf {scope}.\n"
        "Für jedes Finding: zitiere den konkreten Abschnitt, der das Problem verursacht.\n"
        "Schlage eine konkrete Verbesserung vor.\n"
        "Wenn du keine Verletzung erkennst, gib eine leere findings-Liste aus.\n\n"
        f"ARTEFAKT-TYP: spec oder contract\n"
        f"ARTEFAKT-ID: {artifact_id}\n"
        "INHALT:\n"
        f"{text}\n\n"
        "Antworte AUSSCHLIESSLICH als valides JSON (kein Markdown, kein Text davor/danach):\n"
        "{\n"
        '  "solid_findings": [\n'
        '    {\n'
        '      "principle": "S|O|L|I|D",\n'
        '      "severity": "info|warn|violation",\n'
        '      "location": "Abschnitt/Zeile im Artefakt",\n'
        '      "description": "Was genau verletzt wird",\n'
        '      "suggestion": "Konkrete Verbesserung"\n'
        '    }\n'
        '  ],\n'
        '  "overall_solid_score": "compliant|warn|violation",\n'
        '  "summary": "Ein-Satz-Zusammenfassung"\n'
        "}"
    )


def _build_single_principle_prompt(text: str, artifact_id: str, principle: str, label: str) -> str:
    return (
        f"Du bist ein Software-Architekt. Prüfe das Artefakt auf SOLID-Prinzip "
        f"'{principle}' ({label}) auf Spezifikations- und Contract-Ebene.\n\n"
        f"ARTEFAKT-ID: {artifact_id}\n"
        "INHALT:\n"
        f"{text}\n\n"
        "Antworte AUSSCHLIESSLICH als valides JSON:\n"
        '{"solid_findings": [{"principle": "' + principle + '", '
        '"severity": "info|warn|violation", "location": "...", '
        '"description": "...", "suggestion": "..."}], '
        '"overall_solid_score": "compliant|warn|violation", "summary": "..."}'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Response Parsing
# ─────────────────────────────────────────────────────────────────────────────

class SolidResponseError(RuntimeError):
    """Die LLM-Antwort war nicht als JSON auswertbar.

    Fliegt statt eines leeren Ergebnisses: vorher gab _parse_llm_response bei
    unparsbarer Antwort `[], "compliant", ...` zurueck. Ohne Findings entstand
    kein Checker-Fehler-Eintrag, SolidReport.had_llm_error blieb False, und die
    Warnung in der CLI feuerte nicht — eine Antwort, die das Modell gar nicht
    auswertbar geliefert hatte, erschien als bestandene Pruefung.

    Die Aufrufer fangen sie in ihrem bestehenden `except Exception` ab und
    erzeugen daraus ein Finding mit severity `info` — genau der Weg, den
    CON-0045 INV-04 fuer Checker-Fehler vorsieht.
    """


def _parse_llm_response(text: str) -> tuple[list[SolidFinding], str, str]:
    """Parst LLM-Antwort → (findings, overall_solid_score, summary).

    Wirft SolidResponseError, wenn die Antwort kein JSON enthaelt.
    """
    cleaned = _extract_json(text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise SolidResponseError(
            f"Antwort nicht als JSON parsebar ({exc.msg}, Position {exc.pos}); "
            f"{len(text)} Zeichen empfangen"
        ) from exc

    findings: list[SolidFinding] = []
    for item in data.get("solid_findings", []):
        principle = str(item.get("principle", "")).upper()
        if principle not in PRINCIPLE_LABELS:
            continue
        severity = str(item.get("severity", "info")).lower()
        if severity not in _VALID_SEVERITIES:
            severity = "info"
        findings.append(SolidFinding(
            principle=principle,
            severity=severity,
            location=str(item.get("location", "")).strip(),
            description=str(item.get("description", "")).strip(),
            suggestion=str(item.get("suggestion", "")).strip(),
        ))

    score = str(data.get("overall_solid_score", "")).lower()
    if score not in _VALID_SCORES:
        score = _compute_score(findings)

    summary = str(data.get("summary", "")).strip()
    return findings, score, summary


def _extract_json(text: str) -> str:
    """Extrahiert JSON aus LLM-Antwort (entfernt Markdown-Code-Blöcke)."""
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r"(\{.*\})", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Score & Summary Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _compute_score(findings: list[SolidFinding]) -> str:
    severities = {f.severity for f in findings}
    if "violation" in severities:
        return "violation"
    if "warn" in severities:
        return "warn"
    return "compliant"


def _build_summary(findings: list[SolidFinding], score: str) -> str:
    if score == "compliant":
        return "Kein SOLID-Verstoß erkannt."
    violations = sum(1 for f in findings if f.severity == "violation")
    warns = sum(1 for f in findings if f.severity == "warn")
    parts = []
    if violations:
        parts.append(f"{violations} Violation(s)")
    if warns:
        parts.append(f"{warns} Warnung(en)")
    return f"SOLID-Analyse: {', '.join(parts)} gefunden." if parts else "Analyse abgeschlossen."


def _checker_error_finding(principle: str, exc: Exception) -> SolidFinding:
    return SolidFinding(
        principle=principle,
        severity="info",
        location="Checker-Fehler",
        description=f"Checker-Fehler bei Prinzip {principle}: {exc}",
        suggestion="Checker-Konfiguration prüfen oder manuell analysieren.",
    )
