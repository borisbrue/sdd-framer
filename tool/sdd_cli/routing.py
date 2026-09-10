"""LLM-Routing-Strategie für SPEC-0036 – kontextbasierte lokale/Cloud-Delegation.

Strategy Pattern (Refactoring Guru): LlmRoutingStrategy ist austauschbares Protocol.
ContextSizeRoutingStrategy zählt Tokens via tiktoken und vergleicht mit context_window.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal, Protocol


@dataclass
class TaskContext:
    task_description: str = ""
    spec_section: str = ""
    contract_texts: list[str] = field(default_factory=list)
    test_stub_texts: list[str] = field(default_factory=list)
    code_file_texts: list[str] = field(default_factory=list)

    def full_text(self) -> str:
        parts = [self.task_description, self.spec_section]
        parts.extend(self.contract_texts)
        parts.extend(self.test_stub_texts)
        parts.extend(self.code_file_texts)
        return "\n".join(p for p in parts if p)


def count_task_tokens(ctx: TaskContext) -> int:
    """Count tokens using tiktoken cl100k_base (FR-02, INV-04: no network call)."""
    try:
        import tiktoken
    except ImportError as e:
        raise ImportError(
            "tiktoken ist nicht installiert. Installiere es mit: pip install tiktoken"
        ) from e
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(ctx.full_text()))


class LlmRoutingStrategy(Protocol):
    def route(self, ctx: TaskContext) -> Literal["local", "cloud"]: ...


class ContextSizeRoutingStrategy:
    """Implementiert LlmRoutingStrategy via Token-Größen-Vergleich (CON-0125)."""

    def __init__(
        self,
        context_window: int,
        context_reserve_tokens: int,
        enabled: bool,
        counter: Callable[[TaskContext], int] | None = None,
    ) -> None:
        self.context_window = context_window
        self.context_reserve_tokens = context_reserve_tokens
        self.enabled = enabled
        self._counter = counter if counter is not None else count_task_tokens

    def route(self, ctx: TaskContext) -> Literal["local", "cloud"]:
        """INV-01: returns "local" or "cloud". INV-02: disabled → always cloud.
        INV-03: deterministic. INV-04: no network."""
        if not self.enabled:
            return "cloud"
        estimated = self._counter(ctx)
        if estimated + self.context_reserve_tokens <= self.context_window:
            return "local"
        return "cloud"
