"""LLM-Pool-Registry und Selector für SPEC-0026 (CON-0098).

Strategy Pattern: LlmSelector-Subklassen kapseln Auswahlstrategien.
Baut auf SPEC-0008 LLM-Provider-Abstraktion auf.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .task_model import Task, Complexity, ContextSize


class CostTier(str, Enum):
    CHEAP = "cheap"
    STANDARD = "standard"
    POWERFUL = "powerful"


class LlmType(str, Enum):
    LOCAL = "local"
    REMOTE = "remote"


@dataclass
class LlmEntry:
    id: str
    type: LlmType
    model: str
    cost_tier: CostTier
    max_context_tokens: int


class LlmUnavailableError(Exception):
    pass


_TIER_ORDER: list[CostTier] = [CostTier.CHEAP, CostTier.STANDARD, CostTier.POWERFUL]

_TASK_TIER: dict[tuple[Complexity, ContextSize], CostTier] = {
    (Complexity.LOW,    ContextSize.S): CostTier.CHEAP,
    (Complexity.LOW,    ContextSize.M): CostTier.CHEAP,
    (Complexity.LOW,    ContextSize.L): CostTier.STANDARD,
    (Complexity.MEDIUM, ContextSize.S): CostTier.STANDARD,
    (Complexity.MEDIUM, ContextSize.M): CostTier.STANDARD,
    (Complexity.MEDIUM, ContextSize.L): CostTier.POWERFUL,
    (Complexity.HIGH,   ContextSize.S): CostTier.POWERFUL,
    (Complexity.HIGH,   ContextSize.M): CostTier.POWERFUL,
    (Complexity.HIGH,   ContextSize.L): CostTier.POWERFUL,
}


class LlmPoolRegistry:
    def __init__(self, entries: list[LlmEntry] | None = None) -> None:
        self._entries: list[LlmEntry] = []
        for e in (entries or []):
            self.register(e)

    def register(self, entry: LlmEntry) -> None:
        if any(e.id == entry.id for e in self._entries):
            raise ValueError(f"Doppelte LLM-ID: {entry.id}")
        self._entries.append(entry)

    @property
    def entries(self) -> list[LlmEntry]:
        return list(self._entries)

    def get(self, llm_id: str) -> LlmEntry | None:
        return next((e for e in self._entries if e.id == llm_id), None)


class LlmSelector:
    def __init__(self, registry: LlmPoolRegistry) -> None:
        self._registry = registry

    def select(self, task: Task) -> LlmEntry:
        preferred_tier = _TASK_TIER[(task.complexity, task.context_size)]
        candidates = [
            e for e in self._registry.entries
            if e.max_context_tokens >= task.estimated_tokens
        ]
        if not candidates:
            raise LlmUnavailableError(
                f"Kein LLM mit ausreichend Kontext für {task.estimated_tokens} Tokens."
            )

        # Versuche preferred_tier und dann fallback aufwärts/abwärts
        tier_idx = _TIER_ORDER.index(preferred_tier)
        for tier in (
            _TIER_ORDER[tier_idx:] + list(reversed(_TIER_ORDER[:tier_idx]))
        ):
            tier_candidates = [c for c in candidates if c.cost_tier == tier]
            if not tier_candidates:
                continue
            # INV-03: lokal vor remote bei gleichem Tier
            local = [c for c in tier_candidates if c.type == LlmType.LOCAL]
            return local[0] if local else tier_candidates[0]

        raise LlmUnavailableError("Kein passendes LLM im Pool verfügbar.")
