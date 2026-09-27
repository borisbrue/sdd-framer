"""Provider je Rolle (SPEC-0053 FR-04, SPEC-0061 FR-04), Strategy über die Provider-Factory.

Auflösung eines Aufrufs (CON-0213 INV-04): `by_complexity[komplexität]` → `profile` bzw. eigene
Parameter von `llm.roles.<rolle>` → Komponentenblock aus `legacy_component` der Rollendatei (wie in
CON-0023 G-02) → Builtin `claude-cli`. Eine Belegung kann `session` sein: dann arbeitet Claude Code
im Dialog statt eines Modells. Jeder Provider ist vom Usage-Decorator aus SPEC-0060 umhüllt.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..llm.factory import _resolve, _resolve_env_var

if TYPE_CHECKING:
    from ..config import SddConfig
    from .roles import RoleDefinition

PROFILE_KEYS = frozenset({"provider", "model", "base_url", "api_key", "temperature", "top_p",
                          "max_output_tokens", "thinking", "reasoning_effort", "timeout_seconds",
                          "requests_per_minute", "max_concurrent", "seed"})
ROLE_KEYS = PROFILE_KEYS | {"mode", "profile", "by_complexity"}
SESSION = "session"
COMPLEXITIES = ("low", "medium", "high")
# by_complexity wirkt nur für Rollen, die an einem Task arbeiten (CON-0212 INV-02).
TASK_ROLES = ("test_author", "implementer", "reviewer")
_STEUERUNG = {"mode", "profile", "by_complexity"}
SUPPORTED = {
    "claude-cli": frozenset({"provider", "model", "timeout_seconds"} | _STEUERUNG),
    "anthropic": frozenset({"provider", "model", "api_key", "temperature", "max_output_tokens",
                            "timeout_seconds"} | _STEUERUNG),
    "openai-compat": frozenset({"provider", "model", "base_url", "api_key", "temperature",
                                "top_p", "max_output_tokens", "thinking", "reasoning_effort",
                                "timeout_seconds"} | _STEUERUNG),
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
    source: str  # "roles" | "profile:<name>" | "legacy:<komponente>" | "session"

    @property
    def is_session(self) -> bool:
        return self.provider == SESSION

    @property
    def endpoint(self) -> tuple[str, str | None, str]:
        return (self.provider, self.base_url, self.model)

    def describe(self) -> dict:
        if self.is_session:
            return {"mode": SESSION}
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


def profiles(config: SddConfig) -> dict[str, dict]:
    daten = (config.raw.get("llm") or {}).get("profiles") or {}
    return {k: dict(v) for k, v in daten.items() if isinstance(v, dict)} if isinstance(
        daten, dict) else {}


def _aus_block(role: str, block: dict, source: str) -> RoleBinding:
    provider = block.get("provider") or "claude-cli"
    return RoleBinding(role, provider, str(block.get("model") or ""), block.get("base_url"),
                       _resolve_env_var(block.get("api_key")),
                       {k: v for k, v in block.items() if k in PROFILE_KEYS and k not in
                        ("provider", "model", "base_url", "api_key")}, source)


def profile_binding(config: SddConfig, role: str, name: str) -> RoleBinding:
    if name == SESSION:
        return RoleBinding(role, SESSION, "", None, None, {}, SESSION)
    profil = profiles(config).get(name)
    if profil is None:
        raise RoleConfigError(f"llm.roles.{role}: Profil {name!r} fehlt in llm.profiles.")
    return _aus_block(role, profil, f"profile:{name}")


def resolve_binding(config: SddConfig, role_def: RoleDefinition,
                    complexity: str | None = None) -> RoleBinding:
    """Belegung einer Rolle, optional für einen Task mit `complexity` (CON-0213 INV-04)."""
    rolle = role_def.role
    block = role_block(config, rolle)
    if block is not None:
        stufen = block.get("by_complexity") or {}
        if complexity and rolle in TASK_ROLES and complexity in stufen:
            return profile_binding(config, rolle, str(stufen[complexity]))
        if block.get("mode") == SESSION and rolle != "supervisor":
            return profile_binding(config, rolle, SESSION)
        if block.get("profile"):
            return profile_binding(config, rolle, str(block["profile"]))
        if block.get("provider") or block.get("model"):
            return _aus_block(rolle, block, "roles")
    komponente = role_def.legacy_component
    default_block = "code_gen" if komponente == "orchestrator" else "completion"
    cfg = _resolve(config.raw, komponente, default_block)
    provider = cfg["provider"] or "claude-cli"
    params = {"temperature": cfg["temperature"], "thinking": cfg["enable_thinking"]}
    return RoleBinding(rolle, provider, cfg["model"] or "", cfg["base_url"],
                       cfg["api_key"], params, f"legacy:{komponente}")


def all_bindings(config: SddConfig, role_def: RoleDefinition) -> list[RoleBinding]:
    """Alle Belegungen einer Rolle (Basis und je Komplexität), z. B. für Start-Prüfung und test-llm."""
    bindungen = [resolve_binding(config, role_def)]
    for stufe in COMPLEXITIES:
        bindungen.append(resolve_binding(config, role_def, stufe))
    return bindungen


def build_provider(config: SddConfig, binding: RoleBinding, role_def: RoleDefinition) -> Any:
    """Provider für die Belegung; gebaut von der Factory (SPEC-0059 FR-08, ARCH-03)."""
    from ..llm.factory import get_role_provider

    try:
        return get_role_provider(config, role=binding.role, provider=binding.provider,
                                 model=binding.model, base_url=binding.base_url,
                                 api_key=binding.api_key,
                                 params={**role_def.defaults, **binding.params})
    except ValueError as exc:
        raise RoleConfigError(str(exc)) from exc


def _profil_issues(name: str, profil: object) -> list[tuple[str, str, str]]:
    pfad = f"llm.profiles.{name}"
    if not isinstance(profil, dict):
        return [("error", pfad, "muss ein Objekt sein")]
    issues = [("error", f"{pfad}.{k}", "unbekannter Parameter")
              for k in sorted(set(profil) - PROFILE_KEYS)]
    provider = profil.get("provider")
    if provider not in SUPPORTED:
        issues.append(("error", f"{pfad}.provider",
                       f"Pflicht, erlaubt: {', '.join(SUPPORTED)}"))
    else:
        issues += [("warning", f"{pfad}.{k}", f"wird von {provider} ignoriert")
                   for k in sorted((set(profil) & PROFILE_KEYS) - SUPPORTED[provider])]
    return issues


def role_config_issues(config: SddConfig) -> list[tuple[str, str, str]]:
    """(level, pfad, meldung) für `llm.roles` und `llm.profiles` (SPEC-0053 FR-04, SPEC-0061)."""
    llm = config.raw.get("llm") or {}
    roles, profile = llm.get("roles"), llm.get("profiles")
    if roles is None and profile is None:
        return []
    issues: list[tuple[str, str, str]] = []
    if profile is not None and not isinstance(profile, dict):
        issues.append(("error", "llm.profiles", "muss ein Objekt sein"))
        profile = {}
    for name, profil in (profile or {}).items():
        issues += _profil_issues(name, profil)
    bekannt = set(profile or {}) | {SESSION}
    if roles is not None and not isinstance(roles, dict):
        return [*issues, ("error", "llm.roles", "muss ein Objekt sein")]
    for rolle, block in (roles or {}).items():
        pfad = f"llm.roles.{rolle}"
        if not isinstance(block, dict):
            issues.append(("error", pfad, "muss ein Objekt sein"))
            continue
        for key in sorted(set(block) - ROLE_KEYS):
            issues.append(("error", f"{pfad}.{key}", "unbekannter Parameter"))
        if block.get("profile") and block.get("provider"):
            issues.append(("error", pfad, "profile und provider schließen sich aus"))
        if block.get("profile") and block["profile"] not in bekannt - {SESSION}:
            issues.append(("error", f"{pfad}.profile",
                           f"Profil {block['profile']!r} fehlt in llm.profiles"))
        stufen = block.get("by_complexity")
        if stufen is not None:
            if not isinstance(stufen, dict):
                issues.append(("error", f"{pfad}.by_complexity", "muss ein Objekt sein"))
                stufen = {}
            elif rolle not in TASK_ROLES:
                issues.append(("warning", f"{pfad}.by_complexity",
                               "wirkt nur für test_author, implementer und reviewer"))
            for stufe, ziel in stufen.items():
                if stufe not in COMPLEXITIES:
                    issues.append(("error", f"{pfad}.by_complexity.{stufe}",
                                   "erlaubt: low, medium, high"))
                elif ziel not in bekannt:
                    issues.append(("error", f"{pfad}.by_complexity.{stufe}",
                                   f"Profil {ziel!r} fehlt in llm.profiles"))
        provider = block.get("provider") or "claude-cli"
        if provider not in SUPPORTED:
            issues.append(("error", f"{pfad}.provider",
                           f"{provider!r} ist für Rollen nicht erlaubt ({', '.join(SUPPORTED)})"))
            continue
        for key in sorted((set(block) & ROLE_KEYS) - SUPPORTED[provider]):
            issues.append(("warning", f"{pfad}.{key}", f"wird von {provider} ignoriert"))
        if block.get("mode") not in (None, "inline", SESSION):
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
    except (RoleError, RoleConfigError, RuntimeError):
        return False
    reviewer = bindungen["reviewer"]
    if reviewer.is_session:
        return False
    return any(bindungen[r].endpoint == reviewer.endpoint for r in ("implementer", "test_author"))
