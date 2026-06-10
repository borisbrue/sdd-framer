"""TaskRoutingConfig – Konfigurationsschema für task_routing (CON-0174)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TaskRoutingConfig:
    enabled: bool = False
    complexity_threshold: int = 30
    max_retries: int = 3
    max_concurrent: int = 3
    local_llm_configured: bool = False
    local_llm_base_url: str | None = None
    local_llm_model: str | None = None
    local_llm_api_key: str | None = None
    local_llm_temperature: float = 0.0


def load_task_routing_config(raw: dict) -> TaskRoutingConfig:
    """Lädt task_routing-Config aus dem rohen config.yaml-Dict.

    INV-01: enabled=true ohne llm.local_llm → local_llm_configured=False (silent fallback).
    INV-02: Fehlt task_routing-Block → alle Defaults gelten.
    INV-03: complexity_threshold außerhalb 0–100 → ValueError.
    INV-04: llm.local_llm.provider nur openai-compat in v0.1.0.
    INV-05: llm.local_llm.model erbt von llm.completion.model wenn nicht gesetzt.
    """
    tr = raw.get("task_routing") or {}
    llm = raw.get("llm") or {}
    local_llm = llm.get("local_llm")
    completion = llm.get("completion") or {}

    threshold = tr.get("complexity_threshold", 30)
    if not isinstance(threshold, int) or threshold < 0 or threshold > 100:
        raise ValueError(
            f"complexity_threshold muss im Bereich 0–100 liegen, war: {threshold!r}"
        )

    local_llm_configured = False
    local_llm_base_url: str | None = None
    local_llm_model: str | None = None
    local_llm_api_key: str | None = None
    local_llm_temperature: float = 0.0

    if local_llm is not None:
        provider = local_llm.get("provider")
        if provider != "openai-compat":
            raise ValueError(
                f"llm.local_llm.provider muss 'openai-compat' sein in v0.1.0, war: {provider!r}"
            )

        base_url = local_llm.get("base_url")
        if not base_url:
            raise ValueError(
                "llm.local_llm.base_url ist Pflichtfeld für provider: openai-compat"
            )

        model = local_llm.get("model") or completion.get("model")
        local_llm_configured = True
        local_llm_base_url = base_url
        local_llm_model = model
        local_llm_api_key = local_llm.get("api_key")
        local_llm_temperature = float(local_llm.get("temperature", 0.0))

    return TaskRoutingConfig(
        enabled=bool(tr.get("enabled", False)),
        complexity_threshold=threshold,
        max_retries=int(tr.get("max_retries", 3)),
        max_concurrent=int(tr.get("max_concurrent", 3)),
        local_llm_configured=local_llm_configured,
        local_llm_base_url=local_llm_base_url,
        local_llm_model=local_llm_model,
        local_llm_api_key=local_llm_api_key,
        local_llm_temperature=local_llm_temperature,
    )
