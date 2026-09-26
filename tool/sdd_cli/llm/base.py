"""CompletionProvider – abstraktes Protokoll-Interface.

SOLID:
  - LSP: Alle Implementierungen sind über isinstance() prüfbar (@runtime_checkable).
  - DIP: Komponenten (Evaluator, Pipeline-Rollen, …) hängen nur von diesem Protokoll ab.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

UsageSource = Literal["reported", "estimated", "unavailable"]


@dataclass
class UsageMetadata:
    """Token-Nutzungsdaten eines LLM-Aufrufs (SPEC-0060 FR-01, CON-0207).

    `source` sagt, woher die Zählwerte stammen. Nicht gemeldete optionale Werte sind None;
    `reasoning_tokens == 0` heißt „gemeldet, kein Reasoning“.
    """
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    model: str = ""
    estimated: bool = False
    reasoning_tokens: int | None = None
    finish_reason: str | None = None
    latency_ms: int | None = None
    server_model: str | None = None
    source: UsageSource = "reported"

    def __post_init__(self) -> None:
        if self.estimated and self.source == "reported":
            self.source = "estimated"

    @classmethod
    def unavailable(cls, model: str = "", finish_reason: str | None = None) -> UsageMetadata:
        """Usage eines Aufrufs, für den der Provider nichts gemeldet hat."""
        return cls(model=model, finish_reason=finish_reason, source="unavailable")


@dataclass
class CompletionResult:
    """Rückgabe von CompletionProvider.complete().

    Ab SPEC-0060 liefern alle Provider `usage`; None kommt nur noch von Fremd-Implementierungen.
    """
    text: str
    usage: UsageMetadata | None = None


@runtime_checkable
class CompletionProvider(Protocol):
    """Synchrones Prompt → CompletionResult.

    Genutzt von: Evaluator, Analyzer, AI-Routes.
    Implementierungen: AnthropicCompletionProvider,
                       ClaudeCliCompletionProvider,
                       OpenAICompatCompletionProvider.
    """

    def complete(
        self,
        prompt: str,
        *,
        max_tokens: int = 512,
        system_prompt: str | None = None,
        timeout: int | None = None,
    ) -> CompletionResult:
        """Sendet prompt an das LLM und gibt CompletionResult zurück.

        JSON-Parsing liegt in der Verantwortung des Aufrufers.
        Wirft bei Fehler immer eine Exception — gibt nie None zurück.
        timeout: Sekunden; None = Provider-Default. Evaluator belegt ihn mit
        timeout_per_scenario; andere Komponenten lassen None.
        """
        ...
