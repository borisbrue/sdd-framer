"""ClaudeCliCompletionProvider – nutzt die claude CLI."""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ..base import CompletionResult, UsageMetadata

log = logging.getLogger(__name__)

# 600 statt 120: der Regression-Check brauchte fuer reale Specs mehrere Minuten
# und lief systematisch in den alten Wert. Solange ein Skip die Gate-Phase noch
# markierte, fiel das nicht auf; seit #71 bleibt das Gate dort stehen.
_DEFAULT_COMPLETION_TIMEOUT = 600

# Flatpak-Sandboxes und andere eingeschränkte Umgebungen fehlt ~/.local/bin im PATH.
_EXTRA_SEARCH_PATH = os.pathsep.join([
    str(Path.home() / ".local" / "bin"),
    "/usr/local/bin",
    os.environ.get("PATH", ""),
])


def _find_claude() -> str | None:
    return shutil.which("claude") or shutil.which("claude", path=_EXTRA_SEARCH_PATH)


def _command(claude: str, system_prompt: str | None) -> list[str]:
    """Aufruf als reine Completion-Engine (SPEC-0067 FR-01/FR-02, CON-0233 INV-01).

    Ohne Tools, Einstellungen, MCP und den Claude-Code-System-Prompt; der Prompt kommt über stdin.
    """
    return [claude, "--print", "--output-format", "json",
            "--tools", "", "--setting-sources", "", "--strict-mcp-config",
            "--system-prompt", system_prompt or ""]


def _environment() -> dict[str, str]:
    """Elternumgebung ohne Auto-Memory des Projekts (SPEC-0067 FR-03, CON-0233 INV-03)."""
    return {**os.environ, "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"}


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def usage_from_envelope(envelope: Any) -> UsageMetadata:
    """Usage aus dem JSON-Envelope von `claude --print --output-format json` (SPEC-0060 FR-02).

    Fehlt der Usage-Block, ist `source: unavailable` und ein Hinweis wird geloggt.
    """
    usage = envelope.get("usage") if isinstance(envelope, dict) else None
    if not isinstance(usage, dict) or _int(usage.get("input_tokens")) is None:
        log.info("claude-cli: Envelope ohne Usage – Aufruf wird als 'unavailable' erfasst")
        return UsageMetadata.unavailable()
    details = usage.get("output_tokens_details") or {}
    model_usage = envelope.get("modelUsage")
    server_model = next(iter(model_usage), None) if isinstance(model_usage, dict) else None
    return UsageMetadata(
        input_tokens=_int(usage.get("input_tokens")) or 0,
        output_tokens=_int(usage.get("output_tokens")) or 0,
        cache_creation_tokens=_int(usage.get("cache_creation_input_tokens")) or 0,
        cache_read_tokens=_int(usage.get("cache_read_input_tokens")) or 0,
        model=server_model or "",
        reasoning_tokens=_int(details.get("thinking_tokens")) if isinstance(details, dict) else None,
        finish_reason=envelope.get("stop_reason"),
        server_model=server_model,
        source="reported",
    )


class ClaudeCliCompletionProvider:
    """Ruft `claude --print --output-format json` auf und gibt den inneren Text zurück.

    Aufrufform nach CON-0233: keine Tools, keine Einstellungen, kein MCP, kein Auto-Memory;
    Prompt über stdin.
    max_tokens: ignoriert (CLI kennt kein --max-tokens Flag).
    system_prompt: per --system-prompt; ohne ihn ein leerer System-Prompt.
    timeout: an subprocess.run weitergereicht. Reihenfolge: Argument, sonst der
    beim Erzeugen gesetzte Wert (aus llm.timeout_seconds), sonst 600s.
    usage: aus dem Envelope (SPEC-0060 FR-02); ohne Usage-Block `source: unavailable`.
    """

    def __init__(self, timeout: int | None = None) -> None:
        self._timeout = timeout

    def complete(
        self,
        prompt: str,
        *,
        max_tokens: int = 512,
        system_prompt: str | None = None,
        timeout: int | None = None,
    ) -> CompletionResult:
        claude = _find_claude()
        if not claude:
            raise RuntimeError(
                "claude CLI nicht gefunden. "
                "Installiere Claude Code CLI und melde dich an."
            )
        effective_timeout = (
            timeout
            if timeout is not None
            else (self._timeout or _DEFAULT_COMPLETION_TIMEOUT)
        )
        try:
            proc = subprocess.run(
                _command(claude, system_prompt),
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=_environment(),
                timeout=effective_timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"claude CLI Timeout nach {effective_timeout}s."
            ) from exc

        raw = proc.stdout.strip()
        # Strip outer JSON envelope: {"type":"result","result":"<text>",...}
        try:
            outer = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            outer = None
        if isinstance(outer, dict) and "result" in outer:
            return CompletionResult(text=str(outer["result"]), usage=usage_from_envelope(outer))
        if proc.returncode != 0:
            raise RuntimeError(
                f"claude CLI mit Exit-Code {proc.returncode} beendet: {proc.stderr[-500:]}"
            )
        log.info("claude-cli: Ausgabe ist kein JSON-Envelope – Usage 'unavailable'")
        return CompletionResult(text=raw, usage=UsageMetadata.unavailable())
