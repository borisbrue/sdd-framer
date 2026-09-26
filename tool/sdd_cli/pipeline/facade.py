"""Öffentliche Schnittstelle der Pipeline für die übrigen Schichten (SPEC-0062 FR-10, ADR-0006).

Facade: Außerhalb von `pipeline` und `entry` importiert niemand `mediator`, `runner`, `steps`,
`gates`, `providers`, `decisions` oder `context` (ARCH-05). Wer von dort etwas braucht, bekommt
es hier; öffentlich sind außerdem `monitor`, `store`, `schemas`, `roles`, `path_policy` und
`config_migration`.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .providers import build_provider, resolve_binding, role_config_issues
from .roles import RoleDefinition
from .runner import extract_json, unknown_checks

if TYPE_CHECKING:
    from ..config import SddConfig

__all__ = ["extract_json", "role_config_issues", "role_provider", "unknown_checks"]


def role_provider(config: SddConfig, role: RoleDefinition) -> Any:
    """Provider für die konfigurierte Belegung einer Rolle (Factory, ARCH-03)."""
    return build_provider(config, resolve_binding(config, role), role)
