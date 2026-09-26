"""Gates pro Task (SPEC-0061 FR-07, CON-0213 INV-06).

Nach jedem Implementer-Versuch laufen die Gates aus `pipeline.task_gates`. `tests` ist das
GREEN-Gate des Mediators; hier stehen `architecture` (Regeln aus `.sdd/architecture.yaml`) und
`lint` (Sonde aus `.sdd/quality.yaml`). Beide bewerten nur die Dateien, die der Task geändert hat,
damit Altlasten anderer Dateien keinen Task blockieren. Ohne Konfiguration im Projekt ist ein Gate
`n/a` und blockiert nie.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_TASK_GATES = ("tests", "architecture")


@dataclass
class GateResult:
    gate: str
    status: str  # ok | failed | n/a
    reason: str = ""
    findings: list[str] = field(default_factory=list)

    @property
    def blocks(self) -> bool:
        return self.status == "failed"

    def event_detail(self) -> dict:
        detail = {"gate": self.gate, "status": self.status}
        if self.reason:
            detail["reason"] = self.reason
        if self.findings:
            detail["findings"] = self.findings[:10]
        return detail


def task_gates(raw_config: Mapping) -> list[str]:
    gates = (raw_config.get("pipeline") or {}).get("task_gates")
    return list(gates) if isinstance(gates, list) else list(DEFAULT_TASK_GATES)


def architecture_gate(root: Path, raw_config: Mapping, changed: list[str]) -> GateResult:
    from ..quality.arch.baseline import Baseline, BaselineError
    from ..quality.arch.evaluator import evaluate_architecture
    from ..quality.arch.rules import ArchConfigError, load_architecture
    from ..quality.config import QualityConfigError, load_quality_config
    from ..quality.files import collect_files
    from ..quality.parsers import DepsGraph
    from ..quality.probe import ProbeRun
    from ..quality.settings import QualitySettings

    if not (root / ".sdd" / "architecture.yaml").is_file():
        return GateResult("architecture", "n/a", "keine .sdd/architecture.yaml")
    try:
        arch = load_architecture(root)
        qcfg = load_quality_config(root)
        baseline = Baseline.load(root)
    except (FileNotFoundError, ArchConfigError, QualityConfigError, BaselineError) as exc:
        return GateResult("architecture", "n/a", f"nicht auswertbar: {exc}")
    probe = qcfg.probe_for_role("deps")
    if probe is None:
        return GateResult("architecture", "n/a", "keine Sonde mit role: deps")
    outcome = ProbeRun(root, collect_files(root, qcfg.paths, qcfg.exclude)).execute(probe)
    if not outcome.ok or not isinstance(outcome.result, DepsGraph):
        return GateResult("architecture", "n/a", f"Sonde {probe.name}: {outcome.reason}")
    ergebnis = evaluate_architecture(arch, outcome.result, QualitySettings.from_raw(raw_config),
                                     baseline=baseline, root=root)
    neu = [v for v in ergebnis.violations
           if v.severity == "error" and not v.baselined and v.file in set(changed)]
    if neu:
        return GateResult("architecture", "failed", f"{len(neu)} neue Verstöße",
                          [f"{v.rule} {v.file}:{v.line} {v.symbol} ({v.adr})" for v in neu])
    return GateResult("architecture", "ok")


def lint_gate(root: Path, raw_config: Mapping, changed: list[str]) -> GateResult:
    from ..quality.config import QualityConfigError, load_quality_config
    from ..quality.parsers import FindingsResult
    from ..quality.probe import ProbeRun

    name = str((raw_config.get("pipeline") or {}).get("lint_probe") or "lint")
    try:
        qcfg = load_quality_config(root)
    except (FileNotFoundError, QualityConfigError) as exc:
        return GateResult("lint", "n/a", f"keine gültige .sdd/quality.yaml ({exc})")
    probe = next((p for p in qcfg.probes if p.name == name), None)
    if probe is None:
        return GateResult("lint", "n/a", f"keine Sonde {name!r}")
    if not changed:
        return GateResult("lint", "ok")
    outcome = ProbeRun(root, changed).execute(probe)
    if not outcome.ok or not isinstance(outcome.result, FindingsResult):
        return GateResult("lint", "n/a", f"Sonde {name}: {outcome.reason}")
    fehler = [f for f in outcome.result.findings if f.severity == "error" and f.file in changed]
    if fehler:
        return GateResult("lint", "failed", f"{len(fehler)} Befunde der Stufe error",
                          [f"{f.rule} {f.file}:{f.line} {f.message}" for f in fehler])
    return GateResult("lint", "ok")


def run_task_gates(root: Path, raw_config: Mapping, changed: list[str]) -> list[GateResult]:
    """Alle Gates außer `tests` (das prüft der Mediator selbst) in der konfigurierten Reihenfolge."""
    ergebnisse = []
    for gate in task_gates(raw_config):
        if gate == "architecture":
            ergebnisse.append(architecture_gate(root, raw_config, changed))
        elif gate == "lint":
            ergebnisse.append(lint_gate(root, raw_config, changed))
    return ergebnisse
