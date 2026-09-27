"""Token-Budget eines Pipeline-Runs (SPEC-0063 FR-01, CON-0225).

Grenzen kommen aus `pipeline.budget` in `config.yaml`, überschrieben von den Run-Optionen
(`options.budget` in `run.json`). Gezählt wird die Usage des Runs in `token_usage` (`run_id`,
Komponente `role:<rolle>`); Claude-Tokens sind die der Rollen, die laut `run.json` mit `claude-cli`
oder `anthropic` belegt sind. Session-Rollen erzeugen keine Usage und zählen nicht.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import Any

KEYS = ("max_tokens", "max_claude_tokens")
CLAUDE_PROVIDERS = ("claude-cli", "anthropic")
REASON = "budget"


def issues(raw: Mapping) -> list[tuple[str, str, str]]:
    """(level, pfad, meldung) für `pipeline.budget` (ergänzt CON-0190, CON-0225 INV-04)."""
    block = (raw.get("pipeline") or {}).get("budget")
    if block is None:
        return []
    if not isinstance(block, dict):
        return [("error", "pipeline.budget", "muss ein Objekt sein")]
    ergebnis = [("error", f"pipeline.budget.{k}", "unbekannter Schlüssel")
                for k in sorted(set(block) - set(KEYS))]
    for k in KEYS:
        wert = block.get(k)
        if wert is not None and (isinstance(wert, bool) or not isinstance(wert, int)
                                 or wert <= 0):
            ergebnis.append(("error", f"pipeline.budget.{k}", "muss eine ganze Zahl > 0 sein"))
    return ergebnis


def option_errors(options: Mapping[str, Any]) -> list[str]:
    return [f"--{k.replace('_', '-')} muss eine ganze Zahl > 0 sein" for k, v in options.items()
            if v is not None and (not isinstance(v, int) or isinstance(v, bool) or v <= 0)]


def limits(raw: Mapping, options: Mapping[str, Any] | None) -> dict[str, int]:
    basis = (raw.get("pipeline") or {}).get("budget") or {}
    wirksam = {k: basis.get(k) for k in KEYS}
    wirksam.update({k: v for k, v in (options or {}).items() if v is not None})
    return {k: int(v) for k, v in wirksam.items() if v}


def usage(root: Path, run_id: str, claude_roles: set[str]) -> dict[str, int]:
    db = root / ".sdd" / "evaluations.db"
    if not db.is_file():
        return {"tokens": 0, "claude_tokens": 0}
    try:
        with sqlite3.connect(db) as con:
            zeilen = con.execute(
                "SELECT component, COALESCE(SUM(input_tokens),0) + COALESCE(SUM(output_tokens),0)"
                " FROM token_usage WHERE run_id = ? GROUP BY component", (run_id,)).fetchall()
    except sqlite3.Error:
        return {"tokens": 0, "claude_tokens": 0}
    gesamt = sum(n for _, n in zeilen)
    claude = sum(n for komponente, n in zeilen
                 if str(komponente).removeprefix("role:") in claude_roles)
    return {"tokens": int(gesamt), "claude_tokens": int(claude)}


def exceeded(grenzen: Mapping[str, int], stand: Mapping[str, int]) -> str | None:
    if grenzen.get("max_tokens") and stand["tokens"] > grenzen["max_tokens"]:
        return "max_tokens"
    if grenzen.get("max_claude_tokens") and stand["claude_tokens"] > grenzen["max_claude_tokens"]:
        return "max_claude_tokens"
    return None


def claude_roles(roles: Mapping[str, Mapping]) -> set[str]:
    return {r for r, b in roles.items() if b.get("provider") in CLAUDE_PROVIDERS}


class BudgetExhausted(RuntimeError):
    """Der Run ist wegen des Budgets angehalten; weitere Aufrufe werden verweigert."""


class GuardedProvider:
    """Decorator: verweigert Aufrufe, sobald der Run wegen des Budgets angehalten ist."""

    def __init__(self, inner: Any, is_halted: Any) -> None:
        self.inner, self.is_halted = inner, is_halted

    def complete(self, prompt: str, **kwargs: Any) -> Any:
        if self.is_halted():
            raise BudgetExhausted("Run wegen Budget angehalten")
        return self.inner.complete(prompt, **kwargs)
