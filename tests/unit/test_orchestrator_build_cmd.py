"""--build-cmd wird nicht mehr still ignoriert (#111, ruff F841/F821).

SPEC-0026 hat den Build-Schritt aus der Orchestrator-Schleife entfernt. Die
Optionen --build-cmd (sdd orchestrate, sdd start --auto) und der Config-Schluessel
orchestrator.build_command blieben — und wurden seither wortlos verworfen.
"""
from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import patch


def _lauf(tmp_path, *, build_cmd=None, config_cmd=""):
    from sdd_cli import orchestrator

    cfg = SimpleNamespace(root=tmp_path, raw={"orchestrator": {"build_command": config_cmd}})
    schritte: list[str] = []
    with patch.object(orchestrator, "_run", return_value=(0, "main")), \
         patch.object(orchestrator, "_git", return_value=(0, "")), \
         patch.object(orchestrator, "_load_spec", return_value="spec"), \
         patch.object(orchestrator, "_load_agents_md", return_value=""), \
         patch.object(orchestrator, "_load_contracts", return_value=[]), \
         patch.object(orchestrator, "_call_code_gen_agent", return_value=([], "nichts")):
        report = orchestrator.run_pipeline(
            cfg, "SPEC-0007", build_cmd=build_cmd, dry_run=True, on_step=schritte.append,
        )
    return report, schritte


def _warnt(schritte) -> bool:
    return any("#111" in s and "Build-Kommando" in s for s in schritte)


def test_warnung_bei_build_cmd_option(tmp_path):
    report, schritte = _lauf(tmp_path, build_cmd="make test")
    assert report.final_status == "dry_run"
    assert _warnt(schritte), schritte


def test_warnung_bei_build_command_in_config(tmp_path):
    _, schritte = _lauf(tmp_path, config_cmd="npm test")
    assert _warnt(schritte), schritte


def test_keine_warnung_ohne_build_kommando(tmp_path):
    _, schritte = _lauf(tmp_path)
    assert not _warnt(schritte), schritte


def test_kein_verweis_auf_die_geloeschte_variable():
    """Zeile 470 verwies auf `build_output`, das 45b29e6 entfernt hat (F821)."""
    from sdd_cli import orchestrator

    code = [z for z in inspect.getsource(orchestrator.run_pipeline).splitlines()
            if not z.strip().startswith("#")]
    assert not any("build_output" in z for z in code)
