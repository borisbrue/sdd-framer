"""Lokale Sub-Agenten-Delegation und DAG-Scheduler für SPEC-0036.

Proxy Pattern (Refactoring Guru): LocalSubAgentProxy implementiert SubAgentProxy-Protocol,
  startet claude CLI-Subprocess mit ANTHROPIC_BASE_URL-Override.
Observer Pattern: DagScheduler dispatcht nach Task-Completion ereignisgesteuert.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from typing import Callable, Literal, Protocol, runtime_checkable

from .sub_agent import OrchestratorReport, SubAgentResult
from .task_model import Task

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LocalAgentConfig:
    enabled: bool
    proxy_url: str
    model: str
    context_window: int
    context_reserve_tokens: int
    max_parallel_local: int
    max_parallel_cloud: int
    api_key: str
    health_check: bool = True

    @classmethod
    def from_dict(cls, d: dict) -> "LocalAgentConfig":
        api_key_raw = str(d.get("api_key", "local-key"))
        if api_key_raw.startswith("${") and api_key_raw.endswith("}"):
            env_var = api_key_raw[2:-1]
            api_key_raw = os.environ.get(env_var, api_key_raw)
        return cls(
            enabled=bool(d.get("enabled", False)),
            proxy_url=str(d.get("proxy_url", "")),
            model=str(d.get("model", "")),
            context_window=int(d.get("context_window", 0)),
            context_reserve_tokens=int(d.get("context_reserve_tokens", 8192)),
            max_parallel_local=int(d.get("max_parallel_local", 4)),
            max_parallel_cloud=int(d.get("max_parallel_cloud", 2)),
            api_key=api_key_raw,
            health_check=bool(d.get("health_check", True)),
        )

    @classmethod
    def from_sdd_config(cls, config) -> "LocalAgentConfig | None":
        raw = config.raw.get("local_agent")
        if raw is None:
            return None
        return cls.from_dict(raw)


# ─────────────────────────────────────────────────────────────────────────────
# Exceptions + Protocol
# ─────────────────────────────────────────────────────────────────────────────

class DagSchedulerError(Exception):
    pass


@runtime_checkable
class SubAgentProxy(Protocol):
    agent_type: str

    def execute(self, task: Task) -> SubAgentResult: ...


# ─────────────────────────────────────────────────────────────────────────────
# Proxies
# ─────────────────────────────────────────────────────────────────────────────

def _build_prompt(task: Task) -> str:
    parts = [f"Task: {task.title}", f"Description: {task.description}"]
    if task.con_ids:
        parts.append(f"Contracts: {', '.join(task.con_ids)}")
    if task.test_ids:
        parts.append(f"Tests: {', '.join(task.test_ids)}")
    return "\n".join(parts)


class LocalSubAgentProxy:
    """Proxy Pattern: startet claude CLI-Subprocess mit lokalem Proxy-URL (CON-0126)."""

    agent_type: str = "local"

    def __init__(
        self,
        proxy_url: str,
        model: str,
        api_key: str,
        cloud_proxy: SubAgentProxy,
    ) -> None:
        self.proxy_url = proxy_url
        self.model = model
        self._api_key = api_key
        self._cloud_proxy = cloud_proxy

    def execute(self, task: Task) -> SubAgentResult:
        """INV-01: env nur als Subprocess-Env. INV-03: sofortige Cloud-Eskalation bei Fehler.
        INV-04: api_key erscheint nicht in Logs."""
        claude = shutil.which("claude") or "claude"
        prompt = _build_prompt(task)
        env = os.environ.copy()
        env["ANTHROPIC_BASE_URL"] = self.proxy_url
        env["ANTHROPIC_API_KEY"] = self._api_key  # not logged

        try:
            proc = subprocess.run(
                [claude, "--print", "--dangerously-skip-permissions", "-p", prompt],
                env=env,
                capture_output=True,
                text=True,
                timeout=600,
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"claude subprocess exited with code {proc.returncode}"
                )
            return SubAgentResult(
                task_id=task.id,
                task_title=task.title,
                success=True,
            )
        except Exception as local_exc:
            logger.warning(
                "[LOCAL FAILURE] task_id=%s type=%s — escalating to cloud",
                task.id,
                type(local_exc).__name__,
            )
            try:
                return self._cloud_proxy.execute(task)
            except Exception as cloud_exc:
                raise DagSchedulerError(
                    f"Task {task.id!r} failed on both local and cloud."
                ) from cloud_exc


class CloudSubAgentProxy:
    """Wraps a spawn function with 1-retry logic (CON-0126 INV-03 cloud path)."""

    agent_type: str = "cloud"

    def __init__(self, spawn_fn: Callable[[Task], SubAgentResult]) -> None:
        self._spawn_fn = spawn_fn

    def execute(self, task: Task) -> SubAgentResult:
        last_exc: Exception | None = None
        for _ in range(2):  # initial attempt + 1 retry
            try:
                return self._spawn_fn(task)
            except Exception as exc:
                last_exc = exc
        raise DagSchedulerError(
            f"Cloud sub-agent failed for task {task.id!r}: {last_exc}"
        ) from last_exc


# ─────────────────────────────────────────────────────────────────────────────
# DAG-Scheduler
# ─────────────────────────────────────────────────────────────────────────────

class DagScheduler:
    """Observer Pattern: ereignisgesteuerter Task-Dispatch nach Completion (CON-0127)."""

    def __init__(
        self,
        max_parallel_local: int,
        max_parallel_cloud: int,
    ) -> None:
        self.max_parallel_local = max_parallel_local
        self.max_parallel_cloud = max_parallel_cloud

    def run(
        self,
        tasks: list[Task],
        route_fn: Callable[[Task], Literal["local", "cloud"]],
        local_proxy: SubAgentProxy,
        cloud_proxy: SubAgentProxy,
        *,
        spec_id: str = "",
    ) -> OrchestratorReport:
        """INV-01: depends_on strikt. INV-02: Slot-Limits nie überschritten.
        INV-03: root-Tasks sofort. INV-04: kein Polling."""
        self._validate_no_cycles(tasks)

        title_to_id = {t.title: t.id for t in tasks}
        deps_by_id: dict[str, set[str]] = {
            t.id: {title_to_id[dep] for dep in t.dependencies if dep in title_to_id}
            for t in tasks
        }

        completed_ids: set[str] = set()
        pending_ids: set[str] = {t.id for t in tasks}
        running_ids: set[str] = set()
        local_running = 0
        cloud_running = 0
        report = OrchestratorReport(spec_id=spec_id)

        def is_ready(t: Task) -> bool:
            return (
                t.id in pending_ids
                and t.id not in running_ids
                and deps_by_id[t.id].issubset(completed_ids)
            )

        def dispatch_ready(futures_map: dict[Future, tuple[Task, str]]) -> None:
            nonlocal local_running, cloud_running
            for t in list(tasks):
                if not is_ready(t):
                    continue
                route = route_fn(t)
                if route == "local" and local_running < self.max_parallel_local:
                    local_running += 1
                    running_ids.add(t.id)
                    pending_ids.discard(t.id)
                    f = executor.submit(local_proxy.execute, t)
                    futures_map[f] = (t, "local")
                    logger.info(
                        "[LOCAL: %s] %s", local_proxy.model if hasattr(local_proxy, "model") else "?", t.title
                    )
                elif route == "cloud" and cloud_running < self.max_parallel_cloud:
                    cloud_running += 1
                    running_ids.add(t.id)
                    pending_ids.discard(t.id)
                    f = executor.submit(cloud_proxy.execute, t)
                    futures_map[f] = (t, "cloud")
                    logger.info("[CLOUD] %s", t.title)

        max_workers = max(1, self.max_parallel_local + self.max_parallel_cloud)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures_map: dict[Future, tuple[Task, str]] = {}
            dispatch_ready(futures_map)

            while futures_map:
                done, _ = wait(list(futures_map.keys()), return_when=FIRST_COMPLETED)
                for f in done:
                    if f not in futures_map:
                        continue
                    t, route = futures_map.pop(f)
                    running_ids.discard(t.id)
                    if route == "local":
                        local_running -= 1
                    else:
                        cloud_running -= 1

                    try:
                        result = f.result()
                        if not isinstance(result, SubAgentResult):
                            result = SubAgentResult(
                                task_id=t.id, task_title=t.title, success=True
                            )
                        completed_ids.add(t.id)
                        report.completed_tasks.append(result)
                        dispatch_ready(futures_map)  # Observer: newly unblocked tasks
                    except (DagSchedulerError, Exception) as exc:
                        report.failed_task = SubAgentResult(
                            task_id=t.id, task_title=t.title, success=False,
                            error=str(exc),
                        )
                        report.halted = True
                        for pending_f in list(futures_map.keys()):
                            pending_f.cancel()
                        futures_map.clear()
                        break

        return report

    @staticmethod
    def _validate_no_cycles(tasks: list[Task]) -> None:
        from .decompose import detect_circular_dependencies
        circular = detect_circular_dependencies(tasks)
        if circular:
            raise ValueError(
                f"Circular dependencies detected in task(s): {circular}"
            )
