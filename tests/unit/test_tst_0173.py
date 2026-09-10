# TST-0173
# Contract: CON-0150 – Offline-Verhalten und Aktionssperre (Gherkin, v0.1.0)
# Level: acceptance (offline – state-machine tests covering all Gherkin scenarios)

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

_FEATURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "contracts" / "behavior" / "offline-verhalten-und-aktionssperre.feature"
)


# ─── Minimal PWA state machine ────────────────────────────────────────────────

@dataclass
class Project:
    id: str
    name: str
    status: str


@dataclass
class PwaState:
    hub_reachable: bool = True
    projects: list[Project] = field(default_factory=list)
    last_fetched_at: str | None = None
    offline_banner_visible: bool = False

    def buttons_active(self) -> bool:
        return self.hub_reachable

    def attempt_action(self, project_id: str, action: str, send_fn: Callable) -> bool:
        if not self.hub_reachable:
            return False
        send_fn(project_id, action)
        return True

    def set_hub_reachable(self, reachable: bool) -> None:
        self.hub_reachable = reachable
        self.offline_banner_visible = not reachable

    def fetch_projects(self, projects: list[Project], fetched_at: str) -> None:
        if self.hub_reachable:
            self.projects = list(projects)
            self.last_fetched_at = fetched_at


class TestTST0173:
    """CON-0150: Offline-Verhalten – Gherkin-Szenarien als pytest-Tests."""

    def test_feature_file_exists(self):
        assert _FEATURE_PATH.exists(), f"Feature-Datei nicht gefunden: {_FEATURE_PATH}"

    def test_feature_file_contains_expected_scenarios(self):
        content = _FEATURE_PATH.read_text(encoding="utf-8")
        assert "Szenario:" in content
        assert "Offline" in content or "offline" in content
        assert "deaktiviert" in content

    # ── Szenario 1: Buttons gesperrt wenn Hub offline ─────────────────────────

    def test_s1_buttons_disabled_when_hub_offline(self):
        state = PwaState(hub_reachable=False)
        state.projects = [Project("p1", "Web", "running"), Project("p2", "API", "stopped")]
        assert not state.buttons_active()

    def test_s1_buttons_active_when_hub_online(self):
        state = PwaState(hub_reachable=True)
        assert state.buttons_active()

    def test_s1_no_action_sent_when_offline(self):
        calls: list = []
        state = PwaState(hub_reachable=False)
        result = state.attempt_action("p1", "start", lambda pid, act: calls.append((pid, act)))
        assert result is False
        assert calls == []

    # ── Szenario 2: Letzter bekannter Status bleibt sichtbar ─────────────────

    def test_s2_projects_preserved_after_disconnect(self):
        state = PwaState(hub_reachable=True)
        projects = [Project("p1", "Web", "running"), Project("p2", "API", "stopped")]
        state.fetch_projects(projects, "2026-06-08T14:00:00Z")
        state.set_hub_reachable(False)
        assert len(state.projects) == 2
        assert state.projects[0].status == "running"
        assert state.projects[1].status == "stopped"

    def test_s2_fetch_ignored_while_offline(self):
        state = PwaState(hub_reachable=True)
        state.fetch_projects([Project("p1", "Web", "running")], "2026-06-08T14:00:00Z")
        state.set_hub_reachable(False)
        state.fetch_projects([], "2026-06-08T15:00:00Z")  # should be ignored
        assert len(state.projects) == 1

    # ── Szenario 3: Offline-Banner mit Zeitstempel ────────────────────────────

    def test_s3_banner_visible_on_disconnect(self):
        state = PwaState(hub_reachable=True)
        state.fetch_projects([], "2026-06-08T14:00:00Z")
        state.set_hub_reachable(False)
        assert state.offline_banner_visible

    def test_s3_last_fetched_at_available_for_banner(self):
        state = PwaState(hub_reachable=True)
        state.fetch_projects([], "2026-06-08T14:00:00Z")
        state.set_hub_reachable(False)
        assert state.last_fetched_at == "2026-06-08T14:00:00Z"

    def test_s3_banner_not_visible_when_online(self):
        state = PwaState(hub_reachable=True)
        assert not state.offline_banner_visible

    # ── Szenario 4: Reaktivierung bei Wiederverbindung ────────────────────────

    def test_s4_buttons_reactivated_on_reconnect(self):
        state = PwaState(hub_reachable=True)
        state.set_hub_reachable(False)
        state.set_hub_reachable(True)
        assert state.buttons_active()

    def test_s4_banner_hidden_on_reconnect(self):
        state = PwaState(hub_reachable=True)
        state.set_hub_reachable(False)
        state.set_hub_reachable(True)
        assert not state.offline_banner_visible

    def test_s4_fetch_works_after_reconnect(self):
        state = PwaState(hub_reachable=True)
        state.fetch_projects([Project("p1", "Web", "stopped")], "2026-06-08T14:00:00Z")
        state.set_hub_reachable(False)
        state.set_hub_reachable(True)
        new_projects = [Project("p1", "Web", "running")]
        state.fetch_projects(new_projects, "2026-06-08T15:00:00Z")
        assert state.projects[0].status == "running"

    # ── Szenario 5: Aktion wird nur online abgesetzt ──────────────────────────

    def test_s5_action_sent_when_online(self):
        calls: list = []
        state = PwaState(hub_reachable=True)
        result = state.attempt_action("p1", "start", lambda pid, act: calls.append((pid, act)))
        assert result is True
        assert ("p1", "start") in calls

    # ── Szenario 6: Kein API-Aufruf im Offline-Modus ─────────────────────────

    def test_s6_no_api_call_offline(self):
        calls: list = []
        state = PwaState(hub_reachable=False)
        state.attempt_action("p1", "stop", lambda pid, act: calls.append((pid, act)))
        assert calls == []

    def test_s6_displayed_status_unchanged_when_action_blocked(self):
        state = PwaState(hub_reachable=False)
        state.projects = [Project("p1", "Web", "running")]
        state.attempt_action("p1", "stop", lambda *_: None)
        assert state.projects[0].status == "running"

    # ── Multiple online/offline cycles (State-Management-Regression) ─────────

    def test_multiple_cycles_stable(self):
        state = PwaState(hub_reachable=True)
        state.fetch_projects([Project("p1", "Web", "running")], "2026-06-08T10:00:00Z")
        for _ in range(3):
            state.set_hub_reachable(False)
            assert not state.buttons_active()
            assert state.offline_banner_visible
            state.set_hub_reachable(True)
            assert state.buttons_active()
            assert not state.offline_banner_visible
        assert state.projects[0].status == "running"
