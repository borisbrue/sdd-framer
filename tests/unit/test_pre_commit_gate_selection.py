"""Das pre-commit-Gate darf nur bei tatsaechlich roten Tests blockieren.

Zwei Defekte in _run_tests, beide aus #27:

1. `pytest tests/ -k "<SPEC-ID>"` setzte ein pytest im PATH voraus und ignorierte
   test_runner.command.
2. `-k` filtert gegen Test-, Klassen- und Dateinamen. Spec-IDs kommen dort nur
   zufaellig vor. Traf der Filter nichts, lieferte pytest Exitcode 5, den
   `return result.returncode` ungeprueft als roten Lauf durchreichte:
   104 gruene Tests, 0 ausgefuehrt, Commit abgebrochen.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

from sdd_cli.pre_commit_hook import PreCommitHook

# TestResult aliasen: pytest wuerde die Dataclass sonst als Testklasse sammeln.
from sdd_cli.test_runner import RunReport
from sdd_cli.test_runner import TestResult as Result


def _report(spec_id: str, *tests: Result) -> RunReport:
    return RunReport(spec_id=spec_id, runner="pytest", started_at="", duration_s=0.0,
                     exit_code=0, tests=list(tests))


def _hook(root: Path) -> PreCommitHook:
    (root / ".sdd").mkdir(parents=True, exist_ok=True)
    (root / ".sdd" / "config.yaml").write_text("version: 1\n", encoding="utf-8")
    return PreCommitHook(project_root=root, cfg_raw={})


class TestOnlyRedTestsBlock:
    def test_red_test_blocks(self, tmp_path):
        rep = _report("SPEC-0001", Result("TST-1", "tests/a.py", "failed", message="boom"))
        with patch("sdd_cli.test_runner.run", return_value=rep):
            assert _hook(tmp_path)._run_tests({"SPEC-0001"}) == 1

    def test_green_test_passes(self, tmp_path):
        rep = _report("SPEC-0001", Result("TST-1", "tests/a.py", "passed"))
        with patch("sdd_cli.test_runner.run", return_value=rep):
            assert _hook(tmp_path)._run_tests({"SPEC-0001"}) == 0

    def test_nothing_collected_does_not_block(self, tmp_path):
        """Der gemeldete Fall: nichts ausgefuehrt ist kein rotes Ergebnis."""
        rep = _report("SPEC-0001", Result("TST-1", "tests/a.py", "skipped",
                                              message="Keine Tests gesammelt"))
        with patch("sdd_cli.test_runner.run", return_value=rep):
            assert _hook(tmp_path)._run_tests({"SPEC-0001"}) == 0

    def test_missing_runner_does_not_block(self, tmp_path):
        """Infrastrukturproblem darf das Repository nicht commit-unfaehig machen."""
        with patch("sdd_cli.test_runner.run", side_effect=RuntimeError("'uv' nicht gefunden")):
            assert _hook(tmp_path)._run_tests({"SPEC-0001"}) == 0

    def test_spec_without_tests_does_not_block(self, tmp_path):
        with patch("sdd_cli.test_runner.run", side_effect=ValueError("keine Tests im Frontmatter")):
            assert _hook(tmp_path)._run_tests({"SPEC-0001"}) == 0

    def test_one_red_among_many_blocks(self, tmp_path):
        reports = {
            "SPEC-0001": _report("SPEC-0001", Result("TST-1", "a.py", "passed")),
            "SPEC-0002": _report("SPEC-0002", Result("TST-2", "b.py", "error", message="x")),
        }
        with patch("sdd_cli.test_runner.run", side_effect=lambda cfg, sid: reports[sid]):
            assert _hook(tmp_path)._run_tests({"SPEC-0001", "SPEC-0002"}) == 1

    def test_does_not_shell_out_to_bare_pytest(self, tmp_path):
        """Defekt 1: blankes `pytest` setzte ein Binary im PATH voraus."""
        rep = _report("SPEC-0001", Result("TST-1", "tests/a.py", "passed"))
        with patch("sdd_cli.test_runner.run", return_value=rep):
            with patch.object(subprocess, "run") as spawned:
                _hook(tmp_path)._run_tests({"SPEC-0001"})
        assert not spawned.called, "Das Gate darf keinen eigenen pytest-Prozess starten"


class TestRunnerHandlesExitFive:
    """test_runner._run_pytest: Exitcode 5 ist ein leerer Lauf, kein Fehlschlag."""

    def _cfg(self, root: Path, command: str = "pytest"):
        from sdd_cli.config import load_config
        (root / ".sdd").mkdir(parents=True, exist_ok=True)
        (root / ".sdd" / "config.yaml").write_text(
            f"version: 1\ntest_runner:\n  command: {command}\n  extra_args: []\n"
            f"  timeout_per_spec: 30\n", encoding="utf-8")
        return load_config(root)

    def test_exit_five_is_skipped_not_failed(self, tmp_path):
        from sdd_cli import test_runner

        artifact = tmp_path / "tests" / "test_leer.py"
        artifact.parent.mkdir(parents=True)
        artifact.write_text("# keine Tests\n", encoding="utf-8")

        status, _, message = test_runner._run_pytest(
            self._cfg(tmp_path), "tests/test_leer.py", timeout=60)

        assert status == "skipped", f"Exitcode 5 als {status!r} gewertet"
        assert "Keine Tests gesammelt" in message

    def test_multiword_runner_command_is_supported(self, tmp_path):
        """`uv run pytest` scheiterte an shutil.which('uv run pytest')."""
        from sdd_cli import test_runner

        artifact = tmp_path / "tests" / "test_x.py"
        artifact.parent.mkdir(parents=True)
        artifact.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
        cfg = self._cfg(tmp_path, command="env pytest")

        captured = {}

        def fake_run(cmd, **kw):
            captured["cmd"] = cmd
            class R:
                returncode = 0
                stdout = ""
                stderr = ""
            return R()

        with patch.object(test_runner.subprocess, "run", fake_run):
            status, _, _ = test_runner._run_pytest(cfg, "tests/test_x.py", timeout=30)

        assert status == "passed"
        assert captured["cmd"][:2] == ["env", "pytest"], captured["cmd"]


class TestRunnerResolution:
    """`sys.executable -m pytest` ist der Interpreter, der sdd ausfuehrt.

    Im sdd-Repo selbst stimmt das; in einem fremden Projekt hat dieser
    Interpreter kein pytest — und das landete als *fehlgeschlagener Test* im
    Report, blockierte also den Commit. Genau der gemeldete Schaden.
    """

    def setup_method(self):
        from sdd_cli import test_runner
        test_runner._RUNNER_CACHE.clear()

    def teardown_method(self):
        from sdd_cli import test_runner
        test_runner._RUNNER_CACHE.clear()

    def test_falls_back_to_pytest_on_path(self):
        from sdd_cli import test_runner

        def fake_run(cmd, **kw):
            class R:
                # Der eigene Interpreter kennt pytest nicht, das PATH-Binary schon.
                returncode = 0 if cmd[0] == "pytest" else 1
            return R()

        with patch.object(test_runner.subprocess, "run", fake_run):
            with patch.object(test_runner.shutil, "which", lambda _: "/usr/bin/pytest"):
                assert test_runner._resolve_runner("pytest") == ["pytest"]

    def test_raises_when_no_runner_works(self):
        import pytest as _pytest

        from sdd_cli import test_runner

        def fake_run(cmd, **kw):
            class R:
                returncode = 1
            return R()

        with patch.object(test_runner.subprocess, "run", fake_run):
            with patch.object(test_runner.shutil, "which", lambda _: None):
                with _pytest.raises(RuntimeError, match="Kein lauffaehiger Test-Runner"):
                    test_runner._resolve_runner("pytest")

    def test_missing_runner_surfaces_as_skip_not_red(self, tmp_path):
        """Der entscheidende Punkt: kein Runner darf nicht als roter Test gelten."""
        from sdd_cli import test_runner

        with patch.object(test_runner, "_resolve_runner",
                          side_effect=RuntimeError("Kein lauffaehiger Test-Runner")):
            with patch("sdd_cli.test_runner.run",
                       side_effect=RuntimeError("Kein lauffaehiger Test-Runner")):
                assert _hook(tmp_path)._run_tests({"SPEC-0001"}) == 0

    def test_result_is_cached(self):
        from sdd_cli import test_runner
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            class R:
                returncode = 0
            return R()

        with patch.object(test_runner.subprocess, "run", fake_run):
            test_runner._resolve_runner("pytest")
            test_runner._resolve_runner("pytest")
        assert len(calls) == 1, "Runner-Probe darf nicht bei jedem Testlauf erneut laufen"
