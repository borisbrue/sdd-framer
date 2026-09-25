"""Token-Usage der Web-API für die Kostenanalyse.

Seit SPEC-0060 FR-08 liegt alles in `token_usage` (`.sdd/evaluations.db`); das frühere
`.sdd/ai_usage.json` übernimmt `sdd upgrade` einmalig und schreibt es danach nicht mehr.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Cost per 1M tokens by provider (USD).
# GitHub Copilot is subscription-based — tokens tracked but cost shown as 0.
COST_PER_1M: dict[str, dict[str, float]] = {
    "claude": {
        "input": 5.00,
        "output": 25.00,
        "cache_read": 0.50,
        "cache_write": 6.25,
    },
    "copilot": {
        "input": 0.0,
        "output": 0.0,
        "cache_read": 0.0,
        "cache_write": 0.0,
    },
}


def _project_root() -> Path:
    env = os.environ.get("SDD_PROJECT_ROOT")
    return Path(env).resolve() if env else Path.cwd()


def cost_usd(
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int,
    cache_read_tokens: int,
    provider: str = "claude",
) -> float:
    rates = COST_PER_1M.get(provider, COST_PER_1M["claude"])
    cost = (
        input_tokens * rates["input"] / 1_000_000
        + output_tokens * rates["output"] / 1_000_000
        + cache_creation_tokens * rates["cache_write"] / 1_000_000
        + cache_read_tokens * rates["cache_read"] / 1_000_000
    )
    return round(cost, 6)


def cost_entry(
    operation: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int,
    cache_read_tokens: int,
    model: str,
    provider: str = "claude",
) -> dict[str, Any]:
    """Eintrag mit Kosten für die Antwort an den Client, ohne ihn zu speichern.

    Für Aufrufe über die Provider-Factory: die hat den Aufruf bereits erfasst (SPEC-0060 FR-06).
    """
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "operation": operation,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_creation_tokens": cache_creation_tokens,
        "cache_read_tokens": cache_read_tokens,
        "cost_usd": cost_usd(input_tokens, output_tokens, cache_creation_tokens,
                             cache_read_tokens, provider),
    }


def record_usage(
    operation: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int,
    cache_read_tokens: int,
    model: str,
    provider: str = "claude",
) -> dict[str, Any]:
    """Erfasst einen Aufruf, der nicht über die Provider-Factory lief (z. B. Copilot).

    Der Datensatz geht über die Usage-Senken nach `token_usage` (SPEC-0060 FR-08).
    """
    from sdd_cli.llm.base import UsageMetadata
    from sdd_cli.llm.usage import UsageRecord, emit, usage_context

    entry = cost_entry(operation, input_tokens, output_tokens, cache_creation_tokens,
                       cache_read_tokens, model, provider)
    usage = UsageMetadata(input_tokens=input_tokens, output_tokens=output_tokens,
                          cache_creation_tokens=cache_creation_tokens,
                          cache_read_tokens=cache_read_tokens, model=model, source="reported")
    with usage_context(origin="web", operation=operation, provider=provider) as kontext:
        emit(UsageRecord(component="ai_routes", model=model, usage=usage, context=kontext,
                         root=_project_root()))
    return entry


def _rows() -> list[dict[str, Any]]:
    from sdd_cli.estimation import TOKEN_USAGE_TABLE, init_token_usage_table_at

    sdd_dir = _project_root() / ".sdd"
    if not (sdd_dir / "evaluations.db").exists():
        return []
    db = init_token_usage_table_at(sdd_dir)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(f"SELECT * FROM {TOKEN_USAGE_TABLE} ORDER BY id")]


def _entry(row: dict[str, Any]) -> dict[str, Any]:
    try:
        kontext = json.loads(row.get("context_json") or "{}")
    except json.JSONDecodeError:
        kontext = {}
    provider = kontext.get("provider", "claude")
    return {
        "ts": row["timestamp"],
        "provider": provider,
        "operation": kontext.get("operation") or row["component"],
        "model": row["model"],
        "input_tokens": row["input_tokens"],
        "output_tokens": row["output_tokens"],
        "cache_creation_tokens": row["cache_write_tokens"],
        "cache_read_tokens": row["cache_read_tokens"],
        "cost_usd": cost_usd(row["input_tokens"], row["output_tokens"],
                             row["cache_write_tokens"], row["cache_read_tokens"], provider),
        "source": row.get("source"),
        "spec_id": row.get("spec_id"),
    }


def get_all() -> list[dict[str, Any]]:
    return [_entry(r) for r in _rows()]


def get_summary() -> dict[str, Any]:
    alle = get_all()
    # SPEC-0060 FR-11: Aufrufe ohne Usage zählen nicht in Summen, ihre Anzahl wird genannt.
    records = [r for r in alle if r.get("source") != "unavailable"]
    total_cost = sum(r["cost_usd"] for r in records)
    total_input = sum(r["input_tokens"] for r in records)
    total_output = sum(r["output_tokens"] for r in records)
    total_cache_read = sum(r["cache_read_tokens"] for r in records)
    total_cache_write = sum(r["cache_creation_tokens"] for r in records)
    by_op: dict[str, dict[str, Any]] = {}
    by_provider: dict[str, dict[str, Any]] = {}
    for r in records:
        op = r["operation"]
        if op not in by_op:
            by_op[op] = {"count": 0, "cost_usd": 0.0}
        by_op[op]["count"] += 1
        by_op[op]["cost_usd"] = round(by_op[op]["cost_usd"] + r["cost_usd"], 6)

        prov = r.get("provider", "claude")
        if prov not in by_provider:
            by_provider[prov] = {"count": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
        by_provider[prov]["count"] += 1
        by_provider[prov]["input_tokens"] += r["input_tokens"]
        by_provider[prov]["output_tokens"] += r["output_tokens"]
        by_provider[prov]["cost_usd"] = round(by_provider[prov]["cost_usd"] + r["cost_usd"], 6)

    return {
        "total_calls": len(records),
        "unavailable_calls": len(alle) - len(records),
        "total_cost_usd": round(total_cost, 6),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_cache_read_tokens": total_cache_read,
        "total_cache_creation_tokens": total_cache_write,
        "by_operation": by_op,
        "by_provider": by_provider,
    }
