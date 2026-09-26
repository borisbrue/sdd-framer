"""Usage-Erfassung für jeden LLM-Aufruf (SPEC-0060, CON-0206, CON-0207).

Decorator Pattern: `RecordingCompletionProvider`/`RecordingCodeGenProvider` umhüllen die Provider
aus der Factory und erzeugen je Aufruf genau einen `UsageRecord`, auch bei einer Ausnahme.
Observer: Senken (`UsageSink`) empfangen die Datensätze; die SQLite-Senke für `token_usage` ist
vorregistriert. Aufrufkontext (Spec, Lauf, Rolle …) kommt über `usage_context` aus einer
ContextVar, damit Provider-Signaturen unverändert bleiben (CON-0207 INV-06).
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from .base import CodeGenResult, CompletionResult, UsageMetadata

if TYPE_CHECKING:
    from ..config import SddConfig

log = logging.getLogger(__name__)

# Kontextschlüssel mit eigener Spalte in token_usage (CON-0206 INV-03); alle übrigen landen in
# context_json.
COLUMN_KEYS = ("spec_id", "task_id", "task_label", "run_id", "agent_type")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class UsageRecord:
    """Usage eines Aufrufs plus Komponente, Modell, Dauer, Zeitpunkt und Aufrufkontext.

    `root` ist das Projekt, in dessen `evaluations.db` die Standard-Senke schreibt; die Factory
    setzt es. Ohne `root` schreibt nur eine Senke mit eigener Konfiguration.
    """
    component: str
    model: str
    usage: UsageMetadata
    duration_ms: int = 0
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)
    root: Path | None = None


@runtime_checkable
class UsageSink(Protocol):
    def record(self, record: UsageRecord) -> None: ...


# ── Aufrufkontext ─────────────────────────────────────────────────────────────

_context: ContextVar[dict[str, Any] | None] = ContextVar("sdd_usage_context", default=None)


def current_context() -> dict[str, Any]:
    return dict(_context.get() or {})


@contextmanager
def usage_context(**keys: Any) -> Iterator[dict[str, Any]]:
    """Setzt Kontextschlüssel für die Dauer des Blocks; verschachtelt ergänzt/überschreibt."""
    token = _context.set({**current_context(), **keys})
    try:
        yield current_context()
    finally:
        _context.reset(token)


# ── Senken ────────────────────────────────────────────────────────────────────

class SqliteUsageSink:
    """Schreibt Datensätze in `token_usage` von `.sdd/evaluations.db` (SPEC-0060 FR-05).

    Mit `config` schreibt sie immer in dieses Projekt, ohne in das Projekt des Datensatzes
    (`record.root`). Die Standard-Senke verwirft Datensätze ohne Projekt und legt nie ein
    `.sdd/` an, wo keins ist.
    """

    def __init__(self, config: SddConfig | None = None) -> None:
        self._config = config

    def root_for(self, record: UsageRecord) -> Path | None:
        if self._config is not None:
            return self._config.root
        if record.root is None or not (record.root / ".sdd").is_dir():
            return None
        return record.root

    def record(self, record: UsageRecord) -> None:
        root = self.root_for(record)
        if root is None:
            return
        from .usage_table import TOKEN_USAGE_TABLE, init_token_usage_table_at

        db = init_token_usage_table_at(root / ".sdd")
        u = record.usage
        spalten = {k: record.context.get(k) for k in COLUMN_KEYS}
        rest = {k: v for k, v in record.context.items() if k not in COLUMN_KEYS}
        werte = {
            "timestamp": record.timestamp,
            "component": record.component,
            "model": record.model or u.model or "",
            "input_tokens": u.input_tokens or 0,
            "output_tokens": u.output_tokens or 0,
            "cache_read_tokens": u.cache_read_tokens or 0,
            "cache_write_tokens": u.cache_creation_tokens or 0,
            "duration_ms": record.duration_ms,
            **spalten,
            "reasoning_tokens": u.reasoning_tokens,
            "finish_reason": u.finish_reason,
            "server_model": u.server_model,
            "source": u.source,
            "context_json": json.dumps(rest, ensure_ascii=False, default=str) if rest else None,
        }
        namen = ", ".join(werte)
        platzhalter = ", ".join("?" for _ in werte)
        with sqlite3.connect(db) as conn:
            conn.execute(f"INSERT INTO {TOKEN_USAGE_TABLE} ({namen}) VALUES ({platzhalter})",
                         tuple(werte.values()))


_registered: list[UsageSink] = [SqliteUsageSink()]
_override: ContextVar[list[UsageSink] | None] = ContextVar("sdd_usage_sinks", default=None)


def register_sink(sink: UsageSink) -> None:
    """Registriert eine Senke dauerhaft für den Prozess (z. B. Benchmark-Export)."""
    if sink not in _registered:
        _registered.append(sink)


def unregister_sink(sink: UsageSink) -> None:
    if sink in _registered:
        _registered.remove(sink)


@contextmanager
def use_sinks(sinks: list[UsageSink]) -> Iterator[None]:
    """Ersetzt die registrierten Senken für die Dauer des Blocks (Tests, Messläufe)."""
    token = _override.set(list(sinks))
    try:
        yield
    finally:
        _override.reset(token)


def active_sinks() -> list[UsageSink]:
    override = _override.get()
    return list(override) if override is not None else list(_registered)


def emit(record: UsageRecord) -> None:
    """Gibt den Datensatz an alle aktiven Senken; eine ausfallende Senke stoppt keine andere."""
    for sink in active_sinks():
        try:
            sink.record(record)
        except Exception as exc:  # FR-10: Senkenfehler dürfen den Aufruf nicht scheitern lassen
            log.warning("Usage-Senke %s fehlgeschlagen: %s", type(sink).__name__, exc)


# ── Decorators ────────────────────────────────────────────────────────────────

class _Recording:
    def __init__(self, inner: Any, *, component: str, model: str,
                 root: Path | None = None) -> None:
        self.inner = inner
        self.component = component
        self.model = model
        self.root = root

    def _record(self, usage: UsageMetadata, t0: float) -> None:
        dauer = int((time.monotonic() - t0) * 1000)
        if usage.latency_ms is None:
            usage.latency_ms = dauer
        emit(UsageRecord(component=self.component, model=self.model, usage=usage,
                         duration_ms=usage.latency_ms, context=current_context(),
                         root=self.root))

    def _call(self, aufruf: Callable[[], Any]) -> Any:
        t0 = time.monotonic()
        try:
            ergebnis = aufruf()
        except Exception:
            self._record(UsageMetadata.unavailable(self.model, finish_reason="error"), t0)
            raise
        usage = getattr(ergebnis, "usage", None)
        self._record(usage if isinstance(usage, UsageMetadata)
                     else UsageMetadata.unavailable(self.model), t0)
        return ergebnis

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.inner!r}, component={self.component!r})"


class RecordingCompletionProvider(_Recording):
    """Decorator um einen CompletionProvider; Ergebnis und Ausnahme bleiben unverändert."""

    def complete(self, prompt: str, **kwargs: Any) -> CompletionResult:
        return self._call(lambda: self.inner.complete(prompt, **kwargs))


class RecordingCodeGenProvider(_Recording):
    """Decorator um einen CodeGenProvider; ein Datensatz je `generate()` (CON-0207 INV-07)."""

    def generate(self, prompt: str, workspace: Path, **kwargs: Any) -> CodeGenResult:
        return self._call(lambda: self.inner.generate(prompt, workspace, **kwargs))


def unwrap(provider: Any) -> Any:
    """Der umhüllte Provider (oder der Provider selbst, falls nicht umhüllt)."""
    while isinstance(provider, _Recording):
        provider = provider.inner
    return provider
