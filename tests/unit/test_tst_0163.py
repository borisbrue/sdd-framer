"""TST-0153: CommandQueue apply — DAG-Invarianz bei skip (offene Deps → reject)."""
from __future__ import annotations

import pytest

from sdd_cli.dag_command import (
    CommandQueue,
    ForceCloudCommand,
    ForceLocalCommand,
    InvariantViolation,
    PauseTaskCommand,
    RestartTaskCommand,
    ResumeTaskCommand,
    SchedulerState,
    SkipTaskCommand,
    build_command,
)


def _state(**kwargs) -> SchedulerState:
    return SchedulerState(**kwargs)


# ─── PauseTask / ResumeTask ──────────────────────────────────────────────────

def test_pause_adds_task_to_paused():
    state = _state()
    cmd = PauseTaskCommand(run_id="r", task_id="t1")
    cmd.apply(state)
    assert "t1" in state.paused_tasks


def test_resume_removes_task_from_paused():
    state = _state(paused_tasks={"t1"})
    cmd = ResumeTaskCommand(run_id="r", task_id="t1")
    cmd.apply(state)
    assert "t1" not in state.paused_tasks


# ─── ForceRoute ──────────────────────────────────────────────────────────────

def test_force_local_sets_override():
    state = _state()
    ForceLocalCommand(run_id="r", task_id="t1").apply(state)
    assert state.route_overrides["t1"] == "local"


def test_force_cloud_overrides_existing():
    state = _state(route_overrides={"t1": "local"})
    ForceCloudCommand(run_id="r", task_id="t1").apply(state)
    assert state.route_overrides["t1"] == "cloud"


# ─── SkipTask Invarianz ───────────────────────────────────────────────────────

def test_skip_task_with_no_open_deps_succeeds():
    state = _state(
        deps_by_task={"t2": {"t1"}},
        completed_tasks={"t1"},
    )
    SkipTaskCommand(run_id="r", task_id="t2").apply(state)
    assert "t2" in state.skipped_tasks


def test_skip_task_with_open_deps_raises():
    state = _state(deps_by_task={"t2": {"t1"}})  # t1 not completed
    with pytest.raises(InvariantViolation, match="open dependencies"):
        SkipTaskCommand(run_id="r", task_id="t2").apply(state)


def test_skip_task_dep_skipped_counts_as_done():
    state = _state(
        deps_by_task={"t2": {"t1"}},
        skipped_tasks={"t1"},
    )
    SkipTaskCommand(run_id="r", task_id="t2").apply(state)
    assert "t2" in state.skipped_tasks


# ─── RestartTask Invarianz ────────────────────────────────────────────────────

def test_restart_failed_task_succeeds():
    state = _state(failed_tasks={"t1"})
    RestartTaskCommand(run_id="r", task_id="t1").apply(state)
    assert "t1" in state.restart_tasks
    assert "t1" not in state.failed_tasks


def test_restart_non_failed_task_raises():
    state = _state()  # t1 not failed
    with pytest.raises(InvariantViolation, match="not in failed state"):
        RestartTaskCommand(run_id="r", task_id="t1").apply(state)


# ─── CommandQueue FIFO + drain ───────────────────────────────────────────────

def test_command_queue_fifo_order():
    q = CommandQueue()
    state = _state()
    q.enqueue_sync(PauseTaskCommand(run_id="r", task_id="a"))
    q.enqueue_sync(PauseTaskCommand(run_id="r", task_id="b"))
    errors = q.drain("r", state)
    assert not errors
    assert "a" in state.paused_tasks
    assert "b" in state.paused_tasks


def test_command_queue_invariant_error_logged_not_raised():
    q = CommandQueue()
    state = _state()  # no failed tasks
    q.enqueue_sync(RestartTaskCommand(run_id="r", task_id="x"))
    errors = q.drain("r", state)
    assert len(errors) == 1
    assert "not in failed state" in errors[0]


def test_build_command_unknown_type_raises():
    with pytest.raises(ValueError, match="Unknown command_type"):
        build_command("r", "t", "fly_to_moon")


def test_build_command_valid_types():
    for ct in ["pause_task", "resume_task", "force_local", "force_cloud", "skip_task", "restart_task"]:
        cmd = build_command("r", "t", ct)
        assert cmd.command_type == ct
