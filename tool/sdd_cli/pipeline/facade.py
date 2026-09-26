"""Öffentliche Schnittstelle der Pipeline für die übrigen Schichten (SPEC-0062 FR-10, ADR-0006).

Facade: Außerhalb von `pipeline` und `entry` importiert niemand `mediator`, `runner`, `steps`,
`gates`, `providers`, `decisions` oder `context` (ARCH-05). Wer von dort etwas braucht, bekommt
es hier; öffentlich sind außerdem `monitor`, `store`, `schemas`, `roles`, `path_policy` und
`config_migration`.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .providers import RoleConfigError, build_provider, resolve_binding, role_config_issues
from .roles import RoleDefinition, RoleError, load_blueprint_role, load_role
from .runner import extract_json, unknown_checks

if TYPE_CHECKING:
    from ..config import SddConfig

__all__ = ["JudgeUnavailable", "extract_json", "judge_provider", "role_config_issues",
           "role_provider", "unknown_checks"]


class JudgeUnavailable(Exception):
    """Für die Rolle judge lässt sich kein Provider bauen."""


def role_provider(config: SddConfig, role: RoleDefinition) -> Any:
    """Provider für die konfigurierte Belegung einer Rolle (Factory, ARCH-03)."""
    return build_provider(config, resolve_binding(config, role), role)


def judge_provider(config: SddConfig) -> tuple[Any, str]:
    """Provider und Modellbezeichnung der Rolle `judge` (SPEC-0055 FR-12).

    Ist `.sdd/roles/judge.md` noch die alte Rubrikdatei aus SPEC-0054, gilt die Blueprint-Rolle.
    """
    try:
        rolle = load_role(config.root, "judge")
    except RoleError:
        rolle = load_blueprint_role("judge")
    try:
        bindung = resolve_binding(config, rolle)
        if bindung.is_session:
            raise JudgeUnavailable("llm.roles.judge darf nicht im Modus session laufen")
        return build_provider(config, bindung, rolle), bindung.model or bindung.provider
    except RoleConfigError as exc:
        raise JudgeUnavailable(str(exc)) from exc
