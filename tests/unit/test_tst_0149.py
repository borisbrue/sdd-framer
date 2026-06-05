# TST-0149 – DagScheduler: Abhängigkeiten, Slots, Observer-Dispatch (CON-0127)
# Spec: SPEC-0036 | Level: unit | Contract: CON-0127

import threading
from typing import Literal

import pytest

from sdd_cli.local_agent import DagScheduler, DagSchedulerError, SubAgentProxy
from sdd_cli.sub_agent import SubAgentResult
from sdd_cli.task_model import Complexity, ContextSize, Task, TaskType


def _task(title: str, deps: list[str] | None = None) -> Task:
    return Task(
        spec_id="SPEC-0036",
        title=title,
        description="desc",
        type=TaskType.CODE,
        complexity=Complexity.LOW,
        context_size=ContextSize.S,
        estimated_tokens=100,
        dependencies=deps or [],
    )


def _ok(task: Task) -> SubAgentResult:
    return SubAgentResult(task_id=task.id, task_title=task.title, success=True)


class _SyncProxy:
    """Synchronous mock proxy – records call order and task IDs."""

    def __init__(self, agent_type: str = "local", raises: Exception | None = None):
        self.agent_type = agent_type
        self.calls: list[str] = []
        self._raises = raises
        self._lock = threading.Lock()

    def execute(self, task: Task) -> SubAgentResult:
        with self._lock:
            self.calls.append(task.title)
        if self._raises:
            raise self._raises
        return _ok(task)


class _BarrierProxy:
    """Proxy that uses a barrier to prove parallel dispatch."""

    def __init__(self, n: int, agent_type: str = "local"):
        self.agent_type = agent_type
        self.barrier = threading.Barrier(n, timeout=2)
        self.calls: list[str] = []
        self._lock = threading.Lock()

    def execute(self, task: Task) -> SubAgentResult:
        with self._lock:
            self.calls.append(task.title)
        self.barrier.wait()  # all n tasks must be running simultaneously
        return _ok(task)


def _cloud_route(t: Task) -> Literal["local", "cloud"]:
    return "cloud"


def _local_route(t: Task) -> Literal["local", "cloud"]:
    return "local"


class TestTST0149:
    def test_root_tasks_dispatched_in_parallel(self) -> None:
        # INV-03+INV-02: beide root-Tasks (kein deps, max_parallel_local=2) → gleichzeitig gestartet
        a = _task("Task-A")
        b = _task("Task-B")
        proxy = _BarrierProxy(n=2)
        scheduler = DagScheduler(max_parallel_local=2, max_parallel_cloud=1)
        report = scheduler.run([a, b], _local_route, proxy, _SyncProxy("cloud"))
        assert not report.halted
        assert set(proxy.calls) == {"Task-A", "Task-B"}

    def test_dependent_task_runs_after_dependency(self) -> None:
        # INV-01: Task-B hängt von Task-A ab → B erst nach A completed
        a = _task("Task-A")
        b = _task("Task-B", deps=["Task-A"])
        call_order: list[str] = []
        lock = threading.Lock()

        class OrderProxy:
            agent_type = "local"
            def execute(self, task: Task) -> SubAgentResult:
                with lock:
                    call_order.append(task.title)
                return _ok(task)

        proxy = OrderProxy()
        scheduler = DagScheduler(max_parallel_local=2, max_parallel_cloud=1)
        report = scheduler.run([a, b], _local_route, proxy, _SyncProxy("cloud"))
        assert not report.halted
        assert call_order.index("Task-A") < call_order.index("Task-B")

    def test_slot_limit_enforced(self) -> None:
        # INV-02: max_parallel_local=2, 3 Tasks → nie mehr als 2 gleichzeitig
        a = _task("Task-A")
        b = _task("Task-B")
        c = _task("Task-C")
        concurrent_peak = [0]
        running = [0]
        lock = threading.Lock()

        class PeakProxy:
            agent_type = "local"
            barrier = threading.Barrier(2, timeout=2)
            _calls = []

            def execute(self, task: Task) -> SubAgentResult:
                with lock:
                    running[0] += 1
                    concurrent_peak[0] = max(concurrent_peak[0], running[0])
                # Try to wait for a second task — if only 2 max, barrier times out for 3rd
                try:
                    self.barrier.wait(timeout=0.5)
                except threading.BrokenBarrierError:
                    pass
                with lock:
                    running[0] -= 1
                return _ok(task)

        proxy = PeakProxy()
        scheduler = DagScheduler(max_parallel_local=2, max_parallel_cloud=1)
        report = scheduler.run([a, b, c], _local_route, proxy, _SyncProxy("cloud"))
        assert not report.halted
        assert concurrent_peak[0] <= 2

    def test_local_cloud_slots_independent(self) -> None:
        # INV-02: lokale und Cloud-Slots blockieren sich nicht gegenseitig
        a = _task("Task-A")
        b = _task("Task-B")
        local_proxy = _SyncProxy("local")
        cloud_proxy = _SyncProxy("cloud")

        def mixed_route(t: Task) -> Literal["local", "cloud"]:
            return "local" if t.title == "Task-A" else "cloud"

        scheduler = DagScheduler(max_parallel_local=2, max_parallel_cloud=1)
        report = scheduler.run([a, b], mixed_route, local_proxy, cloud_proxy)
        assert not report.halted
        assert "Task-A" in local_proxy.calls
        assert "Task-B" in cloud_proxy.calls

    def test_cyclic_dependency_raises_value_error(self) -> None:
        # INV-01: zirkuläre Abhängigkeit → ValueError, kein Task dispatcht
        a = _task("Task-A", deps=["Task-B"])
        b = _task("Task-B", deps=["Task-A"])
        proxy = _SyncProxy("local")
        scheduler = DagScheduler(max_parallel_local=2, max_parallel_cloud=1)

        with pytest.raises(ValueError, match="[Cc]ircular"):
            scheduler.run([a, b], _local_route, proxy, _SyncProxy("cloud"))

        assert proxy.calls == []

    def test_observer_dispatches_after_completion(self) -> None:
        # INV-04: nach Completion von Task-A → Observer dispatcht Task-B
        a = _task("Task-A")
        b = _task("Task-B", deps=["Task-A"])
        call_order: list[str] = []
        lock = threading.Lock()
        a_completed = threading.Event()

        class ObserverProxy:
            agent_type = "local"
            def execute(self, task: Task) -> SubAgentResult:
                with lock:
                    call_order.append(task.title)
                if task.title == "Task-A":
                    a_completed.set()
                else:
                    # B should only be dispatched AFTER A completed
                    assert a_completed.is_set(), "Task-B dispatched before Task-A completed"
                return _ok(task)

        proxy = ObserverProxy()
        scheduler = DagScheduler(max_parallel_local=2, max_parallel_cloud=1)
        report = scheduler.run([a, b], _local_route, proxy, _SyncProxy("cloud"))
        assert not report.halted
        assert call_order == ["Task-A", "Task-B"]
