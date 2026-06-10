"""executor-Feld in Task-Output (US-02, SPEC-0045)."""
import pytest


class TestExecutorFieldTaskOutput:
    def test_route_task_sets_executor_field(self):
        from tool.sdd_cli.task_routing.router import decide_executor
        from tool.sdd_cli.task_routing.config import TaskRoutingConfig

        from dataclasses import dataclass

        @dataclass
        class Task:
            id: str
            complexity_score: int
            executor: str | None = None

        config = TaskRoutingConfig(enabled=True, complexity_threshold=30, local_llm_configured=True)
        task = Task(id="TSK-001", complexity_score=20)
        result = decide_executor(task, config)
        task.executor = result
        assert task.executor in ("local", "claude")

    def test_executor_local_for_trivial_task(self):
        from tool.sdd_cli.task_routing.router import decide_executor
        from tool.sdd_cli.task_routing.config import TaskRoutingConfig
        from dataclasses import dataclass

        @dataclass
        class Task:
            id: str
            complexity_score: int
            executor: str | None = None

        config = TaskRoutingConfig(enabled=True, complexity_threshold=30, local_llm_configured=True)
        task = Task(id="TSK-002", complexity_score=10)
        assert decide_executor(task, config) == "local"

    def test_executor_claude_for_complex_task(self):
        from tool.sdd_cli.task_routing.router import decide_executor
        from tool.sdd_cli.task_routing.config import TaskRoutingConfig
        from dataclasses import dataclass

        @dataclass
        class Task:
            id: str
            complexity_score: int
            executor: str | None = None

        config = TaskRoutingConfig(enabled=True, complexity_threshold=30, local_llm_configured=True)
        task = Task(id="TSK-003", complexity_score=50)
        assert decide_executor(task, config) == "claude"
