"""Hub StatusEventBus – publish, subscribe, close, project_id-Isolation."""
from __future__ import annotations

import asyncio

import pytest

from typing import Literal

from sdd_cli.hub.events import StatusEventBus
from sdd_cli.hub.models import StatusEvent

HubStatus = Literal["running", "stopped", "error"]


def _ev(project_id: str, status: HubStatus = "running") -> StatusEvent:
    return StatusEvent(id=project_id, status=status)


def _run(coro):
    return asyncio.run(coro)


async def _collect(bus: StatusEventBus, project_id: str, publish_fn, close_after: float = 0.05) -> list[StatusEvent]:
    result: list[StatusEvent] = []

    async def sub():
        async for ev in bus.subscribe(project_id):
            result.append(ev)

    task = asyncio.create_task(sub())
    await asyncio.sleep(0)
    publish_fn()
    await asyncio.sleep(close_after)
    bus.close(project_id)
    await asyncio.wait_for(task, timeout=2.0)
    return result


def test_subscribe_receives_events():
    bus = StatusEventBus()

    def publish():
        bus.publish(_ev("proj-1", "running"))
        bus.publish(_ev("proj-1", "stopped"))

    events = _run(_collect(bus, "proj-1", publish))
    assert len(events) == 2
    assert events[0].status == "running"
    assert events[1].status == "stopped"


def test_project_id_isolation():
    bus = StatusEventBus()
    b_events: list[StatusEvent] = []

    async def run():
        async def collect_b():
            async for ev in bus.subscribe("proj-B"):
                b_events.append(ev)

        task = asyncio.create_task(collect_b())
        await asyncio.sleep(0)
        bus.publish(_ev("proj-A", "running"))
        bus.publish(_ev("proj-B", "stopped"))
        await asyncio.sleep(0.05)
        bus.close("proj-B")
        await asyncio.wait_for(task, timeout=2.0)

    _run(run())
    assert len(b_events) == 1
    assert b_events[0].id == "proj-B"


def test_publish_without_subscriber_does_not_raise():
    bus = StatusEventBus()
    bus.publish(_ev("no-sub", "error"))


def test_multiple_subscribers_receive_same_event():
    bus = StatusEventBus()
    r1: list[StatusEvent] = []
    r2: list[StatusEvent] = []

    async def run():
        async def c1():
            async for ev in bus.subscribe("proj-multi"):
                r1.append(ev)

        async def c2():
            async for ev in bus.subscribe("proj-multi"):
                r2.append(ev)

        t1 = asyncio.create_task(c1())
        t2 = asyncio.create_task(c2())
        await asyncio.sleep(0)
        bus.publish(_ev("proj-multi", "running"))
        await asyncio.sleep(0.05)
        bus.close("proj-multi")
        await asyncio.wait_for(asyncio.gather(t1, t2), timeout=2.0)

    _run(run())
    assert len(r1) == 1
    assert len(r2) == 1
