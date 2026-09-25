"""Messung orchestrieren (SPEC-0054 FR-01..FR-12) – Facade für `sdd quality measure`.

Ablauf: Konfiguration prüfen → Dateimenge (optional Diff) → Sonden ausführen (Tests über den
Test-Runner aus SPEC-0006) → Anforderungen, Architektur, Codequalität, optional Judge →
Score-Baum → Report → Gates.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from .. import test_runner
from ..config import load_config
from .arch.baseline import Baseline, BaselineError
from .arch.evaluator import adr_titles, evaluate_architecture
from .arch.rules import ArchConfigError, load_architecture
from .config import QualityConfigError, load_quality_config
from .diff import changed_files, current_sha, diff_text
from .files import collect_files
from .gates import evaluate_gates
from .judge import judge_node
from .metrics import code_quality_node
from .parsers import DepsGraph, TestSuiteResult
from .probe import ProbeOutcome, ProbeRun
from .report import build_report
from .requirements import evaluate_requirements
from .score import MetricLeaf, ScoreNode
from .settings import QualitySettings, settings_problems

RUNS_DIR = Path(".sdd") / "quality" / "runs"


@dataclass
class MeasureResult:
    report: dict
    gates: list[dict]
    report_path: str | None = None

    @property
    def gates_passed(self) -> bool:
        return all(g["passed"] for g in self.gates)

    @property
    def exit_code(self) -> int:
        return 0 if self.gates_passed else 1


class _DiffAwareProbeRun(ProbeRun):
    def __init__(self, root: Path, paths: list[str], changed: list[str] | None) -> None:
        super().__init__(root, paths)
        self.changed = changed

    def paths_for(self, probe):
        if self.changed is not None and probe.diff_scoped:
            return [p for p in self.paths if p in set(self.changed)]
        return self.paths


def _test_cases(root: Path, spec_id: str | None, qcfg, probe, run: ProbeRun, reuse: bool):
    """(ProbeOutcome, Testfälle oder None, Pfad des Test-Run-Reports).

    Mit Spec laufen die Tests über den Test-Runner (SPEC-0006), damit Run-Report und JUnit
    abgelegt werden. Hat die Spec keine TST-Dokumente oder fällt die Sonde aus, bleibt es
    beim direkten Sondenlauf; der Ausfallgrund steht dann im Outcome.
    """
    if spec_id is None or probe is None:
        return None, None, None
    cfg = load_config(root)
    if reuse:
        treffer = test_runner.latest_probe_run(cfg, spec_id, current_sha(root))
        if treffer is not None:
            faelle, pfad = treffer
            outcome = ProbeOutcome(probe, "ok", probe.command, 0, 0,
                                   result=TestSuiteResult(faelle))
            return outcome, faelle, pfad.relative_to(root).as_posix()
    try:
        _, outcome = test_runner.run_with_probe(cfg, spec_id, qcfg, probe)
        return outcome, outcome.result.cases, _run_path(cfg, spec_id)
    except (ValueError, RuntimeError):
        outcome = run.execute(probe)
    return outcome, outcome.result.cases if outcome.ok else None, None


def _run_path(cfg, spec_id: str) -> str | None:
    kandidaten = sorted(cfg.test_runs_dir.glob(f"{spec_id}-*.json"))
    return kandidaten[-1].relative_to(cfg.root).as_posix() if kandidaten else None


def _architecture(root: Path, raw_config: dict, deps: ProbeOutcome | None,
                  settings: QualitySettings):
    try:
        arch = load_architecture(root)
    except FileNotFoundError:
        node = ScoreNode("architecture", settings.root_weights["architecture"],
                         forced_reason="keine .sdd/architecture.yaml")
        return node, {"violations": [], "rules_na": [], "unresolved_edges": 0}, None
    except ArchConfigError as exc:
        node = ScoreNode("architecture", settings.root_weights["architecture"],
                         forced_reason=f"architecture.yaml ungültig: {exc}")
        return node, {"violations": [], "rules_na": [], "unresolved_edges": 0}, None
    try:
        baseline = Baseline.load(root)
    except BaselineError as exc:
        node = ScoreNode("architecture", settings.root_weights["architecture"],
                         forced_reason=str(exc))
        return node, {"violations": [], "rules_na": [], "unresolved_edges": 0}, None
    graph, grund = None, None
    if deps is None:
        grund = "keine Abhängigkeitssonde (role: deps)"
    elif not deps.ok:
        grund = f"Sonde {deps.probe.name}: {deps.reason}"
    elif isinstance(deps.result, DepsGraph):
        graph = deps.result
    adr_dir = str(((raw_config.get("adr") or {}).get("output_dir")) or "docs/adr")
    titel = {k: str(v.get("title", "")) for k, v in adr_titles(root, adr_dir).items()}
    result = evaluate_architecture(arch, graph, settings, adr_titles=titel, baseline=baseline,
                                   root=root, graph_reason=grund)
    return result.node, result.to_dict(), result


def _judge(root: Path, raw_config: dict, base_ref: str | None, settings: QualitySettings):
    from ..config import load_config as _load
    from ..llm.factory import get_completion_provider

    cfg = _load(root)
    block = (raw_config.get("llm") or {}).get("evaluator") or {}
    modell = str(block.get("model") or block.get("provider") or "claude-cli")
    try:
        provider = get_completion_provider(cfg, "evaluator")
    except Exception as exc:
        return ScoreNode("judge", settings.root_weights["judge"],
                         [MetricLeaf("rubric", None, None, reason=f"kein Judge-Provider: {exc}")],
                         extra={"model": modell, "rubric_version": "-"})
    return judge_node(root, diff_text(root, base_ref), provider, modell,
                      weight=settings.root_weights["judge"])


def measure(root: Path, *, spec_id: str | None = None, base_ref: str | None = None,
            reuse_test_run: bool = False, judge: bool = False,
            raw_config: dict | None = None) -> MeasureResult:
    """FileNotFoundError ohne quality.yaml; QualityConfigError bei ungültiger Konfiguration."""
    start = time.monotonic()
    qcfg = load_quality_config(root)
    raw_config = raw_config if raw_config is not None else load_config(root).raw
    settings = QualitySettings.from_raw(raw_config)
    probleme = settings_problems(settings)
    if probleme:
        raise QualityConfigError(probleme)

    files = collect_files(root, qcfg.paths, qcfg.exclude)
    changed = changed_files(root, base_ref) if base_ref else None
    run = _DiffAwareProbeRun(root, files, changed)

    test_probe = qcfg.probe_for_role("tests")
    test_outcome, cases, test_run = _test_cases(root, spec_id, qcfg, test_probe, run,
                                                reuse_test_run)
    outcomes: list[ProbeOutcome] = []
    for probe in qcfg.probes:
        if probe is test_probe and test_outcome is not None:
            outcomes.append(test_outcome)
        else:
            outcomes.append(run.execute(probe))
    if test_probe is not None and test_outcome is None:
        test_outcome = next(o for o in outcomes if o.probe is test_probe)
        cases = test_outcome.result.cases if test_outcome.ok else None

    if spec_id is None:
        req_node = ScoreNode("requirements", settings.root_weights["requirements"],
                             forced_reason="keine Spec angegeben (--spec)")
        frs, holdout = [], None
    elif test_probe is None:
        req = evaluate_requirements(root, spec_id, None, fr_marker=None, settings=settings,
                                    na_reason="keine Testsonde (role: tests)")
        req_node, frs, holdout = req.node, req.frs, req.holdout_rate
    else:
        req = evaluate_requirements(root, spec_id, cases, fr_marker=test_probe.fr_marker,
                                    settings=settings, na_reason=test_outcome.reason)
        req_node, frs, holdout = req.node, req.frs, req.holdout_rate

    deps_probe = qcfg.probe_for_role("deps")
    deps = next((o for o in outcomes if o.probe is deps_probe), None)
    arch_node, arch_dict, _ = _architecture(root, raw_config, deps, settings)
    cq_node = code_quality_node(outcomes, qcfg, root, files, changed, settings)
    kinder = [req_node, arch_node, cq_node]
    if judge:
        kinder.append(_judge(root, raw_config, base_ref, settings))
    tree = ScoreNode("total", 1.0, kinder, policy="renormalize")

    excluded = sum(getattr(o.result, "discarded", 0) for o in outcomes if o.ok)
    report = build_report(
        tree=tree, git_sha=current_sha(root), duration_ms=int((time.monotonic() - start) * 1000),
        spec_id=spec_id, base_ref=base_ref, frs=[f.to_dict() for f in frs], holdout_rate=holdout,
        test_run=test_run, architecture=arch_dict, probes=[o.to_dict() for o in outcomes],
        gates=None, excluded=excluded)
    gates = evaluate_gates(settings.gates, report)
    if settings.gates:
        report["gates"] = gates
    pfad = _persist(root, report)
    return MeasureResult(report, gates, pfad.relative_to(root).as_posix())


def _persist(root: Path, report: dict) -> Path:
    verzeichnis = root / RUNS_DIR
    verzeichnis.mkdir(parents=True, exist_ok=True)
    name = report["generated_at"].replace(":", "-") + f"-{report.get('spec', 'all')}.json"
    pfad = verzeichnis / name
    pfad.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return pfad
