"""RoleRunner: ein Rollenaufruf nach festem Ablauf (SPEC-0053 FR-06, Template Method).

Kontext zusammenstellen → Prompt mit Nonce rendern → LLM im Usage-Kontext aufrufen → Ausgabe
extrahieren → gegen das Ausgabeschema validieren → Rollen-Checks. Ungültige Ausgaben sind ein
gezählter Fehlversuch (`invalid_output`), kein Absturz. Ein Längenabbruch ohne verwertbaren Inhalt
wird genau einmal mit dem 1,5-fachen Ausgabebudget wiederholt (CON-0205 INV-06).
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from ..llm.base import UsageMetadata
from ..llm.usage import usage_context
from .roles import CONTEXT_SOURCES, RoleDefinition
from .schemas import errors as schema_errors

log = logging.getLogger(__name__)

CHARS_PER_TOKEN = 4
DEFAULT_MAX_OUTPUT = 8000
SOURCE_TITLES = {
    "spec": "Spec", "contracts": "Contracts", "agents_md": "AGENTS.md", "repo_map": "Dateien",
    "task": "Task", "test_file": "Testdatei", "test_output": "Testausgabe", "diff": "Diff",
    "gate_results": "Gate-Ergebnisse", "review": "Review", "history": "history",
}


@dataclass
class RoleResult:
    role: str
    call_id: str
    attempt: int
    outcome: str  # ok | invalid_output | error (gate_failed/rejected setzt der Mediator)
    output: Any = None
    usage: UsageMetadata | None = None
    problems: list[str] = field(default_factory=list)
    prompt_hash: str = ""
    raw: str = ""

    @property
    def ok(self) -> bool:
        return self.outcome == "ok"


# ── Rollen-Checks: prüfen nur die Ausgabe der Rolle (CON-0199 INV-03) ─────────

Check = Callable[[Any, Mapping], list[str]]


def _check_fr_coverage(output: Any, ctx: Mapping) -> list[str]:
    abgedeckt = {fr for t in output.get("tasks", []) for fr in t.get("fr_ids", [])}
    return [f"{fr} ist von keinem Task abgedeckt" for fr in ctx.get("spec_frs", [])
            if fr not in abgedeckt]


def _check_deps_resolvable(output: Any, ctx: Mapping) -> list[str]:
    titel = {t["title"] for t in output.get("tasks", [])}
    return [f"Task {t['title']!r}: Abhängigkeit {d!r} existiert nicht"
            for t in output.get("tasks", []) for d in t.get("dependencies", []) if d not in titel]


def _check_acyclic(output: Any, ctx: Mapping) -> list[str]:
    kanten = {t["title"]: list(t.get("dependencies", [])) for t in output.get("tasks", [])}
    zustand: dict[str, int] = {}

    def zyklisch(knoten: str) -> bool:
        if zustand.get(knoten) == 1:
            return True
        if zustand.get(knoten) == 2 or knoten not in kanten:
            return False
        zustand[knoten] = 1
        if any(zyklisch(n) for n in kanten[knoten]):
            return True
        zustand[knoten] = 2
        return False

    return ["Die Abhängigkeiten der Tasks enthalten einen Zyklus"] if any(
        zyklisch(k) for k in kanten) else []


def _check_test_file_per_code_task(output: Any, ctx: Mapping) -> list[str]:
    gesehen: dict[str, str] = {}
    probleme = []
    for t in output.get("tasks", []):
        datei = t.get("test_file")
        if t.get("type") == "code" and datei:
            if datei in gesehen:
                probleme.append(f"Tasks {gesehen[datei]!r} und {t['title']!r} teilen die "
                                f"Testdatei {datei}")
            gesehen[datei] = t["title"]
    return probleme


def _check_test_file_matches_task(output: Any, ctx: Mapping) -> list[str]:
    erwartet = (ctx.get("task") or {}).get("test_file")
    if erwartet and output.get("test_file") != erwartet:
        return [f"test_file muss {erwartet} sein, nicht {output.get('test_file')}"]
    return []


CHECKS: dict[str, Check] = {
    "json_schema": lambda output, ctx: [],  # läuft immer vorab, s. RoleRunner._validate
    "fr_coverage": _check_fr_coverage,
    "acyclic": _check_acyclic,
    "deps_resolvable": _check_deps_resolvable,
    "test_file_per_code_task": _check_test_file_per_code_task,
    "test_file_matches_task": _check_test_file_matches_task,
}


def unknown_checks(role_def: RoleDefinition) -> list[str]:
    return [c for c in role_def.checks if c not in CHECKS]


# ── Hilfen ────────────────────────────────────────────────────────────────────

def truncate(text: str, tokens: int) -> str:
    grenze = tokens * CHARS_PER_TOKEN
    if len(text) <= grenze:
        return text
    return text[:grenze] + f"\n… [gekürzt auf etwa {tokens} Tokens]"


def extract_json(text: str) -> Any:
    """Erstes JSON-Objekt oder -Array im Text (Codeblöcke erlaubt); None, wenn keins."""
    if not text or not text.strip():
        return None
    block = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    kandidat = block.group(1) if block else text
    decoder = json.JSONDecoder()
    for i, zeichen in enumerate(kandidat):
        if zeichen in "{[":
            try:
                wert, _ = decoder.raw_decode(kandidat[i:])
            except json.JSONDecodeError:
                continue
            return wert
    return None


def render_sources(role_def: RoleDefinition, sources: Mapping[str, Any]) -> str:
    teile = []
    for quelle in role_def.inputs:
        if quelle not in CONTEXT_SOURCES:
            continue
        wert = sources.get(quelle)
        if wert in (None, "", [], {}):
            continue
        text = wert if isinstance(wert, str) else json.dumps(wert, ensure_ascii=False, indent=2)
        teile.append(f"## {SOURCE_TITLES[quelle]}\n\n{truncate(text, role_def.budget(quelle))}")
    return "\n\n".join(teile)


# ── RoleRunner ────────────────────────────────────────────────────────────────

class RoleRunner:
    def __init__(self, *, run_id: str, spec_id: str) -> None:
        self.run_id = run_id
        self.spec_id = spec_id

    def run(self, role_def: RoleDefinition, provider: Any, sources: Mapping[str, Any], *,
            attempt: int, params: Mapping[str, Any] | None = None, lead: str = "",
            check_context: Mapping | None = None, task: Mapping | None = None) -> RoleResult:
        """Führt einen Rollenaufruf aus.

        `lead` steht vor den Kontextquellen (z. B. die Entscheidungsanfrage des Supervisors).
        """
        params = {**role_def.defaults, **(params or {})}
        call_id = secrets.token_hex(6)
        max_tokens = int(params.get("max_output_tokens") or DEFAULT_MAX_OUTPUT)
        timeout = params.get("timeout_seconds")
        prompt = self._prompt(role_def, sources, lead)
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
        ergebnis = RoleResult(role_def.role, call_id, attempt, "error", prompt_hash=prompt_hash)

        kontext: dict[str, Any] = {"spec_id": self.spec_id, "run_id": self.run_id,
                                   "role": role_def.role, "attempt": attempt,
                                   "role_version": role_def.version, "call_id": call_id}
        if task:
            kontext.update(task_id=task.get("id"), task_label=task.get("title") or task.get("id"))
        with usage_context(**kontext):
            for versuch in (1, 2):
                try:
                    antwort = provider.complete(
                        f"{prompt}\n\nnonce: {secrets.token_hex(8)}",
                        max_tokens=max_tokens, system_prompt=role_def.prompt,
                        timeout=int(timeout) if timeout else None)
                except Exception as exc:  # Server weg, Timeout: outcome error, kein Abbruch
                    log.warning("Rolle %s: Aufruf fehlgeschlagen: %s", role_def.role, exc)
                    ergebnis.problems = [f"Aufruf fehlgeschlagen: {exc}"]
                    ergebnis.outcome = "error"
                    return ergebnis
                ergebnis.usage = antwort.usage
                ergebnis.raw = antwort.text
                output = extract_json(antwort.text)
                laengenabbruch = (antwort.usage is not None
                                  and antwort.usage.finish_reason == "length")
                if output is None and laengenabbruch and versuch == 1:
                    max_tokens = int(max_tokens * 1.5)
                    continue
                break
        if output is None:
            ergebnis.outcome = "invalid_output"
            ergebnis.problems = ["Antwort enthält kein JSON"
                                 + (" (Längenabbruch)" if laengenabbruch else "")]
            return ergebnis
        probleme = self._validate(role_def, output, check_context or {})
        ergebnis.output = output
        ergebnis.problems = probleme
        ergebnis.outcome = "invalid_output" if probleme else "ok"
        return ergebnis

    @staticmethod
    def _prompt(role_def: RoleDefinition, sources: Mapping[str, Any], lead: str) -> str:
        teile = [lead] if lead else []
        kontext = render_sources(role_def, sources)
        if kontext:
            teile.append(kontext)
        return "\n\n".join(teile) or role_def.purpose

    @staticmethod
    def _validate(role_def: RoleDefinition, output: Any, ctx: Mapping) -> list[str]:
        name, definition = role_def.schema_ref()
        probleme = schema_errors(name, output, definition)
        if probleme:
            return probleme
        for check in role_def.checks:
            funktion = CHECKS.get(check)
            if funktion is None:
                probleme.append(f"unbekannter Rollen-Check {check!r}")
                continue
            probleme.extend(funktion(output, ctx))
        return probleme
