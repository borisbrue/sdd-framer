"""TST-0198 – Async TDD-Loop: test → implement → pytest (LocalLLMExecutor) (Unit)
Spec: SPEC-0045 · Contract: CON-0172
"""
import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

@dataclass
class TDDLoopResult:
    status: str          # "pass" | "fail"
    pytest_stdout: str
    pytest_returncode: int
    iteration: int
    error: str | None = None


@dataclass
class TaskContext:
    id: str
    description: str
    affected_files: list[str] = field(default_factory=list)
    contract_content: str = ""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAsyncTDDLoop:
    @pytest.fixture
    def tmp_workspace(self, tmp_path: Path) -> Path:
        (tmp_path / "tests" / "unit").mkdir(parents=True)
        return tmp_path

    @pytest.fixture
    def mock_completion_provider(self):
        provider = MagicMock()
        provider.complete = MagicMock(return_value=MagicMock(
            text="def test_foo(): assert foo() == 1"
        ))
        return provider

    @pytest.mark.asyncio
    async def test_test_written_before_implementation(self, tmp_workspace, mock_completion_provider):
        """INV-01: Testdatei muss vor Implementierungsdatei auf Disk existieren."""
        write_order = []

        async def mock_write(path: Path, content: str):
            write_order.append(path.name)

        with patch(
            "tool.sdd_cli.task_routing.local_llm.LocalLLMExecutor._write_file",
            side_effect=mock_write,
        ), patch(
            "tool.sdd_cli.task_routing.local_llm.get_completion_provider",
            return_value=mock_completion_provider,
        ):
            from tool.sdd_cli.task_routing.local_llm import LocalLLMExecutor
            executor = LocalLLMExecutor()
            task = TaskContext(id="TSK-001", description="Implement foo()")
            await executor.execute(task, workspace=tmp_workspace, iteration=1)

        test_idx = next(i for i, n in enumerate(write_order) if n.startswith("test_"))
        impl_idx = next(i for i, n in enumerate(write_order) if not n.startswith("test_"))
        assert test_idx < impl_idx, "Testdatei muss vor Implementierung geschrieben werden"

    @pytest.mark.asyncio
    async def test_test_file_naming_convention(self, tmp_workspace, mock_completion_provider):
        """INV-02: Testdatei liegt unter tests/unit/test_<task_id>.py."""
        with patch(
            "tool.sdd_cli.task_routing.local_llm.get_completion_provider",
            return_value=mock_completion_provider,
        ), patch(
            "tool.sdd_cli.task_routing.local_llm.LocalLLMExecutor._run_pytest",
            new_callable=AsyncMock,
            return_value=(0, "1 passed"),
        ):
            from tool.sdd_cli.task_routing.local_llm import LocalLLMExecutor
            executor = LocalLLMExecutor()
            task = TaskContext(id="TSK-042", description="Implement bar()")
            await executor.execute(task, workspace=tmp_workspace, iteration=1)

        expected = tmp_workspace / "tests" / "unit" / "test_TSK-042.py"
        assert expected.exists(), f"Testdatei erwartet unter {expected}"

    @pytest.mark.asyncio
    async def test_pytest_called_via_async_subprocess(self, tmp_workspace, mock_completion_provider):
        """INV-03: pytest wird via asyncio.create_subprocess_exec aufgerufen."""
        with patch(
            "tool.sdd_cli.task_routing.local_llm.get_completion_provider",
            return_value=mock_completion_provider,
        ), patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_proc:
            mock_proc.return_value = MagicMock(
                returncode=0,
                communicate=AsyncMock(return_value=(b"1 passed", b"")),
            )
            from tool.sdd_cli.task_routing.local_llm import LocalLLMExecutor
            executor = LocalLLMExecutor()
            task = TaskContext(id="TSK-003", description="Implement baz()")
            await executor.execute(task, workspace=tmp_workspace, iteration=1)

        mock_proc.assert_called_once()
        args = mock_proc.call_args[0]
        assert "pytest" in args[0]

    @pytest.mark.asyncio
    async def test_loop_result_contains_required_fields(self, tmp_workspace, mock_completion_provider):
        """INV-04: Ergebnis enthält status, pytest_stdout, returncode, iteration."""
        with patch(
            "tool.sdd_cli.task_routing.local_llm.get_completion_provider",
            return_value=mock_completion_provider,
        ):
            with patch(
                "tool.sdd_cli.task_routing.local_llm.LocalLLMExecutor._run_pytest",
                new_callable=AsyncMock,
                return_value=(0, "2 passed"),
            ):
                from tool.sdd_cli.task_routing.local_llm import LocalLLMExecutor
                executor = LocalLLMExecutor()
                task = TaskContext(id="TSK-004", description="Implement qux()")
                result: TDDLoopResult = await executor.execute(task, workspace=tmp_workspace, iteration=2)

        assert result.status in ("pass", "fail")
        assert isinstance(result.pytest_stdout, str)
        assert isinstance(result.pytest_returncode, int)
        assert result.iteration == 2

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrent_tasks(self):
        """INV-05: max_concurrent Tasks gleichzeitig via Semaphore."""
        running = []
        peak = [0]

        async def fake_execute(task, workspace, iteration):
            running.append(task.id)
            peak[0] = max(peak[0], len(running))
            await asyncio.sleep(0.05)
            running.remove(task.id)
            return TDDLoopResult(status="pass", pytest_stdout="", pytest_returncode=0, iteration=1)

        with patch(
            "tool.sdd_cli.task_routing.local_llm.LocalLLMExecutor.execute",
            side_effect=fake_execute,
        ):
            from tool.sdd_cli.task_routing.local_llm import run_concurrent
            tasks = [TaskContext(id=f"TSK-{i:03d}", description="x") for i in range(6)]
            await run_concurrent(tasks, max_concurrent=2, workspace=Path("/tmp"))

        assert peak[0] <= 2, f"Peak concurrent war {peak[0]}, erwartet ≤ 2"

    @pytest.mark.asyncio
    async def test_llm_uses_spec0008_factory(self, tmp_workspace):
        """INV-06: LLM-Call via get_completion_provider, kein direkter HTTP-Call."""
        with patch(
            "tool.sdd_cli.task_routing.local_llm.get_completion_provider"
        ) as mock_factory:
            mock_provider = MagicMock()
            mock_provider.complete.return_value = MagicMock(text="def test_x(): pass")
            mock_factory.return_value = mock_provider

            with patch(
                "tool.sdd_cli.task_routing.local_llm.LocalLLMExecutor._run_pytest",
                new_callable=AsyncMock,
                return_value=(0, "ok"),
            ):
                from tool.sdd_cli.task_routing.local_llm import LocalLLMExecutor
                executor = LocalLLMExecutor()
                task = TaskContext(id="TSK-006", description="Implement y()")
                await executor.execute(task, workspace=tmp_workspace, iteration=1)

        mock_factory.assert_called_once()
        _, kwargs = mock_factory.call_args
        assert kwargs.get("component") == "local_llm" or mock_factory.call_args[0][1] == "local_llm"

    @pytest.mark.asyncio
    async def test_llm_timeout_returns_fail_result(self, tmp_workspace):
        """LLM-Timeout → fail mit Begründung 'LLM timeout'."""
        mock_provider = MagicMock()
        mock_provider.complete.side_effect = TimeoutError("connection timed out")

        with patch(
            "tool.sdd_cli.task_routing.local_llm.get_completion_provider",
            return_value=mock_provider,
        ):
            from tool.sdd_cli.task_routing.local_llm import LocalLLMExecutor
            executor = LocalLLMExecutor()
            task = TaskContext(id="TSK-007", description="Implement z()")
            result: TDDLoopResult = await executor.execute(task, workspace=tmp_workspace, iteration=1)

        assert result.status == "fail"
        assert "timeout" in result.error.lower()
        test_file = tmp_workspace / "tests" / "unit" / "test_TSK-007.py"
        assert not test_file.exists(), "Bei LLM-Timeout darf keine Testdatei geschrieben werden"
