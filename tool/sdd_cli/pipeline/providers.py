"""Provider je Rolle (SPEC-0053 FR-04), Strategy über die Provider-Factory.

Auflösung: `llm.roles.<rolle>` → Komponentenblock aus `legacy_component` der Rollendatei (wie in
CON-0023 G-02) → Builtin `claude-cli`. Jeder Provider ist vom Usage-Decorator aus SPEC-0060
umhüllt.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..llm.factory import _resolve, _resolve_env_var
from ..llm.usage import RecordingCompletionProvider

if TYPE_CHECKING:
    from ..config import SddConfig
    from .roles import RoleDefinition

ROLE_KEYS = frozenset({"provider", "model", "base_url", "api_key", "temperature", "top_p",
                       "max_output_tokens", "thinking", "reasoning_effort", "timeout_seconds",
                       "mode"})
SUPPORTED = {
    "claude-cli": frozenset({"provider", "model", "timeout_seconds", "mode"}),
    "anthropic": frozenset({"provider", "model", "api_key", "temperature", "max_output_tokens",
                            "timeout_seconds", "mode"}),
    "openai-compat": frozenset({"provider", "model", "base_url", "api_key", "temperature",
                                "top_p", "max_output_tokens", "thinking", "reasoning_effort",
                                "timeout_seconds", "mode"}),
}
SAME_MODEL_WARNING = "Modell reviewt seine eigene Arbeit"


class RoleConfigError(Exception):
    """`llm.roles.<rolle>` ist ungültig."""


@dataclass(frozen=True)
class RoleBinding:
    """Aufgelöste Modellbelegung einer Rolle (ohne Geheimnisse in `describe`)."""
    role: str
    provider: str
    model: str
    base_url: str | None
    api_key: str | None
    params: dict
    source: str  # "roles" | "legacy:<komponente>" | "builtin"

    @property
    def endpoint(self) -> tuple[str, str | None, str]:
        return (self.provider, self.base_url, self.model)

    def describe(self) -> dict:
        eintrag = {"provider": self.provider}
        if self.model:
            eintrag["model"] = self.model
        return eintrag

    def with_model(self, model: str) -> RoleBinding:
        return RoleBinding(self.role, self.provider, model, self.base_url, self.api_key,
                           self.params, self.source)


def role_block(config: SddConfig, role: str) -> dict | None:
    roles = (config.raw.get("llm") or {}).get("roles") or {}
    block = roles.get(role) if isinstance(roles, dict) else None
    return dict(block) if isinstance(block, dict) else None


def supervisor_mode(config: SddConfig) -> str:
    block = role_block(config, "supervisor") or {}
    return str(block.get("mode") or "inline")


def resolve_binding(config: SddConfig, role_def: RoleDefinition) -> RoleBinding:
    block = role_block(config, role_def.role)
    if block is not None:
        provider = block.get("provider") or "claude-cli"
        return RoleBinding(role_def.role, provider, str(block.get("model") or ""),
                           block.get("base_url"), _resolve_env_var(block.get("api_key")),
                           {k: v for k, v in block.items() if k not in
                            ("provider", "model", "base_url", "api_key", "mode")}, "roles")
    komponente = role_def.legacy_component
    default_block = "code_gen" if komponente == "orchestrator" else "completion"
    cfg = _resolve(config.raw, komponente, default_block)
    provider = cfg["provider"] or "claude-cli"
    params = {"temperature": cfg["temperature"], "thinking": cfg["enable_thinking"]}
    return RoleBinding(role_def.role, provider, cfg["model"] or "", cfg["base_url"],
                       cfg["api_key"], params, f"legacy:{komponente}")


def build_provider(config: SddConfig, binding: RoleBinding, role_def: RoleDefinition) -> Any:
    """Provider für die Belegung, umhüllt vom Usage-Decorator."""
    params = {**role_def.defaults, **binding.params}
    p = binding.provider
    if p == "claude-cli":
        from ..llm.providers.claude_cli import ClaudeCliCompletionProvider
        inner = ClaudeCliCompletionProvider(
            timeout=params.get("timeout_seconds") or config.llm_timeout())
    elif p == "anthropic":
        from ..llm.factory import _DEFAULT_ANTHROPIC_MODEL
        from ..llm.providers.anthropic import AnthropicCompletionProvider
        inner = AnthropicCompletionProvider(model=binding.model or _DEFAULT_ANTHROPIC_MODEL,
                                            api_key=binding.api_key,
                                            temperature=float(params.get("temperature") or 0.0))
    elif p == "openai-compat":
        if not binding.base_url or not binding.model:
            raise RoleConfigError(
                f"llm.roles.{binding.role}: base_url und model sind Pflicht für openai-compat.")
        from ..llm.providers.openai_compat import OpenAICompatCompletionProvider
        inner = OpenAICompatCompletionProvider(
            base_url=binding.base_url, model=binding.model, api_key=binding.api_key or "lm-studio",
            temperature=float(params.get("temperature") or 0.0),
            enable_thinking=bool(params.get("thinking", True)),
            top_p=params.get("top_p"), reasoning_effort=params.get("reasoning_effort"))
    else:
        raise RoleConfigError(f"llm.roles.{binding.role}: Provider {p!r} wird für Rollen nicht "
                              f"unterstützt (erlaubt: {', '.join(SUPPORTED)}).")
    return RecordingCompletionProvider(inner, component=f"role:{binding.role}",
                                       model=binding.model, root=config.root)


def role_config_issues(config: SddConfig) -> list[tuple[str, str, str]]:
    """(level, pfad, meldung) für `llm.roles` (FR-04): Fehler und Warnungen."""
    roles = (config.raw.get("llm") or {}).get("roles")
    if roles is None:
        return []
    if not isinstance(roles, dict):
        return [("error", "llm.roles", "muss ein Objekt sein")]
    issues: list[tuple[str, str, str]] = []
    for rolle, block in roles.items():
        pfad = f"llm.roles.{rolle}"
        if not isinstance(block, dict):
            issues.append(("error", pfad, "muss ein Objekt sein"))
            continue
        for key in sorted(set(block) - ROLE_KEYS):
            issues.append(("error", f"{pfad}.{key}", "unbekannter Parameter"))
        provider = block.get("provider") or "claude-cli"
        if provider not in SUPPORTED:
            issues.append(("error", f"{pfad}.provider",
                           f"{provider!r} ist für Rollen nicht erlaubt ({', '.join(SUPPORTED)})"))
            continue
        for key in sorted((set(block) & ROLE_KEYS) - SUPPORTED[provider]):
            issues.append(("warning", f"{pfad}.{key}", f"wird von {provider} ignoriert"))
        if "mode" in block and rolle != "supervisor":
            issues.append(("error", f"{pfad}.mode", "nur für die Rolle supervisor erlaubt"))
        if block.get("mode") not in (None, "inline", "session"):
            issues.append(("error", f"{pfad}.mode", "erlaubt: inline, session"))
        effort = block.get("reasoning_effort")
        if effort is not None and effort not in ("low", "medium", "high"):
            issues.append(("error", f"{pfad}.reasoning_effort", "erlaubt: low, medium, high"))
    if same_model_conflict(config):
        issues.append(("warning", "llm.roles.reviewer", SAME_MODEL_WARNING))
    return issues


def same_model_conflict(config: SddConfig) -> bool:
    """reviewer nutzt dasselbe Modell (Endpunkt und Name) wie implementer oder test_author."""
    from .roles import RoleError, load_role

    try:
        bindungen = {r: resolve_binding(config, load_role(config.root, r))
                     for r in ("reviewer", "implementer", "test_author")}
    except (RoleError, RuntimeError):
        return False
    reviewer = bindungen["reviewer"].endpoint
    return any(bindungen[r].endpoint == reviewer for r in ("implementer", "test_author"))
