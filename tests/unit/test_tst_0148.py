# TST-0148 – LocalSubAgentProxy: Ausführung, Env-Override, Fehler-Eskalation (CON-0126)
# Spec: SPEC-0036 | Level: unit | Contract: CON-0126

import logging
import os
from unittest.mock import MagicMock, patch

import pytest

from sdd_cli.local_agent import (
    CloudSubAgentProxy,
    DagSchedulerError,
    LocalSubAgentProxy,
    SubAgentProxy,
)
from sdd_cli.sub_agent import SubAgentResult
from sdd_cli.task_model import Complexity, ContextSize, Task, TaskType


def _task(title: str = "Test Task") -> Task:
    return Task(
        spec_id="SPEC-0036",
        title=title,
        description="desc",
        type=TaskType.CODE,
        complexity=Complexity.LOW,
        context_size=ContextSize.S,
        estimated_tokens=100,
    )


def _ok_result(task: Task) -> SubAgentResult:
    return SubAgentResult(task_id=task.id, task_title=task.title, success=True)


class _DummyCloud:
    agent_type: str = "cloud"

    def __init__(self, result=None, raises=None):
        self._result = result
        self._raises = raises
        self.call_count = 0
        self.called_tasks = []

    def execute(self, task: Task) -> SubAgentResult:
        self.call_count += 1
        self.called_tasks.append(task)
        if self._raises:
            raise self._raises
        return self._result or _ok_result(task)


class TestTST0148:
    def _proxy(self, cloud=None) -> LocalSubAgentProxy:
        return LocalSubAgentProxy(
            proxy_url="http://localhost:4000",
            model="llama3.1:8b",
            api_key="secret-key",
            cloud_proxy=cloud or _DummyCloud(),
        )

    def test_env_override_correct(self) -> None:
        # INV-01: ANTHROPIC_BASE_URL und ANTHROPIC_API_KEY in Subprocess-Env gesetzt
        task = _task()
        captured_env = {}

        def fake_run(cmd, env, **kwargs):
            captured_env.update(env)
            m = MagicMock()
            m.returncode = 0
            return m

        with patch("sdd_cli.local_agent.subprocess.run", side_effect=fake_run):
            self._proxy().execute(task)

        assert captured_env["ANTHROPIC_BASE_URL"] == "http://localhost:4000"
        assert captured_env["ANTHROPIC_API_KEY"] == "secret-key"

    def test_host_env_unchanged_after_call(self) -> None:
        # INV-01: Prozess-weites os.environ unverändert nach Aufruf
        before = os.environ.copy()
        task = _task()

        def fake_run(cmd, env, **kwargs):
            m = MagicMock()
            m.returncode = 0
            return m

        with patch("sdd_cli.local_agent.subprocess.run", side_effect=fake_run):
            self._proxy().execute(task)

        assert "ANTHROPIC_BASE_URL" not in os.environ or \
               os.environ.get("ANTHROPIC_BASE_URL") == before.get("ANTHROPIC_BASE_URL")

    def test_api_key_not_in_logs(self, caplog) -> None:
        # INV-04: api_key erscheint nicht in Logs
        task = _task()
        cloud = _DummyCloud()

        def fake_run(cmd, env, **kwargs):
            raise ConnectionError("proxy down")

        with patch("sdd_cli.local_agent.subprocess.run", side_effect=fake_run):
            with caplog.at_level(logging.WARNING, logger="sdd_cli.local_agent"):
                try:
                    self._proxy(cloud=cloud).execute(task)
                except DagSchedulerError:
                    pass

        for record in caplog.records:
            assert "secret-key" not in record.getMessage()

    def test_connection_error_escalates_to_cloud(self) -> None:
        # INV-03: ConnectionError → sofort Cloud, kein lokaler Retry
        task = _task()
        cloud = _DummyCloud()

        with patch("sdd_cli.local_agent.subprocess.run", side_effect=ConnectionError("down")):
            result = self._proxy(cloud=cloud).execute(task)

        assert cloud.call_count == 1
        assert result.success is True

    def test_nonzero_exit_escalates_to_cloud(self) -> None:
        # Subprocess Exit-Code ≠ 0 → sofortige Cloud-Eskalation
        task = _task()
        cloud = _DummyCloud()

        def fake_run(cmd, env, **kwargs):
            m = MagicMock()
            m.returncode = 1
            m.stderr = "error output"
            return m

        with patch("sdd_cli.local_agent.subprocess.run", side_effect=fake_run):
            result = self._proxy(cloud=cloud).execute(task)

        assert cloud.call_count == 1
        assert result.success is True

    def test_cloud_escalation_failure_raises_dag_error(self) -> None:
        # Cloud-Eskalation schlägt fehl → DagSchedulerError
        task = _task()
        cloud = _DummyCloud(raises=RuntimeError("cloud down"))

        with patch("sdd_cli.local_agent.subprocess.run", side_effect=ConnectionError("local down")):
            with pytest.raises(DagSchedulerError):
                self._proxy(cloud=cloud).execute(task)

    def test_protocol_isinstance(self) -> None:
        # INV-02: Beide Proxys implementieren SubAgentProxy (runtime_checkable)
        cloud = _DummyCloud()
        local = self._proxy(cloud=cloud)
        cloud_proxy = CloudSubAgentProxy(spawn_fn=lambda t: _ok_result(t))

        assert isinstance(local, SubAgentProxy)
        assert isinstance(cloud_proxy, SubAgentProxy)
