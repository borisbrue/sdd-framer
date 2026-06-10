"""Routing-Entscheidung: complexity_score → executor (CON-0171)."""
from __future__ import annotations

from .config import TaskRoutingConfig


def decide_executor(task, config: TaskRoutingConfig) -> str:
    """Gibt 'local' oder 'claude' zurück basierend auf complexity_score und Config.

    INV-01: complexity_score muss 0–100 sein, sonst ValueError.
    INV-02: Rückgabe ist immer 'local' oder 'claude' (nie None).
    INV-03: routing disabled oder kein local_llm → immer 'claude'.
    INV-04: score <= threshold → 'local' (inklusiver Vergleich).
    INV-05: deterministisch für gleiche Eingabe.
    """
    score = task.complexity_score
    if not isinstance(score, int) or score < 0 or score > 100:
        raise ValueError(
            f"complexity_score muss im Bereich 0–100 liegen, war: {score!r}"
        )

    if not config.enabled or not config.local_llm_configured:
        return "claude"

    return "local" if score <= config.complexity_threshold else "claude"
