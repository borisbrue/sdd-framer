"""LLM-Routing: kontextbasierte Delegation an ein lokales Modell oder die Cloud."""
from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal, Protocol

CHARS_PER_TOKEN = 4


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
    """Schätzt Tokens offline: ein Token je angefangene 4 Zeichen des Gesamttexts."""
    return math.ceil(len(ctx.full_text()) / CHARS_PER_TOKEN)


class LlmRoutingStrategy(Protocol):
    def route(self, ctx: TaskContext) -> Literal["local", "cloud"]: ...


class ContextSizeRoutingStrategy:
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
        if not self.enabled:
            return "cloud"
        estimated = self._counter(ctx)
        if estimated + self.context_reserve_tokens <= self.context_window:
            return "local"
        return "cloud"
