"""TST-0199 – Claude Review-Gate, Retry-Loop und Eskalation (Unit)
Spec: SPEC-0045 · Contract: CON-0173
"""
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
    test_code: str = ""
    impl_code: str = ""


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
    async def test_pytest_fail_feeds_output_into_retry_context(self):
        """CON-0173 Szenario 'pytest fail → direkt Retry mit Fehlerkontext':
        auch ohne Claude-Review landet der pytest-Output in retry_context."""
        tdd_result = TDDLoopResult(status="fail", pytest_stdout="AssertionError: x != 1",
                                   pytest_returncode=1, iteration=1)

        from tool.sdd_cli.task_routing.loop_controller import LoopController
        controller = LoopController(max_retries=3)
        task = TaskState(id="TSK-009")
        await controller.handle_tdd_result(task, tdd_result)

        assert len(task.retry_context) == 1
        assert "AssertionError: x != 1" in task.retry_context[0]

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
    async def test_escalated_executor_uses_code_gen_provider(self, tmp_path):
        """INV-05: Eskalierter Task nutzt get_code_gen_provider().generate(), executor = 'claude (escalated)'."""
        with patch(
            "tool.sdd_cli.task_routing.loop_controller.get_code_gen_provider"
        ) as mock_factory:
            mock_provider = MagicMock()
            mock_provider.generate = MagicMock(return_value=([], "done"))
            mock_factory.return_value = mock_provider

            from tool.sdd_cli.task_routing.loop_controller import LoopController
            controller = LoopController(max_retries=1, workspace=tmp_path)
            task = TaskState(id="TSK-006", retry_context=["Fehler 1"])
            tdd_result = TDDLoopResult(status="fail", pytest_stdout="FAILED",
                                       pytest_returncode=1, iteration=1)
            await controller.handle_tdd_result(task, tdd_result)

        assert task.executor == "claude (escalated)"
        mock_factory.assert_called_once()
        mock_provider.generate.assert_called_once()
        args, kwargs = mock_provider.generate.call_args
        prompt = args[0]
        assert args[1] == tmp_path
        assert "TSK-006" in prompt
        assert "Fehler 1" in prompt
        assert "FAILED" in prompt

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


# ---------------------------------------------------------------------------
# ClaudeReviewer – echte review()-Implementierung (nur der LLM-Aufruf gemockt,
# nicht review() selbst — sonst prüft der Test nichts an der Produktionslogik).
# ---------------------------------------------------------------------------

class TestClaudeReviewerImplementation:
    def _mock_provider(self, response_text: str):
        provider = MagicMock()
        provider.complete = MagicMock(return_value=MagicMock(text=response_text))
        return provider

    @pytest.mark.asyncio
    async def test_review_returns_pass_from_llm_json(self):
        from tool.sdd_cli.task_routing.loop_controller import ClaudeReviewer

        provider = self._mock_provider('{"verdict": "pass", "reason": ""}')
        tdd_result = TDDLoopResult(status="pass", pytest_stdout="1 passed",
                                   pytest_returncode=0, iteration=1)
        task = TaskState(id="TSK-100")

        with patch("tool.sdd_cli.task_routing.loop_controller.get_completion_provider",
                   return_value=provider) as mock_factory:
            result = await ClaudeReviewer(config=None).review(task, tdd_result)

        assert result.verdict == "pass"
        mock_factory.assert_called_once_with(None, "evaluator")

    @pytest.mark.asyncio
    async def test_review_returns_fail_with_reason_from_llm_json(self):
        from tool.sdd_cli.task_routing.loop_controller import ClaudeReviewer

        provider = self._mock_provider(
            'Hier ist meine Bewertung:\n'
            '{"verdict": "fail", "reason": "Implementierung ignoriert Timeout"}'
        )
        tdd_result = TDDLoopResult(status="pass", pytest_stdout="1 passed",
                                   pytest_returncode=0, iteration=1)
        task = TaskState(id="TSK-101")

        with patch("tool.sdd_cli.task_routing.loop_controller.get_completion_provider",
                   return_value=provider):
            result = await ClaudeReviewer(config=None).review(task, tdd_result)

        assert result.verdict == "fail"
        assert "Timeout" in result.reason

    @pytest.mark.asyncio
    async def test_review_prompt_includes_test_and_impl_code(self):
        from tool.sdd_cli.task_routing.loop_controller import ClaudeReviewer

        provider = self._mock_provider('{"verdict": "pass"}')
        tdd_result = TDDLoopResult(
            status="pass", pytest_stdout="1 passed", pytest_returncode=0, iteration=1,
            test_code="def test_x(): assert x() == 1",
            impl_code="def x(): return 1",
        )
        task = TaskState(id="TSK-102")

        with patch("tool.sdd_cli.task_routing.loop_controller.get_completion_provider",
                   return_value=provider):
            await ClaudeReviewer(config=None).review(task, tdd_result)

        prompt = provider.complete.call_args[0][0]
        assert "def test_x()" in prompt
        assert "def x(): return 1" in prompt

    @pytest.mark.asyncio
    async def test_review_loads_spec_and_contract_as_system_prompt(self):
        from tool.sdd_cli.task_routing.loop_controller import ClaudeReviewer

        provider = self._mock_provider('{"verdict": "pass"}')
        tdd_result = TDDLoopResult(status="pass", pytest_stdout="ok",
                                   pytest_returncode=0, iteration=1)
        task = TaskState(id="TSK-103")
        task.spec_id = "SPEC-9999"

        with patch("tool.sdd_cli.task_routing.loop_controller.get_completion_provider",
                   return_value=provider), \
             patch("tool.sdd_cli.orchestrator._load_spec",
                   return_value="# SPEC-9999 Inhalt") as mock_spec, \
             patch("tool.sdd_cli.orchestrator._load_contracts",
                   return_value=[("CON-1234", "# CON-1234 Inhalt")]) as mock_contracts:
            await ClaudeReviewer(config="cfg").review(task, tdd_result)

        mock_spec.assert_called_once_with("cfg", "SPEC-9999")
        mock_contracts.assert_called_once_with("cfg", "SPEC-9999")
        system_prompt = provider.complete.call_args.kwargs["system_prompt"]
        assert "SPEC-9999 Inhalt" in system_prompt
        assert "CON-1234 Inhalt" in system_prompt

    @pytest.mark.asyncio
    async def test_review_without_spec_id_sends_no_system_prompt(self):
        from tool.sdd_cli.task_routing.loop_controller import ClaudeReviewer

        provider = self._mock_provider('{"verdict": "pass"}')
        tdd_result = TDDLoopResult(status="pass", pytest_stdout="ok",
                                   pytest_returncode=0, iteration=1)
        task = TaskState(id="TSK-104")  # kein spec_id-Attribut

        with patch("tool.sdd_cli.task_routing.loop_controller.get_completion_provider",
                   return_value=provider):
            await ClaudeReviewer(config=None).review(task, tdd_result)

        assert provider.complete.call_args.kwargs["system_prompt"] is None

    @pytest.mark.asyncio
    async def test_review_raises_on_non_json_response(self):
        """Kein parsbares JSON → ValueError, nicht stiller Fallback auf pass/fail."""
        from tool.sdd_cli.task_routing.loop_controller import ClaudeReviewer

        provider = self._mock_provider("Das sieht gut aus, passt schon.")
        tdd_result = TDDLoopResult(status="pass", pytest_stdout="ok",
                                   pytest_returncode=0, iteration=1)
        task = TaskState(id="TSK-105")

        with patch("tool.sdd_cli.task_routing.loop_controller.get_completion_provider",
                   return_value=provider):
            with pytest.raises(ValueError):
                await ClaudeReviewer(config=None).review(task, tdd_result)

    @pytest.mark.asyncio
    async def test_review_raises_on_invalid_verdict_value(self):
        from tool.sdd_cli.task_routing.loop_controller import ClaudeReviewer

        provider = self._mock_provider('{"verdict": "maybe"}')
        tdd_result = TDDLoopResult(status="pass", pytest_stdout="ok",
                                   pytest_returncode=0, iteration=1)
        task = TaskState(id="TSK-106")

        with patch("tool.sdd_cli.task_routing.loop_controller.get_completion_provider",
                   return_value=provider):
            with pytest.raises(ValueError):
                await ClaudeReviewer(config=None).review(task, tdd_result)

    @pytest.mark.asyncio
    async def test_review_propagates_provider_connection_error(self):
        """INV-01 (Kein completed ohne Review): Verbindungsfehler wird nicht geschluckt."""
        from tool.sdd_cli.task_routing.loop_controller import ClaudeReviewer

        provider = MagicMock()
        provider.complete.side_effect = ConnectionError("Claude nicht erreichbar")
        tdd_result = TDDLoopResult(status="pass", pytest_stdout="ok",
                                   pytest_returncode=0, iteration=1)
        task = TaskState(id="TSK-107")

        with patch("tool.sdd_cli.task_routing.loop_controller.get_completion_provider",
                   return_value=provider):
            with pytest.raises(ConnectionError):
                await ClaudeReviewer(config=None).review(task, tdd_result)
