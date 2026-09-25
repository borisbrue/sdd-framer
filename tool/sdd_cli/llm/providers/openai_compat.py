"""OpenAICompatCompletionProvider und OpenAICompatCodeGenProvider.

Kompatibel mit LM Studio, Ollama und jedem anderen OpenAI-kompatiblen Server.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..base import CodeGenResult, CompletionResult, UsageMetadata

_PROTECTED_PREFIXES = ("specs/", "contracts/", "tests/", ".sdd/")

_CODE_GEN_SUFFIX = (
    "\n\nReturn ONLY a JSON object — no markdown fences, no prose:\n"
    '{"files":[{"path":"relative/path","content":"..."}],"explanation":"<one line>"}'
)


def usage_from_response(response: Any, model: str) -> UsageMetadata:
    """Usage einer Chat-Completion-Antwort (SPEC-0060 FR-03)."""
    choices = getattr(response, "choices", None) or []
    finish_reason = getattr(choices[0], "finish_reason", None) if choices else None
    server_model = getattr(response, "model", None) or None
    raw = getattr(response, "usage", None)
    if raw is None:
        return UsageMetadata(model=model, finish_reason=finish_reason, server_model=server_model,
                             source="unavailable")
    details = getattr(raw, "completion_tokens_details", None)
    reasoning = getattr(details, "reasoning_tokens", None) if details is not None else None
    prompt_details = getattr(raw, "prompt_tokens_details", None)
    cached = getattr(prompt_details, "cached_tokens", None) if prompt_details is not None else None
    return UsageMetadata(
        input_tokens=raw.prompt_tokens or 0,
        output_tokens=raw.completion_tokens or 0,
        cache_read_tokens=cached or 0,
        model=model,
        reasoning_tokens=reasoning,
        finish_reason=finish_reason,
        server_model=server_model,
        source="reported",
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
            # Disables Qwen3/DeepSeek extended thinking mode. LM Studio reads the flat
            # flag; vLLM (and LiteLLM in front of it) ignores it and only honours
            # chat_template_kwargs. Servers ignore the variant they don't know.
            create_kwargs["extra_body"] = {
                "enable_thinking": False,
                "chat_template_kwargs": {"enable_thinking": False},
            }

        response = client.chat.completions.create(**create_kwargs)
        return CompletionResult(
            text=(response.choices[0].message.content or "").strip(),
            usage=usage_from_response(response, self._model),
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
    ) -> CodeGenResult:
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
            except ValueError as exc:
                raise ValueError(f"Unsicherer Pfad (Workspace-Escape): {rel_path!r}") from exc
            if any(rel_path.startswith(p) for p in _PROTECTED_PREFIXES):
                raise ValueError(
                    f"SDD-Artefakt darf nicht überschrieben werden: {rel_path!r}"
                )
            full.parent.mkdir(parents=True, exist_ok=True)
            content: str = entry.get("content", "")
            full.write_text(content, encoding="utf-8")
            files_written.append({"path": rel_path, "content": content})

        explanation = data.get("explanation", "implement via openai-compat")[:200]
        return CodeGenResult(files_written, explanation, usage_from_response(response, self._model))
