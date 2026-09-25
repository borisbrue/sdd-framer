"""CompletionProvider und CodeGenProvider – abstrakte Protokoll-Interfaces.

SOLID:
  - ISP: Zwei getrennte Interfaces für unterschiedliche Verwendungszwecke.
  - LSP: Alle Implementierungen sind über isinstance() prüfbar (@runtime_checkable).
  - DIP: Komponenten (Evaluator, Orchestrator, …) hängen nur von diesen Protokollen ab.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

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


class CodeGenResult(tuple):
    """Ergebnis von CodeGenProvider.generate() (SPEC-0060 FR-04).

    Übergangs-Schnittstelle: bleibt als `(files, explanation)` entpackbar und trägt die Usage als
    Attribut, bis SPEC-0058 die Tupel-Aufrufer ablöst.
    """

    usage: UsageMetadata

    def __new__(
        cls, files: list[dict[str, Any]], explanation: str, usage: UsageMetadata | None = None,
    ) -> CodeGenResult:
        obj = super().__new__(cls, (files, explanation))
        obj.usage = usage or UsageMetadata.unavailable()
        return obj

    @property
    def files(self) -> list[dict[str, Any]]:
        return self[0]

    @property
    def explanation(self) -> str:
        return self[1]


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


@runtime_checkable
class CodeGenProvider(Protocol):
    """Agentische Code-Generierung, die Dateien in einen Workspace schreibt.

    Genutzt von: Orchestrator.
    Implementierungen: ClaudeCliCodeGenProvider,
                       OpenAICompatCodeGenProvider.
    """

    def generate(
        self,
        prompt: str,
        workspace: Path,
        *,
        timeout: int = 600,
        on_proc: Callable[[Any], None] | None = None,
    ) -> CodeGenResult:
        """Generiert Code, schreibt Dateien in workspace und gibt sie zurück.

        Returns:
            CodeGenResult – entpackbar als ([{"path": "rel/path", "content": "..."}], explanation)

        on_proc: wird von nicht-CLI-Providern ignoriert und niemals aufgerufen.
        Aufrufer dürfen sich nicht darauf verlassen, dass der Callback ausgelöst wird.
        """
        ...
