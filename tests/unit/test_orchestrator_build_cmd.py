"""--build-cmd und orchestrator.build_command wirken (#111).

Bis #111 warnte der Orchestrator nur, dass das Build-Kommando ignoriert wird
(#114). Jetzt reicht er es an die Finalisierung weiter, die es im Dev-Container
vor den Tests ausfuehrt — siehe tests/unit/test_finalize_build.py. Ein
gescheiterter Build wird zum Fehlerkontext des naechsten Versuchs, wie vor 45b29e6.
"""
from __future__ import annotations

import ast
import inspect
from types import SimpleNamespace
from unittest.mock import patch


def _bericht(**kw):
    from sdd_cli.finalize import FinalizeReport

    basis = dict(spec_id="SPEC-0007", branch="b", commit_hash="abc", tests_passed=True,
                 test_output="1 passed", pr_url=None, pr_path=None, error=None)
    basis.update(kw)
    return FinalizeReport(**basis)


class _FakeFinalizer:
    aufrufe: list[dict] = []
    bericht = None

    def __init__(self, cfg, dry_run=False):
        pass

    def run(self, spec_id, **kwargs):
        type(self).aufrufe.append(kwargs)
        return type(self).bericht


def _lauf(tmp_path, bericht, *, build_cmd=None, config_cmd=""):
    from sdd_cli import orchestrator

    cfg = SimpleNamespace(root=tmp_path, raw={"orchestrator": {"build_command": config_cmd}})
    _FakeFinalizer.aufrufe = []
    _FakeFinalizer.bericht = bericht
    schritte: list[str] = []
    with patch.object(orchestrator, "_run", return_value=(0, "main")), \
         patch.object(orchestrator, "_git", return_value=(0, "")), \
         patch.object(orchestrator, "_load_spec", return_value="spec"), \
         patch.object(orchestrator, "_load_agents_md", return_value=""), \
         patch.object(orchestrator, "_load_contracts", return_value=[]), \
         patch.object(orchestrator, "_call_code_gen_agent", return_value=([], "x")), \
         patch.object(orchestrator, "_create_branch_and_commit"), \
         patch.object(orchestrator, "_open_failure_issue", return_value=None), \
         patch.object(orchestrator, "_mark_spec_implemented"), \
         patch.object(orchestrator, "_label_pr"), \
         patch.object(orchestrator, "_merge_pr"), \
         patch("sdd_cli.autonomy.record_pr_result"), \
         patch("sdd_cli.autonomy.auto_merge_allowed", return_value=False), \
         patch("sdd_cli.finalize.SpecFinalizer", _FakeFinalizer):
        report = orchestrator.run_pipeline(
            cfg, "SPEC-0007", build_cmd=build_cmd, max_retries=1, no_pr=True,
            on_step=schritte.append,
        )
    return report, schritte


def test_build_cmd_option_erreicht_die_finalisierung(tmp_path):
    _lauf(tmp_path, _bericht(build_passed=True), build_cmd="make test")
    assert _FakeFinalizer.aufrufe[0]["build_cmd"] == "make test"


def test_config_build_command_erreicht_die_finalisierung(tmp_path):
    _lauf(tmp_path, _bericht(build_passed=True), config_cmd="npm run build")
    assert _FakeFinalizer.aufrufe[0]["build_cmd"] == "npm run build"


def test_ohne_build_kommando_geht_none_weiter(tmp_path):
    _lauf(tmp_path, _bericht())
    assert _FakeFinalizer.aufrufe[0]["build_cmd"] is None


def test_gescheiterter_build_wird_fehlerkontext(tmp_path):
    bericht = _bericht(tests_passed=False, test_output="", build_passed=False,
                       build_output="make: *** [all] Fehler 2", error="Build fehlgeschlagen")
    report, schritte = _lauf(tmp_path, bericht, build_cmd="make")
    assert "Fehler 2" in (report.attempts[0].error or "")
    assert any("Build fehlgeschlagen" in s for s in schritte), schritte
    assert report.final_status == "failed"


def test_keine_warnung_mehr(tmp_path):
    _, schritte = _lauf(tmp_path, _bericht(build_passed=True), build_cmd="make")
    assert not any("#111" in s for s in schritte), schritte


def test_kein_verweis_auf_die_geloeschte_variable():
    """Zeile 470 verwies auf die lokale Variable `build_output`, die 45b29e6
    entfernt hat (F821). Das Feld `fin_report.build_output` ist etwas anderes."""
    from sdd_cli import orchestrator

    baum = ast.parse(inspect.getsource(orchestrator.run_pipeline))
    namen = {n.id for n in ast.walk(baum) if isinstance(n, ast.Name)}
    assert "build_output" not in namen
