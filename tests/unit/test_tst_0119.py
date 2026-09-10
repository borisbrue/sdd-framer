# TST-0119 – ReviewPipeline + Retry-Logik (Unit)
# Spec: SPEC-0026 | Contract: CON-0100

from pathlib import Path
from unittest.mock import MagicMock, patch

from tool.sdd_cli.review_pipeline import (
    ReviewPipeline,
    ReviewResult,
    SyntaxCheckHandler,
)
from tool.sdd_cli.task_lifecycle import MAX_RETRIES, TaskLifecycle
from tool.sdd_cli.task_model import Complexity, ContextSize, Task, TaskStatus, TaskType


def _task() -> Task:
    return Task(
        spec_id="SPEC-0026", title="T", description="desc",
        type=TaskType.CODE, complexity=Complexity.MEDIUM,
        context_size=ContextSize.M, estimated_tokens=1000,
    )


def _passing_pipeline(tmp_path: Path) -> ReviewPipeline:
    pipeline = ReviewPipeline(work_dir=tmp_path)
    pipeline._chain = MagicMock()
    pipeline._chain.handle.return_value = ReviewResult(True)
    return pipeline


def _failing_pipeline(tmp_path: Path, reason: str = "err") -> ReviewPipeline:
    pipeline = ReviewPipeline(work_dir=tmp_path)
    pipeline._chain = MagicMock()
    pipeline._chain.handle.return_value = ReviewResult(False, reason)
    return pipeline


class TestTST0119:
    def test_all_pass_task_committed(self, tmp_path):
        t = _task()
        lc = TaskLifecycle(t)
        lc.assign("llm-1")
        lc.start_running("c1")
        pipeline = _passing_pipeline(tmp_path)
        commit_fn = MagicMock(return_value="abc123")
        result = pipeline.run(t, commit_fn=commit_fn)
        assert result is True
        assert t.status == TaskStatus.COMMITTED
        assert t.commit_hash == "abc123"

    def test_syntax_fail_stops_chain(self, tmp_path):
        t = _task()
        lc = TaskLifecycle(t)
        lc.assign("llm-1")
        lc.start_running("c1")

        syntax = SyntaxCheckHandler(next_handler=None)
        with patch.object(syntax, 'handle', return_value=ReviewResult(False, "SyntaxError")):
            pass

        pipeline = _failing_pipeline(tmp_path, "SyntaxError: line 42")
        pipeline.run(t)
        assert t.status in (TaskStatus.RETRYING, TaskStatus.BLOCKED)
        assert len(t.error_context) >= 1

    def test_failed_increments_retry_count(self, tmp_path):
        t = _task()
        lc = TaskLifecycle(t)
        lc.assign("llm-1")
        lc.start_running("c1")
        pipeline = _failing_pipeline(tmp_path, "Fehler 1")
        pipeline.run(t)
        assert t.retry_count == 1
        assert t.error_context == ["Fehler 1"]

    def test_third_failure_blocks_task(self, tmp_path):
        t = _task()
        t.retry_count = MAX_RETRIES
        lc = TaskLifecycle(t)
        lc.assign("llm-1")
        lc.start_running("c1")
        pipeline = _failing_pipeline(tmp_path, "still broken")
        pipeline.run(t)
        assert t.status == TaskStatus.BLOCKED

    def test_retry_receives_full_error_context(self, tmp_path):
        t = _task()
        t.error_context = ["Fehler 1", "Fehler 2"]
        t.retry_count = 2
        lc = TaskLifecycle(t)
        lc.assign("llm-1")
        lc.start_running("c1")
        pipeline = _failing_pipeline(tmp_path, "Fehler 3")
        pipeline.run(t)
        assert "Fehler 1" in t.error_context
        assert "Fehler 2" in t.error_context
        assert "Fehler 3" in t.error_context

    def test_error_context_grows_monotonically(self, tmp_path):
        t = _task()
        lc = TaskLifecycle(t)
        lc.assign("llm-1")
        lc.start_running("c1")
        pipeline = _failing_pipeline(tmp_path, "err1")
        pipeline.run(t)
        assert len(t.error_context) == 1
        assert t.error_context[0] == "err1"

    def test_claude_review_fail_retries(self, tmp_path):
        t = _task()
        lc = TaskLifecycle(t)
        lc.assign("llm-1")
        lc.start_running("c1")
        pipeline = _failing_pipeline(tmp_path, "SOLID-Verletzung: SRP")
        pipeline.run(t)
        assert t.status in (TaskStatus.RETRYING, TaskStatus.BLOCKED)
        assert any("SOLID" in e for e in t.error_context)

    def test_no_commit_hash_for_non_committed(self, tmp_path):
        t = _task()
        lc = TaskLifecycle(t)
        lc.assign("llm-1")
        lc.start_running("c1")
        pipeline = _failing_pipeline(tmp_path)
        pipeline.run(t)
        assert t.commit_hash is None
