"""AnthropicCompletionProvider – nutzt das anthropic SDK."""
from __future__ import annotations

import os

from ..base import CompletionResult, UsageMetadata


class AnthropicCompletionProvider:
    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        temperature: float = 0.0,
    ) -> None:
        self._model = model
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._temperature = temperature

    def complete(
        self,
        prompt: str,
        *,
        max_tokens: int = 512,
        system_prompt: str | None = None,
        timeout: int | None = None,
    ) -> CompletionResult:
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError(
                "Das anthropic-Paket ist nicht installiert. "
                "Führe `pip install 'sdd-cli[evaluate]'` aus."
            ) from exc
        if not self._api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY ist nicht gesetzt. "
                "Exportiere die Variable oder konfiguriere llm.*.api_key in config.yaml."
            )
        client = anthropic.Anthropic(api_key=self._api_key)
        kwargs: dict = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": self._temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        if timeout is not None:
            kwargs["timeout"] = timeout

        message = client.messages.create(**kwargs)
        usage = message.usage
        return CompletionResult(
            text=message.content[0].text,
            usage=UsageMetadata(
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
                cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
                model=self._model,
                finish_reason=getattr(message, "stop_reason", None),
                server_model=getattr(message, "model", None) or None,
                source="reported",
            ),
        )
