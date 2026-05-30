"""FlowSession State Machine + FlowSessionStore (SPEC-0032, CON-0115)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

SESSION_TTL_HOURS = 2
VALID_FLOW_TYPES = frozenset({"new-spec", "review", "implement", "hotfix"})

_NEW_SPEC_STEPS = [
    "Wie soll die neue Spec heißen?",
    "Welche Art von Feature? (feature/bugfix/refactor/infra)",
    "Kurzbeschreibung (1-3 Sätze):",
    "Owner (Standard: Boris):",
]
_HOTFIX_STEPS = [
    "Beschreibe den Bug:",
    "Betroffene Spec (optional, z.B. SPEC-0032 – leer lassen wenn unbekannt):",
]


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class FlowSession:
    session_id: str
    flow_type: str
    state: str  # awaiting_input | running | awaiting_decision | done | failed
    step_index: int
    answers: dict[str, str]
    current_prompt: str | None
    job_id: str | None
    spec_id: str | None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def touch(self) -> None:
        self.updated_at = _now()

    def is_expired(self) -> bool:
        return _now() - self.updated_at > timedelta(hours=SESSION_TTL_HOURS)

    def accepts_reply(self) -> bool:
        return self.state in ("awaiting_input", "awaiting_decision")


class FlowSessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, FlowSession] = {}

    def create(self, flow_type: str, spec_id: str | None = None) -> FlowSession:
        initial_state, first_prompt = _initial_state_and_prompt(flow_type, spec_id)
        session = FlowSession(
            session_id=str(uuid.uuid4()),
            flow_type=flow_type,
            state=initial_state,
            step_index=0,
            answers={},
            current_prompt=first_prompt,
            job_id=None,
            spec_id=spec_id,
        )
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> FlowSession | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if session.is_expired():
            del self._sessions[session_id]
            return None
        return session

    def save(self, session: FlowSession) -> None:
        session.touch()
        self._sessions[session.session_id] = session

    def active_flows(self) -> list[dict]:
        expired = [sid for sid, s in self._sessions.items() if s.is_expired()]
        for sid in expired:
            del self._sessions[sid]
        return [
            {"session_id": s.session_id, "type": s.flow_type, "state": s.state}
            for s in self._sessions.values()
            if s.state not in ("done", "failed")
        ]


def _initial_state_and_prompt(flow_type: str, spec_id: str | None) -> tuple[str, str]:
    if flow_type == "new-spec":
        return ("awaiting_input", _NEW_SPEC_STEPS[0])
    if flow_type == "hotfix":
        return ("awaiting_input", _HOTFIX_STEPS[0])
    if flow_type == "review":
        if spec_id:
            return ("awaiting_decision", f"Review-Analyse starten für {spec_id}? (ja/nein)")
        return ("awaiting_input", "Welche Spec soll reviewt werden? (z.B. SPEC-0032)")
    if flow_type == "implement":
        if spec_id:
            return ("awaiting_decision", f"Implementierung starten für {spec_id}? (ja/nein)")
        return ("awaiting_input", "Welche Spec soll implementiert werden? (z.B. SPEC-0032)")
    return ("awaiting_input", "Flow gestartet.")


def get_new_spec_steps() -> list[str]:
    return list(_NEW_SPEC_STEPS)


def get_hotfix_steps() -> list[str]:
    return list(_HOTFIX_STEPS)


_store = FlowSessionStore()


def get_flow_session_store() -> FlowSessionStore:
    return _store
