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
from typing import Any, Protocol, runtime_checkable


@dataclass
class UsageMetadata:
    """Token-Nutzungsdaten einer Completion; None-Felder wenn Provider sie nicht liefert."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    model: str = ""
    estimated: bool = False


@dataclass
class CompletionResult:
    """Rückgabe von CompletionProvider.complete()."""
    text: str
    usage: UsageMetadata | None = None
    # usage ist None bei ClaudeCliCompletionProvider (CLI liefert keine Token-Counts).
    # Aufrufer die usage benötigen (ai.py → usage_store) prüfen auf None.


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
    ) -> tuple[list[dict[str, Any]], str]:
        """Generiert Code, schreibt Dateien in workspace und gibt sie zurück.

        Returns:
            ([{"path": "rel/path", "content": "..."}], explanation)

        on_proc: wird von nicht-CLI-Providern ignoriert und niemals aufgerufen.
        Aufrufer dürfen sich nicht darauf verlassen, dass der Callback ausgelöst wird.
        """
        ...
