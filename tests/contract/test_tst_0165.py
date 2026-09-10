"""TST-0155: SSE-Endpoint — Event-Format, Content-Type (CON-0131)."""
from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


def _make_app():
    from sdd_cli.web.api.routes.dag_monitor import router
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return app


def _run(coro):
    return asyncio.run(coro)


def test_stream_content_type():
    from sdd_cli.dag_event import get_event_bus
    app = _make_app()
    bus = get_event_bus()

    async def run():
        async def _close():
            await asyncio.sleep(0.05)
            bus.close("run-ct")

        asyncio.create_task(_close())

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            async with c.stream("GET", "/api/orchestrate/stream/run-ct") as r:
                assert r.status_code == 200
                assert "text/event-stream" in r.headers["content-type"]
                lines = [ln async for ln in r.aiter_lines() if ln.strip()]
                assert any(ln.startswith(":") for ln in lines)

    _run(run())


def test_stream_delivers_published_events():
    from sdd_cli.dag_event import DagEvent, get_event_bus
    app = _make_app()
    bus = get_event_bus()
    received: list[dict] = []

    async def run():
        async def publish():
            await asyncio.sleep(0.05)
            bus.publish(DagEvent(run_id="run-ev2", task_id="t1", status="running"))
            await asyncio.sleep(0.05)
            bus.close("run-ev2")

        asyncio.create_task(publish())

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            async with c.stream("GET", "/api/orchestrate/stream/run-ev2") as r:
                async for line in r.aiter_lines():
                    if line.startswith("data:"):
                        received.append(json.loads(line[5:].strip()))
                    if received:
                        break

    _run(run())
    assert len(received) >= 1
    assert received[0]["task_id"] == "t1"
    assert received[0]["status"] == "running"


def test_runs_endpoint_returns_list():
    app = _make_app()

    async def run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            return await c.get("/api/orchestrate/runs")

    r = _run(run())
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_runs_endpoint_shows_registered_run():
    from sdd_cli.web.api.routes.dag_monitor import register_run
    register_run("run-reg-test", "SPEC-REG")
    app = _make_app()

    async def run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            return await c.get("/api/orchestrate/runs")

    r = _run(run())
    ids = [e["run_id"] for e in r.json()]
    assert "run-reg-test" in ids
