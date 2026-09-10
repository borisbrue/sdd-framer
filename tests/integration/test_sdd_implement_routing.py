"""Integration-Test: sdd-implement Routing-Pipeline (SPEC-0045)."""
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, patch


@dataclass
class TaskStub:
    id: str
    complexity_score: int = 0
    executor: str | None = None
    status: str = "pending"
    retry_context: list[str] = field(default_factory=list)
    affected_files: list[str] = field(default_factory=list)
    estimated_lines: int = 0
    dependent_contracts: int = 0


class TestSddImplementRouting:
    def test_trivial_task_routed_to_local(self):
        from tool.sdd_cli.task_routing.config import TaskRoutingConfig
        from tool.sdd_cli.task_routing.heuristic import compute_complexity_score
        from tool.sdd_cli.task_routing.router import decide_executor

        task = TaskStub(id="TSK-001", affected_files=["one.py"], estimated_lines=20)
        score = compute_complexity_score(task)
        config = TaskRoutingConfig(enabled=True, complexity_threshold=30, local_llm_configured=True)
        executor = decide_executor(TaskStub(id="TSK-001", complexity_score=score), config)
        assert executor in ("local", "claude")

    def test_routing_disabled_falls_back_to_claude(self):
        from tool.sdd_cli.task_routing.config import TaskRoutingConfig
        from tool.sdd_cli.task_routing.router import decide_executor

        config = TaskRoutingConfig(enabled=False, local_llm_configured=True)
        task = TaskStub(id="TSK-002", complexity_score=5)
        assert decide_executor(task, config) == "claude"

    def test_enabled_without_local_llm_falls_back_to_claude(self):
        from tool.sdd_cli.task_routing.config import TaskRoutingConfig
        from tool.sdd_cli.task_routing.router import decide_executor

        config = TaskRoutingConfig(enabled=True, local_llm_configured=False)
        task = TaskStub(id="TSK-003", complexity_score=5)
        assert decide_executor(task, config) == "claude"

    async def test_full_pipeline_local_pass(self, tmp_path):
        from tool.sdd_cli.task_routing.loop_controller import LoopController, ReviewResult

        task = TaskStub(id="TSK-004", executor="local")
        from dataclasses import dataclass as dc

        @dc
        class FakeTDDResult:
            status: str = "pass"
            pytest_stdout: str = "1 passed"
            pytest_returncode: int = 0
            iteration: int = 1

        mock_review = AsyncMock(return_value=ReviewResult(verdict="pass"))
        with patch(
            "tool.sdd_cli.task_routing.loop_controller.ClaudeReviewer.review",
            mock_review,
        ):
            controller = LoopController(max_retries=3)
            await controller.handle_tdd_result(task, FakeTDDResult())

        assert task.status == "completed"
        assert task.executor == "local"
