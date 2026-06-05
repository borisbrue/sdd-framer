"""TST-0152: DagEventBus publish/subscribe — Event-Ordering, run_id-Isolation."""
from __future__ import annotations

import asyncio

from sdd_cli.dag_event import DagEvent, DagEventBus


def _ev(run_id: str, task_id: str, status: str = "running") -> DagEvent:
    return DagEvent(run_id=run_id, task_id=task_id, status=status)  # type: ignore[arg-type]


def _run(coro):
    return asyncio.run(coro)


async def _collect(bus: DagEventBus, run_id: str, publish_fn, close_after: float = 0.05) -> list[DagEvent]:
    result: list[DagEvent] = []

    async def _sub():
        async for ev in bus.subscribe(run_id):
            result.append(ev)

    task = asyncio.create_task(_sub())
    await asyncio.sleep(0)
    publish_fn()
    await asyncio.sleep(close_after)
    bus.close(run_id)
    await asyncio.wait_for(task, timeout=2.0)
    return result


def test_subscribe_receives_published_events():
    bus = DagEventBus()

    def publish():
        bus.publish(_ev("run-1", "t1", "running"))
        bus.publish(_ev("run-1", "t1", "done"))

    events = _run(_collect(bus, "run-1", publish))
    assert len(events) == 2
    assert events[0].status == "running"
    assert events[1].status == "done"


def test_event_ordering_fifo():
    bus = DagEventBus()

    def publish():
        for i in range(5):
            bus.publish(_ev("run-ord", f"task-{i}"))

    events = _run(_collect(bus, "run-ord", publish))
    assert [e.task_id for e in events] == [f"task-{i}" for i in range(5)]


def test_run_id_isolation():
    bus = DagEventBus()
    b_events: list[DagEvent] = []

    async def run():
        async def collect_b():
            async for ev in bus.subscribe("run-B"):
                b_events.append(ev)

        task = asyncio.create_task(collect_b())
        await asyncio.sleep(0)
        bus.publish(_ev("run-A", "t1"))  # soll NICHT bei B ankommen
        bus.publish(_ev("run-B", "t2"))
        await asyncio.sleep(0.05)
        bus.close("run-B")
        await asyncio.wait_for(task, timeout=2.0)

    _run(run())
    assert len(b_events) == 1
    assert b_events[0].task_id == "t2"


def test_multiple_subscribers_same_run():
    bus = DagEventBus()
    r1: list[DagEvent] = []
    r2: list[DagEvent] = []

    async def run():
        async def c1():
            async for ev in bus.subscribe("run-multi"):
                r1.append(ev)

        async def c2():
            async for ev in bus.subscribe("run-multi"):
                r2.append(ev)

        t1 = asyncio.create_task(c1())
        t2 = asyncio.create_task(c2())
        await asyncio.sleep(0)
        bus.publish(_ev("run-multi", "x"))
        await asyncio.sleep(0.05)
        bus.close("run-multi")
        await asyncio.wait_for(asyncio.gather(t1, t2), timeout=2.0)

    _run(run())
    assert len(r1) == 1
    assert len(r2) == 1


def test_publish_without_subscriber_does_not_raise():
    bus = DagEventBus()
    bus.publish(_ev("no-sub", "t1"))  # kein Exception erwartet
