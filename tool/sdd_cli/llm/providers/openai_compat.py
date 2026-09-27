"""OpenAICompatCompletionProvider.

Kompatibel mit LM Studio, Ollama und jedem anderen OpenAI-kompatiblen Server.
"""
from __future__ import annotations

from typing import Any

from ..base import CompletionResult, UsageMetadata


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
        top_p: float | None = None,
        reasoning_effort: str | None = None,
        seed: int | None = None,
    ) -> None:
        self._base_url = base_url
        self._model = model
        self._api_key = api_key or "lm-studio"
        self._temperature = temperature
        self._enable_thinking = enable_thinking
        self._top_p = top_p
        self._reasoning_effort = reasoning_effort
        self._seed = seed

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
        if self._top_p is not None:
            create_kwargs["top_p"] = self._top_p
        if self._seed is not None:
            create_kwargs["seed"] = self._seed  # SPEC-0056 FR-09, Reproduzierbarkeit
        extra_body: dict[str, Any] = {}
        if not self._enable_thinking:
            # Disables Qwen3/DeepSeek extended thinking mode. LM Studio reads the flat
            # flag; vLLM (and LiteLLM in front of it) ignores it and only honours
            # chat_template_kwargs. Servers ignore the variant they don't know.
            extra_body.update({
                "enable_thinking": False,
                "chat_template_kwargs": {"enable_thinking": False},
            })
        if self._reasoning_effort:
            # SPEC-0053 FR-04; als extra_body, damit Server ohne Unterstützung ihn ignorieren.
            extra_body["reasoning_effort"] = self._reasoning_effort
        if extra_body:
            create_kwargs["extra_body"] = extra_body

        response = client.chat.completions.create(**create_kwargs)
        return CompletionResult(
            text=(response.choices[0].message.content or "").strip(),
            usage=usage_from_response(response, self._model),
        )
