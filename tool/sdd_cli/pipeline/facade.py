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

__all__ = ["JudgeUnavailable", "extract_json", "judge_provider", "measure_changed",
           "role_binding", "role_config_issues", "role_provider", "run_role", "unknown_checks"]


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


def run_role(role: RoleDefinition, provider: Any, sources: dict, *, run_id: str, attempt: int = 1,
             params: dict | None = None, lead: str = "", check_context: dict | None = None,
             task: dict | None = None) -> Any:
    """Ein Rollenaufruf nach dem festen Ablauf des RoleRunner (Nonce, Schema, Gate-Checks), z. B.
    für den Benchmark (SPEC-0056 FR-04). Ergebnis: RoleResult."""
    from .runner import RoleRunner

    return RoleRunner(run_id=run_id, spec_id="").run(
        role, provider, sources, attempt=attempt, params=params, lead=lead,
        check_context=check_context, task=task)


def measure_changed(root: Any, raw_config: dict, changed: list[str]) -> dict[str, dict]:
    """Architektur- und Lint-Gate auf geänderten Dateien (SPEC-0061 FR-07), für Messungen."""
    from .gates import architecture_gate, lint_gate

    return {g.gate: {"status": g.status, "reason": g.reason, "findings": g.findings}
            for g in (architecture_gate(root, raw_config, changed),
                      lint_gate(root, raw_config, changed))}


def role_binding(config: SddConfig, role: RoleDefinition) -> Any:
    """Aufgelöste Belegung einer Rolle (Provider, Modell, Endpunkt, Parameter), ohne Aufruf."""
    return resolve_binding(config, role)
