"""Der Health-Check des Eval-Containers hing an hartkodiertem `localhost`.

Der Container-Port wird per `-p <host_port>:<app_port>` auf IPv4
veroeffentlicht. Loest `localhost` auf einem System nur nach ::1 auf, ist der
Health-Check unerreichbar — egal wie lange er wartet. Der Host war zudem als
einziger Wert des container-Blocks nicht konfigurierbar.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

from sdd_cli.config import SddConfig
from sdd_cli.eval_container import EvalContainer, load_eval_container_config


def _cfg(container: dict | None = None) -> SddConfig:
    return SddConfig(root=Path("/tmp"),
                     raw={"evaluator": {"container": container or {}}})


class TestHostIsConfigurable:
    def test_default_is_ipv4_loopback(self):
        """127.0.0.1 passt zu dem, was -p tatsaechlich aufmacht."""
        assert load_eval_container_config(_cfg()).host == "127.0.0.1"

    def test_config_value_wins(self):
        cfg = _cfg({"host": "10.0.0.5"})
        assert load_eval_container_config(cfg).host == "10.0.0.5"

    def test_base_url_uses_the_configured_host(self):
        container = EvalContainer(_cfg({"host": "10.0.0.5", "host_port": 19000}))
        with patch.object(EvalContainer, "_start", lambda self: None):
            base_url, name = container.__enter__()
        assert base_url == "http://10.0.0.5:19000"
        assert name == "sdd-eval-runner"

    def test_base_url_no_longer_says_localhost(self):
        container = EvalContainer(_cfg())
        with patch.object(EvalContainer, "_start", lambda self: None):
            base_url, _ = container.__enter__()
        assert "localhost" not in base_url


class TestBothAddressFamiliesAreProbed:
    def test_ipv4_and_ipv6_are_tried(self):
        urls = EvalContainer(_cfg())._health_urls()
        assert any("127.0.0.1" in u for u in urls)
        assert any("[::1]" in u for u in urls), "IPv6-Fallback fehlt"

    def test_configured_host_comes_first(self):
        urls = EvalContainer(_cfg({"host": "10.0.0.5"}))._health_urls()
        assert urls[0].startswith("http://10.0.0.5:")

    def test_no_duplicate_when_host_is_a_loopback(self):
        urls = EvalContainer(_cfg({"host": "127.0.0.1"}))._health_urls()
        assert len(urls) == len(set(urls)) == 2

    def test_health_path_is_kept(self):
        urls = EvalContainer(_cfg({"health_path": "/healthz"}))._health_urls()
        assert all(u.endswith("/healthz") for u in urls)


class TestLogsSurviveTheTeardown:
    def test_logs_are_fetched_before_the_container_stops(self):
        """Vorher stand self._stop() vor der f-String-Auswertung: die
        Fehlermeldung enthielt zuverlaessig "no such container" statt der
        Diagnose, fuer die sie gedacht war."""
        container = EvalContainer(_cfg({"health_timeout_secs": 0}))
        container._started = True
        reihenfolge: list[str] = []

        def fake_logs(lines: int = 30) -> str:
            reihenfolge.append("logs")
            return "INFO: Application startup complete."

        def fake_stop() -> None:
            reihenfolge.append("stop")
            container._started = False

        with patch.object(container, "_fetch_logs", fake_logs), \
             patch.object(container, "_stop", fake_stop):
            try:
                container._wait_healthy()
            except RuntimeError as exc:
                meldung = str(exc)

        assert reihenfolge == ["logs", "stop"], f"Reihenfolge war {reihenfolge}"
        assert "Application startup complete" in meldung

    def test_error_names_every_tried_url(self):
        container = EvalContainer(_cfg({"health_timeout_secs": 0}))
        container._started = True
        with patch.object(container, "_fetch_logs", lambda lines=30: ""), \
             patch.object(container, "_stop", lambda: None):
            try:
                container._wait_healthy()
            except RuntimeError as exc:
                meldung = str(exc)
        assert "127.0.0.1" in meldung and "[::1]" in meldung
