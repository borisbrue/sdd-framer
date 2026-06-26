"""OpenAICompatCompletionProvider und OpenAICompatCodeGenProvider.

Kompatibel mit LM Studio, Ollama und jedem anderen OpenAI-kompatiblen Server.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from collections.abc import Callable

from ..base import CompletionResult, UsageMetadata

_PROTECTED_PREFIXES = ("specs/", "contracts/", "tests/", ".sdd/")

_CODE_GEN_SUFFIX = (
    "\n\nReturn ONLY a JSON object — no markdown fences, no prose:\n"
    '{"files":[{"path":"relative/path","content":"..."}],"explanation":"<one line>"}'
)


class OpenAICompatCompletionProvider:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "lm-studio",
        temperature: float = 0.0,
        enable_thinking: bool = True,
    ) -> None:
        self._base_url = base_url
        self._model = model
        self._api_key = api_key or "lm-studio"
        self._temperature = temperature
        self._enable_thinking = enable_thinking

    def complete(
        self,
        prompt: str,
        *,
        max_tokens: int = 512,
        system_prompt: str | None = None,
        timeout: int | None = None,
    ) -> CompletionResult:
        try:
            import openai
        except ImportError as exc:
            raise RuntimeError(
                "Das openai-Paket ist nicht installiert. "
                "Führe `pip install 'sdd-cli[lm-studio]'` aus."
            ) from exc
        client = openai.OpenAI(
            base_url=self._base_url,
            api_key=self._api_key,
        )
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        create_kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": self._temperature,
        }
        if timeout is not None:
            create_kwargs["timeout"] = timeout
        if not self._enable_thinking:
            # Disables Qwen3/DeepSeek extended thinking mode in LM Studio
            create_kwargs["extra_body"] = {"enable_thinking": False}

        response = client.chat.completions.create(**create_kwargs)
        raw_usage = response.usage
        usage = UsageMetadata(
            input_tokens=raw_usage.prompt_tokens if raw_usage else 0,
            output_tokens=raw_usage.completion_tokens if raw_usage else 0,
            model=self._model,
        ) if raw_usage else None
        return CompletionResult(
            text=(response.choices[0].message.content or "").strip(),
            usage=usage,
        )


class OpenAICompatCodeGenProvider:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "lm-studio",
    ) -> None:
        self._base_url = base_url
        self._model = model
        self._api_key = api_key or "lm-studio"

    def generate(
        self,
        prompt: str,
        workspace: Path,
        *,
        timeout: int = 600,
        on_proc: Callable[[Any], None] | None = None,
    ) -> tuple[list[dict[str, Any]], str]:
        try:
            import openai
        except ImportError as exc:
            raise RuntimeError(
                "Das openai-Paket ist nicht installiert. "
                "Führe `pip install 'sdd-cli[lm-studio]'` aus."
            ) from exc

        client = openai.OpenAI(
            base_url=self._base_url,
            api_key=self._api_key,
            timeout=float(timeout),
        )
        response = client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt + _CODE_GEN_SUFFIX}],
            max_tokens=8192,
            temperature=0,
        )
        raw = response.choices[0].message.content.strip()

        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            raise json.JSONDecodeError("Kein JSON-Objekt in LLM-Antwort gefunden", raw, 0)
        data = json.loads(raw[start:end])

        workspace_resolved = workspace.resolve()
        files_written: list[dict[str, Any]] = []
        for entry in data.get("files", []):
            rel_path: str = entry["path"].lstrip("/")
            # Path traversal validation
            full = (workspace / rel_path).resolve()
            try:
                full.relative_to(workspace_resolved)
            except ValueError:
                raise ValueError(f"Unsicherer Pfad (Workspace-Escape): {rel_path!r}")
            if any(rel_path.startswith(p) for p in _PROTECTED_PREFIXES):
                raise ValueError(
                    f"SDD-Artefakt darf nicht überschrieben werden: {rel_path!r}"
                )
            full.parent.mkdir(parents=True, exist_ok=True)
            content: str = entry.get("content", "")
            full.write_text(content, encoding="utf-8")
            files_written.append({"path": rel_path, "content": content})

        explanation = data.get("explanation", "implement via openai-compat")[:200]
        return files_written, explanation
