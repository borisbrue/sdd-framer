"""`sdd quality doctor` (SPEC-0054 FR-13): jede Sonde einmal auf einer kleinen Dateimenge."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import load_quality_config
from .files import collect_files
from .metrics import FINDING_METRICS
from .normalize import BUILTIN_NORMALIZATION
from .parsers import MetricsResult, TestSuiteResult
from .probe import ProbeRun

MINIMAL_FILES = 20


@dataclass
class DoctorEntry:
    probe: str
    ready: bool
    messages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"probe": self.probe, "ready": self.ready, "messages": self.messages}


def run_doctor(root: Path) -> list[DoctorEntry]:
    qcfg = load_quality_config(root)
    dateien = collect_files(root, qcfg.paths, qcfg.exclude)[:MINIMAL_FILES]
    bekannt = set(qcfg.normalization) | set(BUILTIN_NORMALIZATION)
    eintraege = []
    for probe in qcfg.probes:
        outcome = ProbeRun(root, dateien).execute(probe)
        e = DoctorEntry(probe.name, outcome.ok)
        if not outcome.ok:
            e.messages.append(outcome.reason or "nicht einsatzbereit")
            eintraege.append(e)
            continue
        e.messages.append(f"Format {probe.format} gültig")
        if outcome.tool_version:
            e.messages.append(f"Version {outcome.tool_version}")
        fehlend = []
        if probe.metric and probe.metric not in FINDING_METRICS and probe.metric not in bekannt:
            fehlend.append(probe.metric)
        if isinstance(outcome.result, MetricsResult):
            fehlend += [m.name for m in outcome.result.metrics
                        if m.scope == "project" and m.name not in bekannt]
        if fehlend:
            e.ready = False
            e.messages.append(f"Normierung fehlt ({', '.join(dict.fromkeys(fehlend))})")
        if probe.role == "tests" and isinstance(outcome.result, TestSuiteResult):
            if any(c.frs for c in outcome.result.cases):
                e.messages.append("FR-Markierung erkannt")
            else:
                e.messages.append("keine FR-Markierung erkannt")
        eintraege.append(e)
    return eintraege
