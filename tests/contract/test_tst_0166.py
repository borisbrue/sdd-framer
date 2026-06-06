"""TST-0156: SchedulerCommand-Schema — Pflichtfelder, unbekannte Commands → 422 (CON-0132)."""
from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


def _make_app():
    from sdd_cli.web.api.routes.dag_monitor import router
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return app


def _run(coro):
    return asyncio.run(coro)


def _post(app, payload: dict) -> int:
    async def run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            return await c.post("/api/orchestrate/command/run-x", json=payload)
    return _run(run())


def test_valid_pause_command_returns_202():
    r = _post(_make_app(), {"command_type": "pause_task", "task_id": "t1"})
    assert r.status_code == 202
    assert r.json()["queued"] is True
    assert r.json()["command_type"] == "pause_task"


def test_unknown_command_type_returns_422():
    r = _post(_make_app(), {"command_type": "fly_to_moon", "task_id": "t1"})
    assert r.status_code == 422


def test_missing_task_id_returns_422():
    r = _post(_make_app(), {"command_type": "pause_task"})
    assert r.status_code == 422


def test_missing_command_type_returns_422():
    r = _post(_make_app(), {"task_id": "t1"})
    assert r.status_code == 422


@pytest.mark.parametrize("cmd_type", [
    "pause_task", "resume_task", "force_local",
    "force_cloud", "skip_task", "restart_task",
])
def test_all_valid_command_types_accepted(cmd_type):
    r = _post(_make_app(), {"command_type": cmd_type, "task_id": "any"})
    assert r.status_code == 202
