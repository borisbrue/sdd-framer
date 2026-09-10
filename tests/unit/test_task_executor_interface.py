"""TaskExecutor Protocol/ABC – interface tests (SPEC-0045 Strategy Pattern)."""


class TestTaskExecutorInterface:
    def test_local_llm_executor_implements_protocol(self):
        from tool.sdd_cli.task_routing.executor import TaskExecutor
        from tool.sdd_cli.task_routing.local_llm import LocalLLMExecutor

        assert isinstance(LocalLLMExecutor(), TaskExecutor)

    def test_task_executor_has_execute_method(self):
        from tool.sdd_cli.task_routing.executor import TaskExecutor

        assert hasattr(TaskExecutor, "execute")

    def test_executor_is_runtime_checkable(self):
        from tool.sdd_cli.task_routing.executor import TaskExecutor

        class DummyExecutor:
            async def execute(self, task, workspace, iteration):
                ...

        assert isinstance(DummyExecutor(), TaskExecutor)

    def test_object_without_execute_not_executor(self):
        from tool.sdd_cli.task_routing.executor import TaskExecutor

        class NotAnExecutor:
            pass

        assert not isinstance(NotAnExecutor(), TaskExecutor)
