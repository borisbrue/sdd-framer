"""Hub ProcessManager – start/stop mit Mock-Subprocess, Crash-Detection."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sdd_cli.hub.events import StatusEventBus
from sdd_cli.hub.models import ProjectEntry
from sdd_cli.hub.process_manager import ProcessManager
from sdd_cli.hub.registry import ProjectRegistry


def _entry(name: str = "testapp") -> ProjectEntry:
    return ProjectEntry(
        id=name, name=name, path=Path("/tmp"),
        start_cmd=["echo", "hello"], port=9000,
    )


def _make_manager(tmp_path) -> tuple[ProcessManager, ProjectRegistry, StatusEventBus]:
    reg = ProjectRegistry(tmp_path / "registry.yaml")
    bus = StatusEventBus()
    manager = ProcessManager(reg, bus)
    return manager, reg, bus


def test_start_stores_pid(tmp_path):
    manager, reg, bus = _make_manager(tmp_path)
    reg.register(_entry("app"))
    mock_proc = MagicMock(spec=subprocess.Popen)
    mock_proc.pid = 42
    mock_proc.poll.return_value = None

    with patch("subprocess.Popen", return_value=mock_proc):
        manager.start("app")

    assert reg.get("app").status == "running"
    assert reg.get("app").pid == 42


def test_start_already_running_raises_409(tmp_path):
    from fastapi import HTTPException
    manager, reg, bus = _make_manager(tmp_path)
    reg.register(_entry("app"))
    mock_proc = MagicMock(spec=subprocess.Popen)
    mock_proc.pid = 42
    mock_proc.poll.return_value = None

    with patch("subprocess.Popen", return_value=mock_proc):
        manager.start("app")
        with pytest.raises(HTTPException) as exc:
            manager.start("app")
        assert exc.value.status_code == 409


def test_stop_updates_status(tmp_path):
    manager, reg, bus = _make_manager(tmp_path)
    reg.register(_entry("app"))
    mock_proc = MagicMock(spec=subprocess.Popen)
    mock_proc.pid = 42
    mock_proc.poll.return_value = None

    with patch("subprocess.Popen", return_value=mock_proc), \
         patch("os.killpg"), patch("os.getpgid", return_value=42):
        manager.start("app")
        manager.stop("app")

    assert reg.get("app").status == "stopped"
    assert reg.get("app").pid is None


def test_stop_not_running_raises_409(tmp_path):
    from fastapi import HTTPException
    manager, reg, _ = _make_manager(tmp_path)
    reg.register(_entry("app"))

    with pytest.raises(HTTPException) as exc:
        manager.stop("app")
    assert exc.value.status_code == 409


def test_get_live_status_stopped_when_no_process(tmp_path):
    manager, reg, _ = _make_manager(tmp_path)
    reg.register(_entry("app"))
    status, pid = manager.get_live_status("app")
    assert status == "stopped"
    assert pid is None


def test_start_publishes_event(tmp_path):
    manager, reg, bus = _make_manager(tmp_path)
    reg.register(_entry("app"))
    received = []

    import asyncio

    async def collect():
        async for ev in bus.subscribe("app"):
            received.append(ev)
            break

    mock_proc = MagicMock(spec=subprocess.Popen)
    mock_proc.pid = 99
    mock_proc.poll.return_value = None

    async def run():
        task = asyncio.create_task(collect())
        await asyncio.sleep(0)
        with patch("subprocess.Popen", return_value=mock_proc):
            manager.start("app")
        await asyncio.sleep(0.05)
        bus.close("app")
        await asyncio.wait_for(task, timeout=2.0)

    asyncio.run(run())
    assert len(received) == 1
    assert received[0].status == "running"
