"""ClaudeCliCompletionProvider und ClaudeCliCodeGenProvider – nutzen die claude CLI."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any
from collections.abc import Callable

from ..base import CompletionResult

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


class ClaudeCliCompletionProvider:
    """Ruft `claude --print --output-format json` auf und gibt den inneren Text zurück.

    max_tokens: ignoriert (CLI kennt kein --max-tokens Flag).
    system_prompt: als Präfix <system>\\n...\\n</system>\\n\\n eingefügt.
    timeout: an subprocess.run weitergereicht. Reihenfolge: Argument, sonst der
    beim Erzeugen gesetzte Wert (aus llm.timeout_seconds), sonst 600s.
    usage: immer None (CLI liefert keine Token-Counts).
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
        if system_prompt:
            full_prompt = f"<system>\n{system_prompt}\n</system>\n\n{prompt}"
        else:
            full_prompt = prompt

        effective_timeout = (
            timeout
            if timeout is not None
            else (self._timeout or _DEFAULT_COMPLETION_TIMEOUT)
        )
        try:
            proc = subprocess.run(
                [claude, "--print", "--output-format", "json", "-p", full_prompt],
                capture_output=True,
                text=True,
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
            if isinstance(outer, dict) and "result" in outer:
                return CompletionResult(text=str(outer["result"]), usage=None)
        except (json.JSONDecodeError, ValueError):
            pass
        return CompletionResult(text=raw, usage=None)


class ClaudeCliCodeGenProvider:
    """Ruft `claude --print --dangerously-skip-permissions` auf.

    Claude schreibt Dateien direkt in den Workspace; die Methode
    entdeckt Änderungen anschließend via git.
    """

    def generate(
        self,
        prompt: str,
        workspace: Path,
        *,
        timeout: int = 600,
        on_proc: Callable[[Any], None] | None = None,
    ) -> tuple[list[dict[str, Any]], str]:
        claude = _find_claude()
        if not claude:
            raise RuntimeError(
                "claude CLI nicht gefunden. "
                "Installiere Claude Code CLI und melde dich an."
            )
        proc = subprocess.Popen(
            [claude, "--print", "--dangerously-skip-permissions", "-p", prompt],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(workspace),
        )
        if on_proc:
            on_proc(proc)
        try:
            stdout, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            raise RuntimeError(f"claude CLI Timeout nach {timeout}s")

        if proc.returncode != 0:
            raise RuntimeError(f"claude CLI Fehler (exit {proc.returncode})")

        def _git(*args: str) -> str:
            r = subprocess.run(
                ["git", *args], cwd=workspace, capture_output=True, text=True
            )
            return (r.stdout + r.stderr).strip()

        changed = _git("diff", "--name-only")
        untracked = _git("ls-files", "--others", "--exclude-standard")
        all_paths = [
            p.strip()
            for p in (changed + "\n" + untracked).splitlines()
            if p.strip()
        ]
        files: list[dict[str, Any]] = []
        for p in all_paths:
            full = workspace / p
            if full.exists():
                try:
                    files.append({"path": p, "content": full.read_text(encoding="utf-8")})
                except Exception:
                    files.append({"path": p, "content": ""})

        lines = [ln for ln in stdout.strip().splitlines() if ln.strip()]
        explanation = lines[-1][:200] if lines else "implement via claude-cli"
        return files, explanation
