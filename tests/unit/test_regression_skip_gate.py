"""Ein uebersprungener LLM-Check darf regression-ok nicht markieren.

`sdd spec regression` markierte die Phase auch dann, wenn Stufe 2 gar nicht
lief:

    ⚠ LLM-Check übersprungen (claude CLI Timeout nach 120s.)
    ✓ Gate-Phase regression-ok markiert

Der erste Lauf derselben Spec hatte zwei Widersprueche mit Severity ERROR
gefunden. Ein Timeout wurde damit zur Umgehung des Gates: regression-ok ist
Vorbedingung fuer spec-approved und damit fuer execute-unlocked.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

from sdd_cli.config import SddConfig
from sdd_cli.gate import PHASE_ORDER, ExecutionGate


def _projekt(tmp_path: Path) -> SddConfig:
    (tmp_path / ".sdd" / "specs").mkdir(parents=True)
    (tmp_path / ".sdd" / "pipeline").mkdir(parents=True)
    (tmp_path / ".sdd" / "config.yaml").write_text("version: 1\n", encoding="utf-8")
    (tmp_path / ".sdd" / "specs" / "SPEC-0001-demo.md").write_text(
        "---\nid: SPEC-0001\ntitle: Demo\nstatus: draft\nowner: B\nversion: 0.1.0\n"
        "---\n\n# Demo\n", encoding="utf-8")
    return SddConfig(root=tmp_path, raw={})


def _kette_bis_regression(cfg: SddConfig) -> ExecutionGate:
    """Alle Vorgaengerphasen abschliessen, damit nur der Skip entscheidet."""
    g = ExecutionGate(cfg.root)
    for phase in PHASE_ORDER[:PHASE_ORDER.index("regression-ok")]:
        g.mark_phase_complete("SPEC-0001", phase)
    return g


def _mark(cfg: SddConfig, **kwargs) -> bool:
    from sdd_cli.main import _mark_regression_ok
    return _mark_regression_ok(cfg, "SPEC-0001", **kwargs)


def _phase(cfg: SddConfig):
    return ExecutionGate(cfg.root)._load("SPEC-0001").get("pipeline_phase")


class TestSkipVerhindertMarkierung:
    def test_uebersprungener_check_markiert_nicht(self, tmp_path):
        """Der gemeldete Fall."""
        cfg = _projekt(tmp_path)
        _kette_bis_regression(cfg)

        assert _mark(cfg, llm_skipped=True,
                     skip_reason="claude CLI Timeout nach 120s.") is False
        assert _phase(cfg) != "regression-ok"

    def test_kette_bleibt_danach_blockiert(self, tmp_path):
        """spec-approved prueft nur regression-ok — das darf nicht fallen."""
        cfg = _projekt(tmp_path)
        g = _kette_bis_regression(cfg)
        _mark(cfg, llm_skipped=True, skip_reason="Timeout")

        assert g.can_start_phase("SPEC-0001", "spec-approved").allowed is False

    def test_kein_history_eintrag(self, tmp_path):
        cfg = _projekt(tmp_path)
        _kette_bis_regression(cfg)
        _mark(cfg, llm_skipped=True, skip_reason="Timeout")

        history = ExecutionGate(cfg.root)._load("SPEC-0001").get("phase_history", [])
        assert not [e for e in history if e.get("phase") == "regression-ok"]

    def test_kein_abbruch(self, tmp_path):
        """Die Analyse bleibt nuetzlich — nur die Markierung entfaellt."""
        cfg = _projekt(tmp_path)
        _kette_bis_regression(cfg)
        assert _mark(cfg, llm_skipped=True, skip_reason="Timeout") is False


class TestVollstaendigerLaufMarkiertWeiterhin:
    def test_ohne_skip_wird_markiert(self, tmp_path):
        cfg = _projekt(tmp_path)
        _kette_bis_regression(cfg)

        assert _mark(cfg, llm_skipped=False) is True
        assert _phase(cfg) == "regression-ok"

    def test_vorgaengerpruefung_gilt_weiterhin(self, tmp_path):
        """Der Guard aus #46 bleibt wirksam."""
        cfg = _projekt(tmp_path)
        assert _mark(cfg, llm_skipped=False) is False


class TestAusdrucklicheBestaetigung:
    def test_flag_erlaubt_die_markierung(self, tmp_path):
        cfg = _projekt(tmp_path)
        _kette_bis_regression(cfg)

        assert _mark(cfg, llm_skipped=True, skip_reason="Timeout",
                     allow_skipped_llm=True) is True
        assert _phase(cfg) == "regression-ok"

    def test_flag_umgeht_die_vorgaengerpruefung_nicht(self, tmp_path):
        """Das Flag betrifft nur die LLM-Stufe, nicht die Phasenkette."""
        cfg = _projekt(tmp_path)
        assert _mark(cfg, llm_skipped=True, skip_reason="Timeout",
                     allow_skipped_llm=True) is False

    def test_kommando_kennt_das_flag(self):
        from sdd_cli.main import cli
        params = {p.name for p in cli.commands["spec"].commands["regression"].params}
        assert "allow_skipped_llm" in params
