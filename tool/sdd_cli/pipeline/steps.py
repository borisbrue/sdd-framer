"""Abschluss-Schritte der Pipeline (SPEC-0061 FR-08, CON-0214), Chain of Responsibility.

`sdd pipeline run --auto` führt die Kette aus `pipeline.auto_steps` aus: `holdout` liefert vor S3
Fakten für die Abnahme, `finalize` und `automerge` laufen danach. Jeder Schritt meldet `ok`,
`failed` oder `n/a` und entscheidet selbst, ob die Kette weiterläuft. Die eigentliche Arbeit machen
die bestehenden Werkzeuge; sie werden über die Funktionen `run_holdouts`, `run_finalize` und
`automerge` aufgerufen, die Tests ersetzen können.
"""
from __future__ import annotations

import shutil
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..config import SddConfig

DEFAULT_AUTO_STEPS = ("holdout", "finalize", "automerge")
BEFORE_ACCEPTANCE = ("holdout",)
LABEL_APPROVED = "sdd:approved"


class StepError(Exception):
    """Ein Schritt ist gescheitert (z. B. Finalize ohne PR)."""


@dataclass
class StepResult:
    step: str
    status: str  # ok | failed | n/a
    reason: str = ""
    data: dict = field(default_factory=dict)

    def event_detail(self) -> dict:
        return {"gate": self.step, "status": self.status,
                **({"reason": self.reason} if self.reason else {}), **self.data}


def auto_steps(raw_config: Mapping) -> list[str]:
    schritte = (raw_config.get("pipeline") or {}).get("auto_steps")
    return list(schritte) if isinstance(schritte, list) else list(DEFAULT_AUTO_STEPS)


# ── Wrapper um die bestehenden Werkzeuge ─────────────────────────────────────

def run_holdouts(config: SddConfig, spec_id: str, base_url: str) -> dict:
    """Holdout-Evaluation der Spec (unverändert, SPEC-0004); nur Ergebnis, keine Inhalte."""
    from ..evaluator import run_evaluation

    report = run_evaluation(config, base_url, spec_id=spec_id)
    szenarien = [{"id": s.hol_id, "title": s.title, "passed": s.passed} for s in report.scenarios]
    bestanden = sum(1 for s in szenarien if s["passed"])
    return {"passed": bestanden, "failed": len(szenarien) - bestanden,
            "rate": round(report.pass_rate, 4) if szenarien else None, "scenarios": szenarien}


def run_finalize(config: SddConfig, spec_id: str) -> str:
    """PR über `SpecFinalizer`; ohne Git-Repository nur Status `implemented` (wie bisher)."""
    from .context import ProjectContext

    ctx = ProjectContext(config.root, spec_id)
    if not ctx.is_git_repo():
        from ..frontmatter import patch_status

        patch_status(ctx.spec_path, "implemented")
        return ""
    from ..finalize import SpecFinalizer

    report = SpecFinalizer(config).run(spec_id, skip_container=True)
    if report.error:
        raise StepError(report.error)
    return report.pr_url or (str(report.pr_path) if report.pr_path else "")


def _gh(config: SddConfig, *args: str) -> bool:
    if not shutil.which("gh"):
        return False
    return subprocess.run(["gh", *args], cwd=config.root, capture_output=True,
                          text=True).returncode == 0


def automerge(config: SddConfig, spec_id: str, pr_url: str) -> tuple[str, str]:
    """Labelt bzw. merged den PR nach Autonomie-Level (Logik aus SPEC-0004/SPEC-0005).

    Gibt (Ergebnis, Grund) zurück; Ergebnis ist `merged`, `labeled` oder `open`.
    """
    from ..autonomy import auto_merge_allowed, compute_level_stats, record_pr_result
    from ..frontmatter import parse_safe
    from .context import ProjectContext

    orch = config.raw.get("orchestrator") or {}
    if not orch.get("auto_merge", False):
        return "open", "orchestrator.auto_merge ist aus"
    doc = parse_safe(ProjectContext(config.root, spec_id).spec_path)
    projekt = str((doc.frontmatter if doc else {}).get("project") or "")
    level = 1.0
    if projekt:
        from ..projects import load_project

        gefunden = load_project(config, projekt)
        level = gefunden.autonomy_level if gefunden else 1.0
        record_pr_result(config, projekt, pr_url.rstrip("/").split("/")[-1], passed=True,
                         pass_rate=1.0)
    stats = compute_level_stats(config, projekt, level)
    erlaubt, grund = auto_merge_allowed(config, projekt, level, stats.total_prs, 1.0)
    if not erlaubt:
        return "open", grund or f"Autonomie-Level {level} erlaubt keinen Merge"
    _gh(config, "pr", "edit", pr_url, "--add-label", LABEL_APPROVED)
    if orch.get("auto_merge_strategy", "label") == "direct":
        if _gh(config, "pr", "merge", pr_url, "--squash"):
            return "merged", grund or "Autonomie-Level erlaubt Merge"
        return "labeled", "Merge über gh fehlgeschlagen oder gh fehlt"
    return "labeled", grund or "Strategie label"


# ── Kette ─────────────────────────────────────────────────────────────────────

def holdout_step(config: SddConfig, spec_id: str, base_url: str | None) -> StepResult:
    if not base_url:
        return StepResult("holdout", "n/a",
                          "keine Base-URL (evaluator.base_url oder --base-url)")
    ergebnis = run_holdouts(config, spec_id, base_url)
    if not ergebnis.get("scenarios"):
        return StepResult("holdout", "n/a", "keine Holdout-Szenarien für die Spec",
                          {"result": ergebnis})
    status = "ok" if not ergebnis.get("failed") else "failed"
    return StepResult("holdout", status, "", {"result": {k: ergebnis[k] for k in
                                                         ("passed", "failed", "rate", "scenarios")}})


def after_acceptance(config: SddConfig, spec_id: str, steps: list[str]) -> list[StepResult]:
    """`finalize` und `automerge` in dieser Reihenfolge; ein Fehler bricht die Kette ab."""
    ergebnisse: list[StepResult] = []
    pr_url = ""
    if "finalize" in steps:
        try:
            pr_url = run_finalize(config, spec_id)
        except StepError as exc:
            ergebnisse.append(StepResult("finalize", "failed", str(exc)))
            return ergebnisse
        ergebnisse.append(StepResult("finalize", "ok", "", {"pr": pr_url} if pr_url else {}))
    if "automerge" in steps:
        if not pr_url:
            ergebnisse.append(StepResult("automerge", "n/a", "kein PR (kein Git-Repository?)"))
        else:
            ergebnis, grund = automerge(config, spec_id, pr_url)
            ergebnisse.append(StepResult("automerge", "ok", grund, {"result": ergebnis}))
    return ergebnisse


def holdout_facts(result: StepResult) -> dict[str, Any]:
    """Fakt `holdout` der S3-Anfrage (CON-0214 INV-02): nur Zahlen, Status und Grund."""
    if result.status == "n/a" and "result" not in result.data:
        return {"status": "n/a", "reason": result.reason}
    daten = dict(result.data.get("result") or {})
    return {"status": result.status, **daten, **({"reason": result.reason} if result.reason
                                                    else {})}
