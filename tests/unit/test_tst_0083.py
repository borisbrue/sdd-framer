# TST-0083 – Acceptance: Vollständiger Dev-Container-Stack
# Contracts: CON-0069, CON-0070, CON-0071, CON-0073
# Spec: SPEC-0022
from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

import pytest

from sdd_cli.dev_container import DevContainerManager, DockerRuntime
from sdd_cli.log_streamer import LogEventBus, LogStreamer


class TestTST0083:
    # Vollständiger Stack-Flow: build → up → log-publish → down (gemockt)
    def test_full_stack_flow_mocked(self) -> None:
        # Setup: echte LogEventBus, gemockte ContainerRuntime
        bus = LogEventBus(max_lines=500)
        runtime = MagicMock(spec=DockerRuntime)
        runtime.cli.return_value = "docker"
        runtime.inspect_status.return_value = None
        runtime.logs_popen.return_value = MagicMock(
            stdout=MagicMock(readline=MagicMock(return_value="")),
        )

        streamer = LogStreamer(bus, runtime)

        cfg = MagicMock()
        cfg.raw = {
            "docker": {
                "runtime": "docker",
                "image": "sdd-dev:latest",
                "dockerfile": ".sdd/Dockerfile",
                "compose_file": ".sdd/docker-compose.yml",
                "log_stream": {"enabled": True, "max_lines": 500},
            }
        }
        cfg.root = MagicMock()

        manager = DevContainerManager(cfg, runtime=runtime, log_streamer=streamer)

        # Schritt 1: build (CON-0069 G-01)
        with patch("pathlib.Path.exists", return_value=True):
            manager.build()
        runtime.build.assert_called_once_with("sdd-dev:latest", ".sdd/Dockerfile")

        # Schritt 2: up SPEC-0022 startet Compose + LogStreamer (CON-0069 G-05)
        manager.up("SPEC-0022")
        runtime.compose_up.assert_called_once_with(".sdd/docker-compose.yml", build=True)
        assert bus.has_stream("SPEC-0022")

        # Schritt 3: LogEventBus.publish → Zeile im Buffer (CON-0070 G-03)
        received: list[str] = []
        bus.subscribe("SPEC-0022", received.append)
        t_before = time.monotonic()
        bus.publish("SPEC-0022", "pytest: 5 passed in 0.2s")
        latency = time.monotonic() - t_before

        assert len(received) == 1
        data = json.loads(received[0])
        assert data["line"] == "pytest: 5 passed in 0.2s"
        assert data["spec_id"] == "SPEC-0022"
        # CON-0073: Latenz < 1 s (lokales publish ist instantan)
        assert latency < 1.0

        buf = bus.get_buffer("SPEC-0022")
        assert len(buf) >= 1

        # Schritt 4: down SPEC-0022 stoppt Compose + LogStreamer (CON-0069 G-06)
        manager.down("SPEC-0022")
        runtime.compose_down.assert_called_once_with(".sdd/docker-compose.yml")
        assert not bus.has_stream("SPEC-0022")

    # CON-0073: LogEventBus.publish Latenz < 1 s für 100 Zeilen
    def test_log_publish_latency_under_1s_for_100_lines(self) -> None:
        bus = LogEventBus(max_lines=500)
        received: list[str] = []
        bus.subscribe("SPEC-0022", received.append)
        bus.mark_active("SPEC-0022")

        t0 = time.monotonic()
        for i in range(100):
            bus.publish("SPEC-0022", f"line-{i}: output from container process")
        elapsed = time.monotonic() - t0

        assert len(received) == 100
        assert elapsed < 1.0  # 100 lokale publishes in < 1 s

    # CON-0070 G-03: Buffer-History bei Verbindungsaufbau
    def test_buffer_history_preserved_across_connect(self) -> None:
        bus = LogEventBus(max_lines=500)
        bus.mark_active("SPEC-0022")
        for i in range(10):
            bus.publish("SPEC-0022", f"startup-line-{i}")

        buf = bus.get_buffer("SPEC-0022")
        assert len(buf) == 10
        lines = [json.loads(m)["line"] for m in buf]
        assert lines[0] == "startup-line-0"
        assert lines[-1] == "startup-line-9"
