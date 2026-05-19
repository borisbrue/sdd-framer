"""LLM-Provider-Verbindungstest für SPEC-0027 (CON-0103).

Strategy Pattern: Jeder Provider-Typ implementiert LlmProviderProbe.
"""
from __future__ import annotations

import time
from typing import Protocol


class LlmProbeError(Exception):
    """Raised when an LLM provider is unreachable or returns an error."""


class LlmProviderProbe(Protocol):
    def probe(self, provider: dict) -> float:
        """Send a minimal ping request. Returns latency in ms. Raises LlmProbeError."""
        ...


class OllamaProbe:
    def probe(self, provider: dict) -> float:
        import urllib.request
        base_url = provider.get("base_url", "http://localhost:11434").rstrip("/")
        url = f"{base_url}/api/tags"
        start = time.monotonic()
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                resp.read()
        except Exception as exc:
            raise LlmProbeError(f"Ollama nicht erreichbar unter {base_url}: {exc}") from exc
        return (time.monotonic() - start) * 1000


class AnthropicProbe:
    def probe(self, provider: dict) -> float:
        import os
        import urllib.request
        import urllib.error
        import json as _json

        key_env = provider.get("api_key_env", "")
        api_key = os.environ.get(key_env, "")
        if not api_key:
            raise LlmProbeError(
                f"Env-Variable '{key_env}' nicht gesetzt – Anthropic-Provider nicht testbar."
            )
        url = "https://api.anthropic.com/v1/models"
        req = urllib.request.Request(
            url,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        start = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise LlmProbeError(f"Anthropic-API-Key ungültig (HTTP {exc.code})") from exc
            raise LlmProbeError(f"Anthropic HTTP-Fehler {exc.code}") from exc
        except Exception as exc:
            raise LlmProbeError(f"Anthropic nicht erreichbar: {exc}") from exc
        return (time.monotonic() - start) * 1000


class OpenAICompatProbe:
    def probe(self, provider: dict) -> float:
        import os
        import urllib.request
        import urllib.error

        key_env = provider.get("api_key_env", "")
        api_key = os.environ.get(key_env, "") if key_env else ""
        base_url = provider.get("base_url", "").rstrip("/")
        if not base_url:
            raise LlmProbeError("OpenAI-compat-Provider braucht base_url")
        url = f"{base_url}/models"
        headers: dict = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        req = urllib.request.Request(url, headers=headers)
        start = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
        except Exception as exc:
            raise LlmProbeError(f"OpenAI-compat nicht erreichbar unter {base_url}: {exc}") from exc
        return (time.monotonic() - start) * 1000


_PROBES: dict[str, LlmProviderProbe] = {
    "local": OllamaProbe(),
    "anthropic": AnthropicProbe(),
    "remote": AnthropicProbe(),
    "openai": OpenAICompatProbe(),
    "openai-compat": OpenAICompatProbe(),
}


def get_probe(provider: dict) -> LlmProviderProbe:
    ptype = provider.get("type", "remote")
    model = provider.get("model", "")
    if ptype == "local":
        return OllamaProbe()
    if "openai" in model.lower() or provider.get("base_url"):
        return OpenAICompatProbe()
    return AnthropicProbe()


def probe_llm(provider: dict) -> float:
    """Probe a provider config. Returns latency ms. Raises LlmProbeError if unreachable."""
    probe = get_probe(provider)
    return probe.probe(provider)
