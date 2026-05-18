# TST-0114 – Task-Lifecycle Zustandsübergänge (Unit)
# Spec: SPEC-0026 | Contract: CON-0095

import pytest
from tool.sdd_cli.task_model import Task, TaskStatus, TaskType, Complexity, ContextSize
from tool.sdd_cli.task_lifecycle import TaskLifecycle, InvalidTransitionError, MAX_RETRIES


def _task() -> Task:
    return Task(
        spec_id="SPEC-0026", title="Test Task", description="",
        type=TaskType.CODE, complexity=Complexity.MEDIUM,
        context_size=ContextSize.M, estimated_tokens=1000,
    )


class TestTST0114:
    def test_pending_to_assigned(self):
        t = _task()
        lc = TaskLifecycle(t)
        lc.assign("llm-1")
        assert t.status == TaskStatus.ASSIGNED
        assert t.llm_id == "llm-1"

    def test_assigned_to_running(self):
        t = _task()
        lc = TaskLifecycle(t)
        lc.assign("llm-1")
        lc.start_running("container-1")
        assert t.status == TaskStatus.RUNNING
        assert t.container_id == "container-1"

    def test_running_to_review(self):
        t = _task()
        lc = TaskLifecycle(t)
        lc.assign("llm-1")
        lc.start_running("c1")
        lc.submit_for_review()
        assert t.status == TaskStatus.REVIEW

    def test_review_to_committed(self):
        t = _task()
        lc = TaskLifecycle(t)
        lc.assign("llm-1")
        lc.start_running("c1")
        lc.submit_for_review()
        lc.mark_passed()
        lc.commit("abc123")
        assert t.status == TaskStatus.COMMITTED
        assert t.commit_hash == "abc123"

    def test_review_to_retrying(self):
        t = _task()
        lc = TaskLifecycle(t)
        lc.assign("llm-1")
        lc.start_running("c1")
        lc.submit_for_review()
        lc.mark_failed("TypeError")
        lc.retry()
        assert t.status == TaskStatus.RETRYING
        assert t.retry_count == 1

    def test_blocked_after_max_retries(self):
        t = _task()
        t.retry_count = MAX_RETRIES
        lc = TaskLifecycle(t)
        lc.assign("llm-1")
        lc.start_running("c1")
        lc.submit_for_review()
        lc.mark_failed("still broken")
        lc.retry()
        assert t.status == TaskStatus.BLOCKED

    def test_pending_to_committed_raises(self):
        t = _task()
        lc = TaskLifecycle(t)
        with pytest.raises(InvalidTransitionError):
            lc.commit("abc123")

    def test_retry_count_never_exceeds_max(self):
        t = _task()
        t.retry_count = MAX_RETRIES
        lc = TaskLifecycle(t)
        lc.assign("llm-1")
        lc.start_running("c1")
        lc.submit_for_review()
        lc.mark_failed("err")
        lc.retry()
        assert t.retry_count == MAX_RETRIES
        assert t.status == TaskStatus.BLOCKED
