"""RoleRunner: ein Rollenaufruf nach festem Ablauf (SPEC-0053 FR-06, Template Method).

Kontext zusammenstellen → System-Prompt und Prompt mit Nonce rendern → LLM im Usage-Kontext
aufrufen → Ausgabe
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
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ..llm.base import UsageMetadata
from ..llm.usage import usage_context
from . import checks as checks_mod
from .roles import CONTEXT_SOURCES, SOURCE_KINDS, RoleDefinition
from .schemas import errors as schema_errors

log = logging.getLogger(__name__)

CHARS_PER_TOKEN = 4
DEFAULT_MAX_OUTPUT = 8000
SOURCE_TITLES = {
    "spec": "Spec", "contracts": "Contracts", "agents_md": "AGENTS.md", "repo_map": "Dateien",
    "current_files": "Aktueller Inhalt der Dateien aus allowed_paths",
    "dependency_api": "Schnittstellen erledigter Abhängigkeiten",
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
    failed_checks: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.outcome == "ok"


def unknown_checks(role_def: RoleDefinition) -> list[str]:
    """Unbekannte oder im Gate nicht nutzbare Checks einer Rolle (CON-0219 INV-01)."""
    return [*checks_mod.unknown_checks(role_def.checks),
            *checks_mod.not_gate_capable(role_def.checks)]


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


def render_sources(role_def: RoleDefinition, sources: Mapping[str, Any],
                   kind: str | None = None) -> str:
    """Quellen der Rolle in der Reihenfolge ihrer `inputs`; mit `kind` nur diese Einteilung."""
    teile = []
    for quelle in role_def.inputs:
        if quelle not in CONTEXT_SOURCES or (kind and SOURCE_KINDS[quelle] != kind):
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
        system, prompt = self._prompt(role_def, sources, lead)
        prompt_hash = hashlib.sha256(f"{system}\n\n{prompt}".encode()).hexdigest()[:16]
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
                        max_tokens=max_tokens, system_prompt=system,
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
        probleme, gescheitert = self.validate_checks(role_def, output, check_context or {})
        ergebnis.failed_checks = gescheitert
        ergebnis.output = output
        ergebnis.problems = probleme
        ergebnis.outcome = "invalid_output" if probleme else "ok"
        return ergebnis

    @staticmethod
    def _prompt(role_def: RoleDefinition, sources: Mapping[str, Any],
                lead: str) -> tuple[str, str]:
        """(System-Prompt, Prompt) nach CON-0234 INV-02/INV-03.

        Stabile Quellen hängen am Rollen-Prompt, damit der System-Prompt über Wiederholungsversuche
        byte-gleich bleibt und aus dem Prompt-Cache gelesen wird (SPEC-0068).
        """
        stabil = render_sources(role_def, sources, "stable")
        system = f"{role_def.prompt}\n\n{stabil}" if stabil else role_def.prompt
        teile = [lead] if lead else []
        wechselnd = render_sources(role_def, sources, "volatile")
        if wechselnd:
            teile.append(wechselnd)
        return system, "\n\n".join(teile) or role_def.purpose

    @staticmethod
    def validate_checks(role_def: RoleDefinition, output: Any,
                        ctx: Mapping) -> tuple[list[str], list[str]]:
        """Schema und Gate-Checks der Rolle: (Probleme, Namen der gescheiterten Checks)."""
        name, definition = role_def.schema_ref()
        probleme = schema_errors(name, output, definition)
        if probleme:
            return probleme, ["json_schema"]
        return checks_mod.gate_problems(role_def.checks, output, ctx)

    @staticmethod
    def _validate(role_def: RoleDefinition, output: Any, ctx: Mapping) -> list[str]:
        return RoleRunner.validate_checks(role_def, output, ctx)[0]
