"""Quality-Gates in `sdd finalize` und im Auto-Merge (SPEC-0054 FR-10, CON-0196 INV-08).

Jede Entscheidung wird mit Report-Pfad, Git-Stand und Schema-Version als Eintrag
`quality-gates` in `.sdd/pipeline/<SPEC>-gate.json` belegt.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import QUALITY_FILE, QualityConfigError
from .diff import DiffError
from .settings import QualitySettings

GATE_PHASE = "quality-gates"
SUPPORTED_SCHEMA_VERSIONS = (1,)


@dataclass
class QualityGateDecision:
    mode: str
    passed: bool | None
    message: str = ""


def check_quality_gates(root: Path, spec_id: str, raw_config: dict, *,
                        respect_mode: bool = True) -> QualityGateDecision:
    """passed None: nicht anwendbar (keine quality.yaml, keine Gates oder Modus off)."""
    from ..gate import ExecutionGate
    from .measure import measure

    settings = QualitySettings.from_raw(raw_config)
    mode = settings.finalize if respect_mode else "block"
    if mode == "off" or not (root / QUALITY_FILE).is_file() or not settings.gates:
        return QualityGateDecision(mode, None, "Quality-Gates nicht anwendbar")
    try:
        ergebnis = measure(root, spec_id=spec_id, reuse_test_run=True, raw_config=raw_config)
    except (QualityConfigError, DiffError, FileNotFoundError) as exc:
        return QualityGateDecision(mode, False, f"Quality-Gates nicht auswertbar: {exc}")
    report = ergebnis.report
    passed = ergebnis.gates_passed and report["schema_version"] in SUPPORTED_SCHEMA_VERSIONS
    fehlgeschlagen = [f"{g['expression']} ({g.get('reason', '')})"
                      for g in ergebnis.gates if not g["passed"]]
    ExecutionGate(root).mark_phase_complete(
        spec_id, GATE_PHASE, result="ok" if passed else "failed",
        report_path=ergebnis.report_path, git_sha=report["git_sha"],
        schema_version=report["schema_version"], gates=ergebnis.gates)
    meldung = ("Quality-Gates bestanden" if passed
               else "Quality-Gates nicht bestanden: " + "; ".join(fehlgeschlagen))
    return QualityGateDecision(mode, passed, meldung)
