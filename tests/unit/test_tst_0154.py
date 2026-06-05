"""TST-0154: AutopilotStateMachine — Transitionen, Iterationszähler, Fortschritts-Check."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from sdd_cli.autopilot import AutopilotConfig, AutopilotStateMachine


def _make_machine(
    runner_sequence: list[tuple[int, str]],
    max_fix_iterations: int = 3,
    progress_check: bool = True,
    automated_gate_approval: bool = False,
) -> tuple[AutopilotStateMachine, list[str]]:
    """Helper: runner liefert Responses in Reihenfolge; gibt Machine + phase_log zurück."""
    calls = iter(runner_sequence)
    phase_log: list[str] = []

    def mock_runner(*args, timeout=120):
        try:
            return next(calls)
        except StopIteration:
            return (0, "ok")

    cfg = AutopilotConfig(
        max_fix_iterations=max_fix_iterations,
        progress_check=progress_check,
        automated_gate_approval=automated_gate_approval,
        notify_on_escalation=False,  # kein Terminal-Prompt in Tests
    )
    machine = AutopilotStateMachine(
        spec_id="SPEC-TEST",
        config=cfg,
        on_phase=lambda phase, detail: phase_log.append(phase),
        _sdd_runner=mock_runner,
    )
    return machine, phase_log


def test_green_path_all_phases():
    """Vollständiger grüner Durchlauf: decompose → implement → test → review → finalize → done."""
    machine, log = _make_machine([
        (0, "Tasks: 3"),          # decompose
        (0, "ok"),                # implement
        (0, "PASSED 5 tests"),    # test
        (0, "approved"),          # review
        (0, "finalized"),         # finalize
    ])
    report = machine.run()
    assert report.final_phase == "done"
    assert "done" in log
    assert report.escalation_reason == ""


def test_decompose_failure_escalates():
    machine, log = _make_machine([(1, "error: no tasks")])
    report = machine.run()
    assert report.final_phase == "escalated"
    assert "decompose failed" in report.escalation_reason.lower()


def test_test_failure_enters_fix_loop():
    machine, log = _make_machine([
        (0, "Tasks: 2"),              # decompose
        (0, "ok"),                    # implement (1st)
        (1, "FAILED tests/a.py::x"),  # test fails
        (0, "ok"),                    # implement (fix loop)
        (0, "PASSED"),                # test passes
        (0, "approved"),              # review
        (0, "finalized"),             # finalize
    ])
    report = machine.run()
    assert report.final_phase == "done"
    assert report.iterations >= 1


def test_review_rejection_enters_fix_loop():
    machine, log = _make_machine([
        (0, "Tasks: 1"),              # decompose
        (0, "ok"),                    # implement
        (0, "PASSED"),                # test green
        (1, "changes_requested"),     # review rejected
        (0, "ok"),                    # implement fix
        (0, "PASSED"),                # test green
        (0, "approved"),              # review approved
        (0, "finalized"),             # finalize
    ])
    report = machine.run()
    assert report.final_phase == "done"


def test_max_fix_iterations_reached_escalates():
    machine, log = _make_machine(
        runner_sequence=[
            (0, "Tasks"),   # decompose
            (0, "ok"),      # implement
            (1, "FAILED tests/a.py::x"),  # test fails each time
            (0, "ok"),      # implement fix 1
            (1, "FAILED tests/a.py::x"),  # test still failing
            (0, "ok"),      # implement fix 2
            (1, "FAILED tests/a.py::x"),  # test still failing
            (0, "ok"),      # implement fix 3 — after max iterations
        ],
        max_fix_iterations=3,
        progress_check=False,  # deaktiviert damit nur Zähler zählt
    )
    report = machine.run()
    assert report.final_phase == "escalated"
    assert "max_fix_iterations" in report.escalation_reason


def test_no_progress_escalates_early():
    """Mit progress_check=True und gleichen fehlenden Tests → Eskalation vor max."""
    machine, log = _make_machine(
        runner_sequence=[
            (0, "Tasks"),
            (0, "ok"),
            (1, "FAILED tests/a.py::same_test"),  # iteration 1
            (0, "ok"),
            (1, "FAILED tests/a.py::same_test"),  # iteration 2 — kein Fortschritt
        ],
        max_fix_iterations=5,
        progress_check=True,
    )
    report = machine.run()
    assert report.final_phase == "escalated"
    assert "progress" in report.escalation_reason.lower()


def test_iteration_counter_increments():
    machine, log = _make_machine(
        runner_sequence=[
            (0, "Tasks"),
            (0, "ok"),
            (1, "FAILED tests/a.py::t1"),
            (0, "ok"),
            (1, "FAILED tests/a.py::t2"),  # different test — progress!
            (0, "ok"),
            (1, "FAILED tests/a.py::t3"),
            (0, "ok"),
            (0, "PASSED"),
            (0, "approved"),
            (0, "finalized"),
        ],
        max_fix_iterations=5,
        progress_check=True,
    )
    report = machine.run()
    assert report.iterations >= 2


def test_automated_gate_approval_calls_sdd_spec_approve():
    calls: list[tuple] = []

    def runner(*args, timeout=120):
        calls.append(args)
        if args[0] == "review":
            return (0, "approved")
        if args[0] == "decompose":
            return (0, "Tasks: 1")
        return (0, "ok")

    cfg = AutopilotConfig(automated_gate_approval=True, notify_on_escalation=False)
    machine = AutopilotStateMachine("SPEC-X", cfg, _sdd_runner=runner)
    report = machine.run()
    approve_calls = [c for c in calls if c[0] == "spec" and "approve" in c]
    assert len(approve_calls) == 1


def test_transitions_logged():
    machine, log = _make_machine([
        (0, "Tasks"),
        (0, "ok"),
        (0, "PASSED"),
        (0, "approved"),
        (0, "ok"),
    ])
    machine.run()
    assert "decomposing" in log
    assert "implementing" in log
    assert "testing" in log
    assert "reviewing" in log
    assert "finalizing" in log
