"""Eval-Report, Aggregation und Holdout-Sicht (SPEC-0055 FR-04 bis FR-06, CON-0218).

Proxy: `ReportProxy` ist die einzige Stelle, an der Holdout-Fälle nach außen gelangen. Ohne
`include_holdout` gibt sie nur Anzahl und Aggregate heraus, ohne IDs und Details (CON-0219 INV-04).
"""
from __future__ import annotations

import hashlib
import json
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ... import __version__
from ..roles import RoleDefinition
from ..schemas import errors as schema_errors
from .cases import MIN_HOLDOUT, RoleHome
from .runner import CaseRuns, EvalSetup

REPORT_DIR = Path(".sdd") / "role-evals"


def prompt_hash(role_def: RoleDefinition) -> str:
    return "sha256:" + hashlib.sha256(role_def.prompt.encode("utf-8")).hexdigest()


def case_result(cr: CaseRuns) -> dict:
    scores = [r.score for r in cr.runs]
    bestanden = [r.passed for r in cr.runs]
    return {"id": cr.case.id, "score": round(statistics.fmean(scores), 4) if scores else 0.0,
            "std": round(statistics.pstdev(scores), 4) if len(scores) > 1 else 0.0,
            "passed": sum(bestanden) * 2 > len(bestanden),
            "pass_at_1": bool(bestanden and bestanden[0]),
            "pass_all": bool(bestanden) and all(bestanden),
            "runs": [r.to_dict() for r in cr.runs]}


def aggregate(results: list[dict]) -> dict:
    if not results:
        return {"cases": 0, "mean": None, "std": None, "pass_at_1": None, "pass_all": None}
    scores = [r["score"] for r in results]
    n = len(results)
    return {"cases": n, "mean": round(statistics.fmean(scores), 4),
            "std": round(statistics.pstdev(scores), 4) if n > 1 else 0.0,
            "pass_at_1": round(sum(r["pass_at_1"] for r in results) / n, 4),
            "pass_all": round(sum(r["pass_all"] for r in results) / n, 4)}


@dataclass
class ReportProxy:
    """Hält alle Ergebnisse und gibt Holdout-Fälle nur maskiert heraus (Proxy)."""

    full: dict
    holdout_results: list[dict]
    include_holdout: bool

    def to_dict(self) -> dict:
        daten = dict(self.full)
        daten["include_holdout"] = self.include_holdout
        daten["holdout"] = self.holdout_results if self.include_holdout else aggregate(
            self.holdout_results)
        return daten


def build_report(st: EvalSetup, results: list[CaseRuns], *, runs: int,
                 include_holdout: bool, role_file: Path | None) -> ReportProxy:
    sichtbar = [case_result(r) for r in results if not r.case.holdout]
    holdout = [case_result(r) for r in results if r.case.holdout]
    warnungen = list(st.warnings)
    if len(holdout) < MIN_HOLDOUT:
        warnungen.append(f"nur {len(holdout)} Holdout-Fälle (mindestens {MIN_HOLDOUT}): die "
                         f"Ratchet-Regel ist eingeschränkt aussagekräftig.")
    judge = None
    if st.judge_def and st.judge_binding:
        judge = {"provider": st.judge_binding.provider, "model": st.judge_binding.model,
                 "rubric_version": st.judge_def.version}
    full = {"kind": "role-eval-report", "role": st.role_def.role,
            "role_version": st.role_def.version, "prompt_hash": prompt_hash(st.role_def),
            "output_schema": st.role_def.output_schema,
            "profile": {"name": st.profile_name, "provider": st.binding.provider,
                        "model": st.binding.model},
            "judge": judge, "runs": runs, "sdd_version": __version__,
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "visible": sichtbar, "total": aggregate(sichtbar + holdout),
            "warnings": warnungen}
    if role_file is not None:
        full["role_file"] = str(role_file)
    return ReportProxy(full, holdout, include_holdout)


def report_errors(report: Any) -> list[str]:
    return schema_errors("role-eval-report", report)


def persist(root: Path, home: RoleHome, proxy: ReportProxy) -> Path:
    """Ohne Holdout-Details nach `.sdd/role-evals/`, sonst unter `.sdd/holdout/…/reports/`
    (CON-0218 INV-03/06)."""
    daten = proxy.to_dict()
    stempel = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    name = f"{stempel}-{daten['role']}-{daten['profile']['name']}.json"
    ziel = (home.holdout_reports if proxy.include_holdout else root / REPORT_DIR) / name
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(json.dumps(daten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ziel


def estimate(root: Path, role: str, calls: int) -> int | None:
    """Geschätzte Tokens aus dem letzten Report der Rolle (für `--dry-run`)."""
    reports = sorted((root / REPORT_DIR).glob(f"*-{role}-*.json"))
    if not reports:
        return None
    daten = json.loads(reports[-1].read_text(encoding="utf-8"))
    werte = [(r["tokens"].get("input_tokens") or 0) + (r["tokens"].get("output_tokens") or 0)
             for c in daten.get("visible", []) for r in c.get("runs", [])]
    return int(statistics.fmean(werte) * calls) if werte else None
