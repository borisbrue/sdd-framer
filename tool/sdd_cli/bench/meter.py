"""Provider-Hüllen eines Laufs (SPEC-0056 FR-09, CON-0223 INV-05), Decorator.

`Meter` zählt Tokens je Rolle (gemeldet oder geschätzt), erzwingt das Budget und begrenzt
gleichzeitige Aufrufe je Endpunkt (`max_concurrent`); optional auch die Rate
(`requests_per_minute`), wenn der Aufrufer sie nicht selbst begrenzt.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from ..pipeline.evals.runner import RateLimiter
from .config import CLAUDE_PROVIDERS

CHARS_PER_TOKEN = 4


class BudgetExceeded(RuntimeError):
    """Budget des Laufs ausgeschöpft; weitere Aufrufe werden verweigert."""


_LOCK = threading.Lock()
_SEMAPHORES: dict[tuple, threading.BoundedSemaphore] = {}


def _semaphore(endpoint: tuple, limit: int) -> threading.BoundedSemaphore:
    with _LOCK:
        schluessel = (*endpoint, limit)
        if schluessel not in _SEMAPHORES:
            _SEMAPHORES[schluessel] = threading.BoundedSemaphore(limit)
        return _SEMAPHORES[schluessel]


@dataclass
class RoleTokens:
    input: int = 0
    output: int = 0
    reasoning: int = 0
    calls: int = 0
    estimated: bool = False

    def to_dict(self) -> dict:
        return {"input": self.input, "output": self.output, "reasoning": self.reasoning,
                "calls": self.calls, "estimated": self.estimated}


@dataclass
class Meter:
    max_tokens: int | None = None
    max_claude_tokens: int | None = None
    rate_limit: bool = False
    tokens: dict[str, RoleTokens] = field(default_factory=dict)
    claude_tokens: int = 0
    server_models: dict[str, str] = field(default_factory=dict)
    exceeded: bool = False
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _limiter: RateLimiter = field(default_factory=RateLimiter)

    @property
    def total(self) -> int:
        return sum(t.input + t.output for t in self.tokens.values())

    def wrap(self, provider: Any, binding: Any, role: str) -> MeteredProvider:
        return MeteredProvider(provider, binding, role, self)

    def record(self, role: str, binding: Any, prompt: str, system: str | None,
               result: Any) -> None:
        usage = getattr(result, "usage", None)
        with self._lock:
            t = self.tokens.setdefault(role, RoleTokens())
            t.calls += 1
            if usage is None or getattr(usage, "source", "") == "unavailable":
                eingabe = (len(prompt) + len(system or "")) // CHARS_PER_TOKEN
                ausgabe = len(getattr(result, "text", "") or "") // CHARS_PER_TOKEN
                t.estimated = True
                reasoning = 0
            else:
                eingabe, ausgabe = usage.input_tokens or 0, usage.output_tokens or 0
                reasoning = usage.reasoning_tokens or 0
                if usage.source == "estimated":
                    t.estimated = True
                if getattr(usage, "server_model", None):
                    self.server_models[role] = usage.server_model
            t.input += eingabe
            t.output += ausgabe
            t.reasoning += reasoning
            if binding.provider in CLAUDE_PROVIDERS:
                self.claude_tokens += eingabe + ausgabe
            if (self.max_tokens and self.total > self.max_tokens) or (
                    self.max_claude_tokens and self.claude_tokens > self.max_claude_tokens):
                self.exceeded = True


class MeteredProvider:
    def __init__(self, inner: Any, binding: Any, role: str, meter: Meter) -> None:
        self.inner, self.binding, self.role, self.meter = inner, binding, role, meter

    def complete(self, prompt: str, **kwargs: Any) -> Any:
        if self.meter.exceeded:
            raise BudgetExceeded("Budget des Laufs ausgeschöpft")
        grenze = self.binding.params.get("max_concurrent")
        sperre = _semaphore(self.binding.endpoint, int(grenze)) if grenze else None
        if self.meter.rate_limit:
            self.meter._limiter.wait(self.binding)
        if sperre:
            sperre.acquire()
        try:
            ergebnis = self.inner.complete(prompt, **kwargs)
        finally:
            if sperre:
                sperre.release()
        self.meter.record(self.role, self.binding, prompt, kwargs.get("system_prompt"), ergebnis)
        return ergebnis
