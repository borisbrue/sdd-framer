"""Persists AI provider token usage for cost analysis."""
from __future__ import annotations

import json
import os
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


def _store_path() -> Path:
    env = os.environ.get("SDD_PROJECT_ROOT")
    root = Path(env).resolve() if env else Path.cwd()
    return root / ".sdd" / "ai_usage.json"


def _load() -> list[dict[str, Any]]:
    p = _store_path()
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text())
    except Exception:
        return []


def _save(records: list[dict[str, Any]]) -> None:
    p = _store_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(records, indent=2))


def record_usage(
    operation: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int,
    cache_read_tokens: int,
    model: str,
    provider: str = "claude",
) -> dict[str, Any]:
    rates = COST_PER_1M.get(provider, COST_PER_1M["claude"])
    cost = (
        input_tokens * rates["input"] / 1_000_000
        + output_tokens * rates["output"] / 1_000_000
        + cache_creation_tokens * rates["cache_write"] / 1_000_000
        + cache_read_tokens * rates["cache_read"] / 1_000_000
    )
    entry: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "operation": operation,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_creation_tokens": cache_creation_tokens,
        "cache_read_tokens": cache_read_tokens,
        "cost_usd": round(cost, 6),
    }
    records = _load()
    records.append(entry)
    _save(records)
    return entry


def get_all() -> list[dict[str, Any]]:
    return _load()


def get_summary() -> dict[str, Any]:
    records = _load()
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
        "total_cost_usd": round(total_cost, 6),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_cache_read_tokens": total_cache_read,
        "total_cache_creation_tokens": total_cache_write,
        "by_operation": by_op,
        "by_provider": by_provider,
    }
