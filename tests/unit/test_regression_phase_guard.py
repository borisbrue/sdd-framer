"""`sdd spec regression` darf die Gate-Kette nicht ueberspringbar machen.

Der Befehl markierte regression-ok an beiden Ausgabepfaden ohne
can_start_phase-Pruefung — als einziger Phasenuebergang der CLI. Auf einer
frischen Spec genuegte der Aufruf, um pipeline_phase auf regression-ok zu
setzen; da `sdd spec approve` nur seinen direkten Vorgaenger prueft, war die
Kette danach bis execute-unlocked durchlaufbar. Die Phasen 1 bis 6 liessen
sich vollstaendig ueberspringen.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

from sdd_cli.config import SddConfig
from sdd_cli.gate import PHASE_ORDER, ExecutionGate


def _project(tmp_path: Path) -> SddConfig:
    (tmp_path / ".sdd" / "specs").mkdir(parents=True)
    (tmp_path / ".sdd" / "pipeline").mkdir(parents=True)
    (tmp_path / ".sdd" / "config.yaml").write_text("version: 1\n", encoding="utf-8")
    (tmp_path / ".sdd" / "specs" / "SPEC-0001-demo.md").write_text(
        "---\nid: SPEC-0001\ntitle: Demo\nstatus: draft\nowner: B\nversion: 0.1.0\n"
        "---\n\n# Demo\n", encoding="utf-8")
    return SddConfig(root=tmp_path, raw={})


def _mark(cfg: SddConfig) -> bool:
    from sdd_cli.main import _mark_regression_ok
    return _mark_regression_ok(cfg, "SPEC-0001")


def _phase(cfg: SddConfig):
    return ExecutionGate(cfg.root)._load("SPEC-0001").get("pipeline_phase")


class TestGuard:
    def test_fresh_spec_is_not_marked(self, tmp_path):
        """Der gemeldete Fall: auf einer frischen Spec darf regression-ok nicht fallen.

        pipeline_phase steht danach auf spec-draft, nicht auf None:
        can_start_phase() zieht die zustandsbasierten Phasen nach (CON-0025).
        Das ist gewollt – entscheidend ist, dass regression-ok nicht gesetzt wird.
        """
        cfg = _project(tmp_path)
        assert _mark(cfg) is False
        assert _phase(cfg) != "regression-ok"

    def test_chain_stays_unpassable_afterwards(self, tmp_path):
        """spec-approved prueft nur regression-ok – das darf nicht gesetzt sein."""
        cfg = _project(tmp_path)
        _mark(cfg)
        g = ExecutionGate(cfg.root)
        assert g.can_start_phase("SPEC-0001", "spec-approved").allowed is False

    def test_marks_when_predecessor_is_complete(self, tmp_path):
        cfg = _project(tmp_path)
        g = ExecutionGate(cfg.root)
        for phase in PHASE_ORDER[:PHASE_ORDER.index("regression-ok")]:
            g.mark_phase_complete("SPEC-0001", phase)

        assert _mark(cfg) is True
        assert _phase(cfg) == "regression-ok"

    def test_marking_is_the_only_thing_skipped(self, tmp_path):
        """Kein Abbruch: der Aufruf kehrt zurueck, statt das Programm zu beenden."""
        cfg = _project(tmp_path)
        result = _mark(cfg)  # wuerde bei sys.exit() gar nicht erst zurueckkehren
        assert result is False

    def test_no_history_entry_is_written(self, tmp_path):
        cfg = _project(tmp_path)
        _mark(cfg)
        history = ExecutionGate(cfg.root)._load("SPEC-0001").get("phase_history", [])
        assert not [e for e in history if e.get("phase") == "regression-ok"]


class TestEveryCliTransitionIsGuarded:
    def test_regression_ok_is_no_longer_the_exception(self):
        """Absicherung gegen einen Rueckfall: kein ungeschuetzter Uebergang mehr."""
        src = (Path(__file__).resolve().parents[2] / "tool" / "sdd_cli"
               / "main.py").read_text(encoding="utf-8")
        marks = src.count('g.mark_phase_complete(spec_id, "regression-ok")')
        assert marks == 1, (
            f"regression-ok wird an {marks} Stellen markiert – erwartet ist genau "
            f"eine, naemlich innerhalb von _mark_regression_ok(). Mehr heisst: "
            f"der Guard wird irgendwo umgangen."
        )
