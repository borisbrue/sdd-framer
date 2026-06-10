"""TST-0199 – Claude Review-Gate, Retry-Loop und Eskalation (Unit)
Spec: SPEC-0045 · Contract: CON-0173
"""
import asyncio
from dataclasses import dataclass, field
from typing import Literal
from unittest.mock import AsyncMock, MagicMock, patch
import pytest


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

@dataclass
class TDDLoopResult:
    status: str
    pytest_stdout: str
    pytest_returncode: int
    iteration: int
    error: str | None = None


@dataclass
class ReviewResult:
    verdict: Literal["pass", "fail"]
    reason: str = ""


@dataclass
class TaskState:
    id: str
    status: str = "pending"
    executor: str = "local"
    retry_context: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestReviewGate:
    @pytest.mark.asyncio
    async def test_local_pass_claude_pass_completes_task(self):
        """INV-01: pytest pass + Claude pass → status completed, executor local."""
        tdd_result = TDDLoopResult(status="pass", pytest_stdout="1 passed",
                                   pytest_returncode=0, iteration=1)
        mock_reviewer = AsyncMock(return_value=ReviewResult(verdict="pass"))

        with patch("tool.sdd_cli.task_routing.loop_controller.ClaudeReviewer.review",
                   mock_reviewer):
            from tool.sdd_cli.task_routing.loop_controller import LoopController
            controller = LoopController(max_retries=3)
            task = TaskState(id="TSK-001")
            await controller.handle_tdd_result(task, tdd_result)

        assert task.status == "completed"
        assert task.executor == "local"
        mock_reviewer.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_pytest_fail_skips_claude_review(self):
        """INV-01: pytest fail → Claude wird NICHT aufgerufen, direkt Retry."""
        tdd_result = TDDLoopResult(status="fail", pytest_stdout="FAILED",
                                   pytest_returncode=1, iteration=1)
        mock_reviewer = AsyncMock()

        with patch("tool.sdd_cli.task_routing.loop_controller.ClaudeReviewer.review",
                   mock_reviewer):
            from tool.sdd_cli.task_routing.loop_controller import LoopController
            controller = LoopController(max_retries=3)
            task = TaskState(id="TSK-002")
            await controller.handle_tdd_result(task, tdd_result)

        mock_reviewer.assert_not_awaited()
        assert task.status != "completed"

    @pytest.mark.asyncio
    async def test_local_pass_claude_fail_triggers_retry(self):
        """pytest pass + Claude fail → Retry-Kontext angereichert."""
        tdd_result = TDDLoopResult(status="pass", pytest_stdout="1 passed",
                                   pytest_returncode=0, iteration=1)
        mock_reviewer = AsyncMock(return_value=ReviewResult(
            verdict="fail", reason="Contract-Invariante INV-02 verletzt"
        ))

        with patch("tool.sdd_cli.task_routing.loop_controller.ClaudeReviewer.review",
                   mock_reviewer):
            from tool.sdd_cli.task_routing.loop_controller import LoopController
            controller = LoopController(max_retries=3)
            task = TaskState(id="TSK-003")
            await controller.handle_tdd_result(task, tdd_result)

        assert task.status != "completed"
        assert len(task.retry_context) == 1
        assert "INV-02" in task.retry_context[0]

    @pytest.mark.asyncio
    async def test_retry_context_accumulates(self):
        """INV-03: Kontext ist akkumulativ über alle Iterationen."""
        from tool.sdd_cli.task_routing.loop_controller import LoopController

        controller = LoopController(max_retries=3)
        task = TaskState(id="TSK-004")

        reasons = ["Fehler 1: Test fehlt Edge-Case", "Fehler 2: Timeout ignoriert"]
        for i, reason in enumerate(reasons, 1):
            tdd_result = TDDLoopResult(status="pass", pytest_stdout="ok",
                                       pytest_returncode=0, iteration=i)
            mock_reviewer = AsyncMock(return_value=ReviewResult(verdict="fail", reason=reason))
            with patch("tool.sdd_cli.task_routing.loop_controller.ClaudeReviewer.review",
                       mock_reviewer):
                await controller.handle_tdd_result(task, tdd_result)

        assert len(task.retry_context) == 2
        assert "Fehler 1" in task.retry_context[0]
        assert "Fehler 2" in task.retry_context[1]

    @pytest.mark.asyncio
    async def test_escalation_after_max_retries(self):
        """INV-04: Nach max_retries → Eskalation, nie stilles Verwerfen."""
        from tool.sdd_cli.task_routing.loop_controller import LoopController

        controller = LoopController(max_retries=2)
        task = TaskState(id="TSK-005")

        mock_escalate = AsyncMock()
        with patch("tool.sdd_cli.task_routing.loop_controller.LoopController._escalate",
                   mock_escalate):
            for i in range(1, 3):
                tdd_result = TDDLoopResult(status="fail", pytest_stdout="FAILED",
                                           pytest_returncode=1, iteration=i)
                await controller.handle_tdd_result(task, tdd_result)

        mock_escalate.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_escalated_executor_uses_code_gen_provider(self):
        """INV-05: Eskalierter Task nutzt get_code_gen_provider(), executor = 'claude (escalated)'."""
        with patch(
            "tool.sdd_cli.task_routing.loop_controller.get_code_gen_provider"
        ) as mock_factory:
            mock_provider = MagicMock()
            mock_provider.generate = AsyncMock(return_value=([], "done"))
            mock_factory.return_value = mock_provider

            from tool.sdd_cli.task_routing.loop_controller import LoopController
            controller = LoopController(max_retries=1)
            task = TaskState(id="TSK-006")
            tdd_result = TDDLoopResult(status="fail", pytest_stdout="FAILED",
                                       pytest_returncode=1, iteration=1)
            await controller.handle_tdd_result(task, tdd_result)

        assert task.executor == "claude (escalated)"
        mock_factory.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_completed_without_review(self):
        """INV-01: Kein Task kann completed werden ohne dass Review aufgerufen wurde."""
        from tool.sdd_cli.task_routing.loop_controller import LoopController

        controller = LoopController(max_retries=3)
        task = TaskState(id="TSK-007")

        tdd_result = TDDLoopResult(status="pass", pytest_stdout="ok",
                                   pytest_returncode=0, iteration=1)

        with patch("tool.sdd_cli.task_routing.loop_controller.ClaudeReviewer.review",
                   side_effect=ConnectionError("Claude nicht erreichbar")):
            with pytest.raises(ConnectionError):
                await controller.handle_tdd_result(task, tdd_result)

        assert task.status != "completed"

    @pytest.mark.asyncio
    async def test_claude_fail_reason_required(self):
        """INV-02: Claude-fail ohne Begründung ist Protokollverstoß → ValueError."""
        tdd_result = TDDLoopResult(status="pass", pytest_stdout="ok",
                                   pytest_returncode=0, iteration=1)
        mock_reviewer = AsyncMock(return_value=ReviewResult(verdict="fail", reason=""))

        with patch("tool.sdd_cli.task_routing.loop_controller.ClaudeReviewer.review",
                   mock_reviewer):
            from tool.sdd_cli.task_routing.loop_controller import LoopController
            controller = LoopController(max_retries=3)
            task = TaskState(id="TSK-008")
            with pytest.raises(ValueError, match="[Bb]egründung"):
                await controller.handle_tdd_result(task, tdd_result)
