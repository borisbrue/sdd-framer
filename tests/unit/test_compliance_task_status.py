"""Das Compliance-Gate muss den Task-Status pruefen.

Die Kette prueft die FR->Test-Abdeckung, aber nicht, ob die Tasks der Spec
abgeschlossen sind. Gegen SPEC-0050 mit 7 Tasks auf `pending` meldete sie 0
Issues — `sdd finalize` haette ungeprueft auf `implemented` geschaltet, obwohl
task_lifecycle COMMITTED als Endzustand ohne ausgehende Uebergaenge definiert.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

from sdd_cli.frontmatter import Document
from sdd_cli.task_model import Task, TaskStatus


def _spec(status: str = "in-progress") -> Document:
    return Document(
        path=Path("/tmp/SPEC-0001.md"),
        frontmatter={"id": "SPEC-0001", "title": "Demo", "status": status},
        body="## 1. Funktionale Anforderungen\n\n- **FR-01:** etwas\n",
    )


def _task(title: str, status: TaskStatus) -> Task:
    return Task(id="t", spec_id="SPEC-0001", title=title, description="d",
                type="code", complexity="low", context_size="S",
                estimated_tokens=100, status=status)


def _issues(spec: Document, tasks: list[Task], cfg: dict | None = None,
            strict: bool = True):
    from sdd_cli.compliance import TaskCompletionChecker
    return TaskCompletionChecker(tasks, strict=strict).check(
        spec, cfg if cfg is not None else {})


class TestOpenTasksBlock:
    def test_pending_task_is_an_error(self):
        """Der gemeldete Fall."""
        issues = _issues(_spec(), [_task("Factory umstellen", TaskStatus.PENDING)])
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert "Factory umstellen" in issues[0].message

    def test_all_seven_pending_are_reported(self):
        tasks = [_task(f"T{i}", TaskStatus.PENDING) for i in range(7)]
        assert len([i for i in _issues(_spec(), tasks) if i.severity == "error"]) == 7

    def test_committed_tasks_pass(self):
        tasks = [_task("A", TaskStatus.COMMITTED), _task("B", TaskStatus.COMMITTED)]
        assert _issues(_spec(), tasks) == []

    def test_passed_counts_as_done(self):
        """finalize committet selbst – ein bestandener Task ist erledigte Arbeit."""
        assert _issues(_spec(), [_task("A", TaskStatus.PASSED)]) == []

    def test_failed_and_blocked_are_errors(self):
        for st in (TaskStatus.FAILED, TaskStatus.BLOCKED, TaskStatus.RUNNING):
            issues = _issues(_spec(), [_task("A", st)])
            assert issues and issues[0].severity == "error", st

    def test_status_is_named_in_the_message(self):
        issues = _issues(_spec(), [_task("A", TaskStatus.BLOCKED)])
        assert "blocked" in issues[0].message


class TestMissingDecomposition:
    def test_no_tasks_is_a_warning_not_an_error(self):
        """46 von 48 implemented-Specs haben keine Task-Datei.

        Ein Fehler wuerde finalize praktisch ueberall blockieren; sichtbar
        muss die Luecke trotzdem sein.
        """
        issues = _issues(_spec(), [])
        assert len(issues) == 1
        assert issues[0].severity == "warning"
        assert "keine Tasks dekomponiert" in issues[0].message

    def test_empty_list_does_not_read_as_all_done(self):
        assert _issues(_spec(), []) != []


class TestBoundaries:
    def test_implemented_spec_is_not_blocked_retroactively(self):
        """Wie bei FrCoverage: abgeschlossene Specs werden nicht ruecklaeufig geprueft."""
        assert _issues(_spec("implemented"), [_task("A", TaskStatus.PENDING)]) == []

    def test_switch_disables_the_check(self):
        cfg = {"compliance": {"task_completion_check": False}}
        assert _issues(_spec(), [_task("A", TaskStatus.PENDING)], cfg) == []

    def test_report_mode_warns_instead_of_blocking(self):
        """sdd validate ist ein Bericht, kein Gate – sonst faellt es im eigenen
        Repo mit 18 Fehlern aus, obwohl die Arbeit laengst gemerged ist."""
        issues = _issues(_spec(), [_task("A", TaskStatus.PENDING)], strict=False)
        assert len(issues) == 1 and issues[0].severity == "warning"

    def test_gate_mode_blocks(self):
        issues = _issues(_spec(), [_task("A", TaskStatus.PENDING)], strict=True)
        assert len(issues) == 1 and issues[0].severity == "error"

    def test_gate_callers_pass_strict(self):
        """finalize und spec approve entscheiden ueber einen Statuswechsel."""
        root = Path(__file__).resolve().parents[2] / "tool" / "sdd_cli"
        for name in ("finalize.py", "main.py"):
            src = (root / name).read_text(encoding="utf-8")
            assert "strict=True," in src, f"{name} ruft die Kette nicht im Gate-Modus"

    def test_checker_is_wired_into_the_chain(self):
        import inspect

        from sdd_cli import compliance
        src = inspect.getsource(compliance.run_compliance_chain)
        assert "TaskCompletionChecker(tasks, strict=strict)" in src
