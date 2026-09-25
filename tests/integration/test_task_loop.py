"""Integration-Tests: execute_task_loop – Headless Batch-Modus (SPEC-0045).

Deckt die Orchestrierung ab (Routing, Retry, Eskalation, Dependency-Reihenfolge,
BLOCKED-Skip, Persistenz) — mockt ausschließlich die LLM-Provider-Grenze
(get_completion_provider/get_code_gen_provider), nicht die Produktionslogik
selbst.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tool.sdd_cli.task_model import Complexity, ContextSize, Task, TaskStatus, TaskType


@dataclass
class FakeConfig:
    raw: dict
    specs_dir: Path = field(default_factory=lambda: Path("/nonexistent-specs"))
    contracts_dir: Path = field(default_factory=lambda: Path("/nonexistent-contracts"))


BASE_RAW = {
    "llm": {"local_llm": {"provider": "openai-compat", "base_url": "http://x/v1", "model": "m"}},
    "task_routing": {
        "enabled": True, "complexity_threshold": 30, "max_retries": 2, "max_concurrent": 2,
    },
}


def _config(tmp_path) -> FakeConfig:
    """FakeConfig mit specs_dir/contracts_dir — inkl. Minimal-Spec SPEC-9001.

    _load_spec/_load_contracts (orchestrator.py) suchen darin per .rglob()
    nach der id im Frontmatter; ClaudeReviewer.review() braucht das (INV-06).
    """
    specs_dir = tmp_path / ".sdd" / "specs"
    contracts_dir = tmp_path / ".sdd" / "contracts"
    specs_dir.mkdir(parents=True, exist_ok=True)
    contracts_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / "SPEC-9001-test.md").write_text(
        "---\nid: SPEC-9001\ncontracts: []\n---\n# Test-Spec\n"
    )
    return FakeConfig(raw=BASE_RAW, specs_dir=specs_dir, contracts_dir=contracts_dir)


def _task(title: str, complexity: Complexity = Complexity.LOW,
          ttype: TaskType = TaskType.CODE, deps: list[str] | None = None) -> Task:
    return Task(
        spec_id="SPEC-9001", title=title, description=f"Implement {title}",
        type=ttype, complexity=complexity, context_size=ContextSize.S,
        estimated_tokens=100, dependencies=deps or [],
        test_command="pytest -q",
    )


def _write_tasks(workspace, spec_id: str, tasks: list[Task]) -> None:
    tasks_dir = workspace / ".sdd" / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / f"{spec_id}.json").write_text(
        json.dumps([t.to_dict() for t in tasks], indent=2, ensure_ascii=False)
    )


def _persisted(workspace, spec_id: str) -> list[dict]:
    return json.loads((workspace / ".sdd" / "tasks" / f"{spec_id}.json").read_text())


class TestExecuteTaskLoopLocalPath:
    @pytest.mark.asyncio
    async def test_local_task_passes_first_try(self, tmp_path):
        from tool.sdd_cli.task_routing.task_loop import execute_task_loop

        task = _task("alpha")
        _write_tasks(tmp_path, "SPEC-9001", [task])
        config = _config(tmp_path)

        mock_completion = MagicMock()
        mock_completion.complete.return_value = MagicMock(text="def test_x(): pass")
        mock_review = MagicMock()
        mock_review.complete.return_value = MagicMock(text='{"verdict": "pass"}')

        with patch(
            "tool.sdd_cli.task_routing.local_llm.get_completion_provider",
            return_value=mock_completion,
        ), patch(
            "tool.sdd_cli.task_routing.local_llm.LocalLLMExecutor._run_pytest",
            new_callable=AsyncMock, return_value=(0, "1 passed"),
        ), patch(
            "tool.sdd_cli.task_routing.loop_controller.get_completion_provider",
            return_value=mock_review,
        ):
            report = await execute_task_loop("SPEC-9001", config, tmp_path)

        assert len(report.outcomes) == 1
        assert report.outcomes[0].status == "completed"
        assert report.outcomes[0].executor == "local"
        assert report.all_passed

        persisted = _persisted(tmp_path, "SPEC-9001")
        assert persisted[0]["status"] == TaskStatus.PASSED.value
        assert persisted[0]["executor"] == "local"

    @pytest.mark.asyncio
    async def test_local_task_escalates_after_max_retries(self, tmp_path):
        from tool.sdd_cli.task_routing.task_loop import execute_task_loop

        task = _task("beta")
        _write_tasks(tmp_path, "SPEC-9001", [task])
        config = _config(tmp_path)  # max_retries: 2

        mock_completion = MagicMock()
        mock_completion.complete.return_value = MagicMock(text="def test_x(): pass")
        mock_code_gen = MagicMock()
        mock_code_gen.generate.return_value = ([{"path": "beta.py", "content": "x=1"}], "done")

        with patch(
            "tool.sdd_cli.task_routing.local_llm.get_completion_provider",
            return_value=mock_completion,
        ), patch(
            "tool.sdd_cli.task_routing.local_llm.LocalLLMExecutor._run_pytest",
            new_callable=AsyncMock, return_value=(1, "FAILED"),
        ), patch(
            "tool.sdd_cli.task_routing.loop_controller.get_code_gen_provider",
            return_value=mock_code_gen,
        ), patch(
            "tool.sdd_cli.task_routing.task_loop._run_tests",
            return_value=(True, "1 passed"),
        ) as mock_verify:
            report = await execute_task_loop("SPEC-9001", config, tmp_path)

        outcome = report.outcomes[0]
        assert outcome.executor == "claude (escalated)"
        assert outcome.status == "completed"
        mock_code_gen.generate.assert_called_once()
        prompt = mock_code_gen.generate.call_args[0][0]
        assert "beta" in prompt
        mock_verify.assert_called_once()

        persisted = _persisted(tmp_path, "SPEC-9001")
        assert persisted[0]["executor"] == "claude (escalated)"
        assert persisted[0]["status"] == TaskStatus.PASSED.value


    @pytest.mark.asyncio
    async def test_local_retry_receives_prior_failure_as_context(self, tmp_path):
        """Bugfix: retry_context muss tatsächlich in den zweiten lokalen
        Versuch einfließen (vorher: identischer Prompt bei jedem Retry)."""
        from tool.sdd_cli.task_routing.task_loop import execute_task_loop

        task = _task("delta")
        _write_tasks(tmp_path, "SPEC-9001", [task])
        config = _config(tmp_path)  # max_retries: 2

        impl_prompts: list[str] = []
        pytest_results = iter([(1, "AssertionError: boom"), (0, "1 passed")])

        def fake_complete(prompt: str, **kwargs):
            if "Implement the following" in prompt:
                impl_prompts.append(prompt)
            return MagicMock(text="CODE")

        mock_completion = MagicMock()
        mock_completion.complete.side_effect = fake_complete
        mock_review = MagicMock()
        mock_review.complete.return_value = MagicMock(text='{"verdict": "pass"}')

        with patch(
            "tool.sdd_cli.task_routing.local_llm.get_completion_provider",
            return_value=mock_completion,
        ), patch(
            "tool.sdd_cli.task_routing.local_llm.LocalLLMExecutor._run_pytest",
            new_callable=AsyncMock, side_effect=lambda *a, **kw: next(pytest_results),
        ), patch(
            "tool.sdd_cli.task_routing.loop_controller.get_completion_provider",
            return_value=mock_review,
        ):
            report = await execute_task_loop("SPEC-9001", config, tmp_path)

        assert report.outcomes[0].status == "completed"
        assert report.outcomes[0].executor == "local"
        assert len(impl_prompts) == 2, "erwarte genau 2 Implementierungs-Versuche"
        assert "AssertionError: boom" in impl_prompts[1], (
            "Iteration 2 muss den Fehler aus Iteration 1 im Prompt sehen"
        )


class TestExecuteTaskLoopClaudeDirect:
    @pytest.mark.asyncio
    async def test_high_complexity_task_routes_directly_to_claude(self, tmp_path):
        from tool.sdd_cli.task_routing.task_loop import execute_task_loop

        task = _task("gamma", complexity=Complexity.HIGH)
        _write_tasks(tmp_path, "SPEC-9001", [task])
        config = _config(tmp_path)

        mock_code_gen = MagicMock()
        mock_code_gen.generate.return_value = ([{"path": "gamma.py", "content": "x=1"}], "done")

        with patch(
            "tool.sdd_cli.task_routing.task_loop.get_code_gen_provider",
            return_value=mock_code_gen,
        ), patch(
            "tool.sdd_cli.task_routing.task_loop._run_tests",
            return_value=(True, "1 passed"),
        ), patch(
            "tool.sdd_cli.task_routing.local_llm.get_completion_provider",
        ) as mock_local_factory:
            report = await execute_task_loop("SPEC-9001", config, tmp_path)

        mock_local_factory.assert_not_called()
        assert report.outcomes[0].executor == "claude"
        assert report.outcomes[0].status == "completed"

    @pytest.mark.asyncio
    async def test_non_code_task_skips_green_verification(self, tmp_path):
        from tool.sdd_cli.task_routing.task_loop import execute_task_loop

        task = _task("doc-update", ttype=TaskType.DOC)
        _write_tasks(tmp_path, "SPEC-9001", [task])
        config = _config(tmp_path)

        mock_code_gen = MagicMock()
        mock_code_gen.generate.return_value = ([{"path": "README.md", "content": "x"}], "done")

        with patch(
            "tool.sdd_cli.task_routing.task_loop.get_code_gen_provider",
            return_value=mock_code_gen,
        ), patch(
            "tool.sdd_cli.task_routing.task_loop._run_tests",
        ) as mock_verify:
            report = await execute_task_loop("SPEC-9001", config, tmp_path)

        mock_verify.assert_not_called()
        assert report.outcomes[0].status == "completed"
        assert report.outcomes[0].executor == "claude"


class TestExecuteTaskLoopOrderingAndSkip:
    @pytest.mark.asyncio
    async def test_dependent_task_never_runs_if_dependency_fails(self, tmp_path):
        from tool.sdd_cli.task_routing.task_loop import execute_task_loop

        task_a = _task("A", complexity=Complexity.HIGH)
        task_b = _task("B", complexity=Complexity.HIGH, deps=["A"])
        _write_tasks(tmp_path, "SPEC-9001", [task_a, task_b])
        config = _config(tmp_path)

        mock_code_gen = MagicMock()
        mock_code_gen.generate.return_value = ([{"path": "a.py", "content": "x"}], "done")

        with patch(
            "tool.sdd_cli.task_routing.task_loop.get_code_gen_provider",
            return_value=mock_code_gen,
        ), patch(
            "tool.sdd_cli.task_routing.task_loop._run_tests",
            return_value=(False, "1 failed"),  # A schlägt fehl
        ):
            report = await execute_task_loop("SPEC-9001", config, tmp_path)

        mock_code_gen.generate.assert_called_once()  # nur A, nie B
        by_title = {o.task.title: o for o in report.outcomes}
        assert by_title["A"].status == "failed"
        assert by_title["B"].status == "failed"
        assert "Abhängigkeit" in by_title["B"].detail

    @pytest.mark.asyncio
    async def test_blocked_task_reported_not_silently_dropped(self, tmp_path):
        from tool.sdd_cli.task_routing.task_loop import execute_task_loop

        task = _task("cyclic")
        task.status = TaskStatus.BLOCKED
        _write_tasks(tmp_path, "SPEC-9001", [task])
        config = _config(tmp_path)

        report = await execute_task_loop("SPEC-9001", config, tmp_path)

        assert len(report.outcomes) == 1
        assert report.outcomes[0].status == "failed"
        assert "BLOCKED" in report.outcomes[0].detail
