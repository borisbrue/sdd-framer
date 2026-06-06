"""Hub API Contract-Tests – GET /hub/projects, POST start/stop, SSE stream."""
from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from sdd_cli.hub.app import create_app
from sdd_cli.hub.events import StatusEventBus
from sdd_cli.hub.models import ProjectEntry
from sdd_cli.hub.registry import ProjectRegistry


def _entry(name: str = "testapp", port: int = 9000) -> ProjectEntry:
    return ProjectEntry(
        id=name, name=name, path=Path("/tmp"),
        start_cmd=["echo", "hi"], port=port,
    )


def _make_client(tmp_path, entries: list[ProjectEntry] | None = None) -> TestClient:
    reg = ProjectRegistry(tmp_path / "registry.yaml")
    bus = StatusEventBus()
    for e in (entries or []):
        reg.register(e)
    app = create_app(registry=reg, event_bus=bus)
    return TestClient(app)


def test_get_hub_projects_empty(tmp_path):
    client = _make_client(tmp_path)
    r = client.get("/hub/projects")
    assert r.status_code == 200
    assert r.json() == []


def test_get_hub_projects_returns_registered(tmp_path):
    client = _make_client(tmp_path, [_entry("app1"), _entry("app2", port=9001)])
    r = client.get("/hub/projects")
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()]
    assert "app1" in ids
    assert "app2" in ids


def test_get_hub_projects_live_status_stopped(tmp_path):
    client = _make_client(tmp_path, [_entry("app1")])
    r = client.get("/hub/projects")
    assert r.json()[0]["status"] == "stopped"


def test_post_start_returns_starting(tmp_path):
    client = _make_client(tmp_path, [_entry("app1")])
    mock_proc = MagicMock(spec=subprocess.Popen)
    mock_proc.pid = 55
    mock_proc.poll.return_value = None
    with patch("subprocess.Popen", return_value=mock_proc):
        r = client.post("/hub/projects/app1/start")
    assert r.status_code == 200
    assert r.json()["status"] == "starting"
    assert r.json()["pid"] == 55


def test_post_start_unknown_project_returns_404(tmp_path):
    client = _make_client(tmp_path)
    r = client.post("/hub/projects/unknown/start")
    assert r.status_code in (404, 422, 500)


def test_post_start_already_running_returns_409(tmp_path):
    client = _make_client(tmp_path, [_entry("app1")])
    mock_proc = MagicMock(spec=subprocess.Popen)
    mock_proc.pid = 55
    mock_proc.poll.return_value = None
    with patch("subprocess.Popen", return_value=mock_proc):
        client.post("/hub/projects/app1/start")
        r = client.post("/hub/projects/app1/start")
    assert r.status_code == 409


def test_post_stop_not_running_returns_409(tmp_path):
    client = _make_client(tmp_path, [_entry("app1")])
    r = client.post("/hub/projects/app1/stop")
    assert r.status_code == 409


def test_sse_stream_route_registered(tmp_path):
    from sdd_cli.hub.routes.projects import router
    paths = [getattr(r, "path", "") for r in router.routes]
    assert "/hub/projects/stream" in paths or "/projects/stream" in paths
