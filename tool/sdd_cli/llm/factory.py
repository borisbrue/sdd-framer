"""Provider-Factory – löst LLM-Provider aus config.yaml auf.

Auflösungs-Hierarchie (erstes nicht-None gewinnt):
  1. config.raw["llm"][component]          (Komponenten-Override)
  2. config.raw["llm"]["completion"|"code_gen"]  (globaler Default-Block)
  3. Built-in-Defaults (je Komponente)
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from ..config import SddConfig
    from .base import CodeGenProvider, CompletionProvider

_COMPLETION_PROVIDERS = ("anthropic", "claude-cli", "openai-compat", "huggingface")
_CODE_GEN_PROVIDERS = ("claude-cli", "openai-compat")

_DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"

# Built-in defaults per component (Ebene 3)
_COMPLETION_BUILTIN: dict[str, dict] = {
    "evaluator":  {"provider": "claude-cli"},
    "analyzer":   {"provider": "claude-cli"},
    "ai_routes":  {"provider": "claude-cli"},
    "completion": {"provider": "claude-cli"},
}


def _resolve_env_var(value: str | None) -> str | None:
    """Löst ${ENV_VAR}-Referenzen in api_key-Werten auf."""
    if value and value.startswith("${") and value.endswith("}"):
        var_name = value[2:-1]
        resolved = os.environ.get(var_name)
        if resolved is None:
            raise RuntimeError(
                f"Env-Var {var_name!r} ist nicht gesetzt "
                f"(referenziert als api_key in config.yaml)."
            )
        return resolved
    return value


def _resolve(raw: dict, component: str, default_block: str) -> dict:
    llm = raw.get("llm") or {}
    comp: dict = llm.get(component) or {}
    block: dict = llm.get(default_block) or {}
    builtin: dict = _COMPLETION_BUILTIN.get(component, {})

    # Deprecated: evaluator.model (ohne llm-Prefix)
    deprecated_model: str | None = None
    if component == "evaluator":
        deprecated_model = (raw.get("evaluator") or {}).get("model")
    # Deprecated: evaluator.llm.* (SPEC-0008 v0.2.0)
    if component == "evaluator" and not comp:
        comp = (raw.get("evaluator") or {}).get("llm") or {}

    api_key = comp.get("api_key") or block.get("api_key")
    enable_thinking_comp = comp.get("enable_thinking")
    enable_thinking_block = block.get("enable_thinking")
    enable_thinking = (
        enable_thinking_comp if enable_thinking_comp is not None
        else (enable_thinking_block if enable_thinking_block is not None else True)
    )
    return {
        "provider": comp.get("provider") or block.get("provider") or builtin.get("provider"),
        "model": comp.get("model") or block.get("model") or deprecated_model or builtin.get("model"),
        "base_url": comp.get("base_url") or block.get("base_url"),
        "api_key": _resolve_env_var(api_key),
        "temperature": comp.get("temperature") if comp.get("temperature") is not None
                       else (block.get("temperature") if block.get("temperature") is not None
                             else 0.0),
        "enable_thinking": enable_thinking,
    }


def get_completion_provider(
    config: "SddConfig",
    component: Literal["evaluator", "analyzer", "ai_routes", "completion", "local_llm"] = "completion",
) -> "CompletionProvider":
    """Gibt den CompletionProvider für die angegebene Komponente zurück.

    Unbekannter component-Wert → ValueError (kein stiller Fallback).
    local_llm: nutzt llm.local_llm als Override, fällt auf llm.completion zurück.
    """
    valid = ("evaluator", "analyzer", "ai_routes", "completion", "local_llm")
    if component not in valid:
        raise ValueError(
            f"Unbekannte Komponente: {component!r}. "
            f"Erlaubte Werte: {', '.join(valid)}"
        )

    cfg = _resolve(config.raw, component, "completion")
    provider = cfg["provider"] or "claude-cli"

    if provider not in _COMPLETION_PROVIDERS:
        raise ValueError(
            f"Unbekannter LLM-Provider: {provider!r}. "
            f"Erlaubte Werte: {', '.join(_COMPLETION_PROVIDERS)}"
        )

    if provider == "anthropic":
        from .providers.anthropic import AnthropicCompletionProvider
        return AnthropicCompletionProvider(
            model=cfg["model"] or _DEFAULT_ANTHROPIC_MODEL,
            api_key=cfg["api_key"],
            temperature=cfg["temperature"],
        )

    if provider == "claude-cli":
        from .providers.claude_cli import ClaudeCliCompletionProvider
        return ClaudeCliCompletionProvider(timeout=config.llm_timeout())

    if provider == "huggingface":
        llm = config.raw.get("llm") or {}
        comp_raw: dict = llm.get(component) or {}
        block_raw: dict = llm.get("completion") or {}

        raw_token = comp_raw.get("hf_token") or block_raw.get("hf_token")
        hf_token = _resolve_env_var(raw_token)
        hf_mode = comp_raw.get("hf_mode") or block_raw.get("hf_mode") or "serverless"
        endpoint_url = comp_raw.get("endpoint_url") or block_raw.get("endpoint_url")

        if hf_mode == "dedicated" and not endpoint_url:
            raise ValueError(
                f"llm.{component}.endpoint_url ist Pflicht für provider: huggingface, hf_mode: dedicated."
            )
        if hf_mode in ("serverless", "dedicated") and not hf_token:
            raise RuntimeError(
                f"hf_token ist nicht gesetzt für provider: huggingface (hf_mode: {hf_mode}). "
                "Setze HF_TOKEN als Env-Var oder konfiguriere llm.*.hf_token in config.yaml."
            )
        if not cfg["model"] and hf_mode in ("serverless", "local"):
            raise ValueError(
                f"llm.{component}.model ist Pflicht für provider: huggingface, hf_mode: {hf_mode}."
            )

        from .providers.huggingface import HuggingFaceCompletionProvider
        return HuggingFaceCompletionProvider(
            model=cfg["model"],
            hf_token=hf_token,
            hf_mode=hf_mode,
            endpoint_url=endpoint_url,
            temperature=cfg["temperature"],
        )

    # openai-compat
    base_url = cfg["base_url"]
    model = cfg["model"]
    if not base_url:
        raise ValueError(
            f"llm.{component}.base_url ist Pflicht für provider: openai-compat."
        )
    if not model:
        raise ValueError(
            f"llm.{component}.model ist Pflicht für provider: openai-compat."
        )
    from .providers.openai_compat import OpenAICompatCompletionProvider
    return OpenAICompatCompletionProvider(
        base_url=base_url,
        model=model,
        api_key=cfg["api_key"] or "lm-studio",
        temperature=cfg["temperature"],
        enable_thinking=cfg["enable_thinking"],
    )


def get_code_gen_provider(config: "SddConfig") -> "CodeGenProvider":
    """Gibt den CodeGenProvider zurück (genutzt vom Orchestrator)."""
    cfg = _resolve(config.raw, "orchestrator", "code_gen")
    provider = cfg["provider"] or "claude-cli"

    if provider == "huggingface":
        raise ValueError(
            "provider: huggingface unterstützt keinen code_gen-Modus. "
            "Nutze claude-cli oder openai-compat für Code-Generierung."
        )
    if provider not in _CODE_GEN_PROVIDERS:
        raise ValueError(
            f"Unbekannter CodeGen-Provider: {provider!r}. "
            f"Erlaubte Werte: {', '.join(_CODE_GEN_PROVIDERS)}"
        )

    if provider == "claude-cli":
        from .providers.claude_cli import ClaudeCliCodeGenProvider
        return ClaudeCliCodeGenProvider()

    # openai-compat
    base_url = cfg["base_url"]
    model = cfg["model"]
    if not base_url:
        raise ValueError(
            "llm.orchestrator.base_url ist Pflicht für provider: openai-compat."
        )
    if not model:
        raise ValueError(
            "llm.orchestrator.model ist Pflicht für provider: openai-compat."
        )
    from .providers.openai_compat import OpenAICompatCodeGenProvider
    return OpenAICompatCodeGenProvider(
        base_url=base_url,
        model=model,
        api_key=cfg["api_key"] or "lm-studio",
    )
