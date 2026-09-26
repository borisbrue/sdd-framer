"""Quality Maintenance Agents – wöchentlicher Sweep für Drift-Erkennung.

Prüft (SPEC-0004 §3.8):
- Veraltete Specs (updated älter als stale_after_weeks)
- Specs ohne Contracts (Drift)
- Contracts ohne Tests (Drift)
- Gibt einen Report zurück und kann optional sdd pipeline run --auto für jede
  veraltete Spec anstoßen.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .config import SddConfig
from .frontmatter import parse_safe


@dataclass
class MaintenanceIssue:
    severity: str         # "stale" | "missing_contract" | "missing_test" | "drift"
    spec_id: str
    spec_file: Path
    message: str
    action: str           # empfohlene Aktion

    def format(self, root: Path) -> str:
        try:
            rel = self.spec_file.relative_to(root)
        except ValueError:
            rel = self.spec_file
        icons = {"stale": "⏰", "missing_contract": "📋", "missing_test": "🧪", "drift": "⚠"}
        icon = icons.get(self.severity, "ℹ")
        return f"  {icon} [{self.severity}] {rel}: {self.message}"

    def to_dict(self, root: Path) -> dict:
        try:
            rel = str(self.spec_file.relative_to(root))
        except ValueError:
            rel = str(self.spec_file)
        return {
            "severity": self.severity,
            "spec_id": self.spec_id,
            "file": rel,
            "message": self.message,
            "action": self.action,
        }


@dataclass
class MaintenanceReport:
    stale_after_weeks: int
    issues: list[MaintenanceIssue] = field(default_factory=list)

    @property
    def stale(self) -> list[MaintenanceIssue]:
        return [i for i in self.issues if i.severity == "stale"]

    @property
    def drift(self) -> list[MaintenanceIssue]:
        return [i for i in self.issues if i.severity != "stale"]

    def to_dict(self, root: Path) -> dict:
        return {
            "stale_after_weeks": self.stale_after_weeks,
            "total_issues": len(self.issues),
            "stale_specs": len(self.stale),
            "drift_issues": len(self.drift),
            "issues": [i.to_dict(root) for i in self.issues],
        }


def _parse_date(raw: Any) -> date | None:
    if isinstance(raw, date):
        return raw
    if isinstance(raw, str):
        try:
            return date.fromisoformat(raw)
        except ValueError:
            return None
    return None


def run_maintenance_sweep(config: SddConfig) -> MaintenanceReport:
    """Durchsucht alle aktiven Specs nach Drift und veralteten Einträgen."""
    stale_weeks = (
        config.raw.get("maintenance", {}).get("stale_after_weeks", 4)
    )
    report = MaintenanceReport(stale_after_weeks=stale_weeks)
    cutoff = date.today() - timedelta(weeks=stale_weeks)

    # Index aufbauen
    contract_docs = list(config.contracts_dir.rglob("*.md")) if config.contracts_dir.exists() else []
    test_docs = list(config.tests_dir.rglob("*.md")) if config.tests_dir.exists() else []

    contracts_by_spec: dict[str, list[str]] = {}
    for md in contract_docs:
        doc = parse_safe(md)
        if not doc:
            continue
        ref_spec = doc.frontmatter.get("spec")
        cid = doc.frontmatter.get("id")
        if ref_spec and cid:
            contracts_by_spec.setdefault(ref_spec, []).append(cid)

    tests_by_contract: set[str] = set()
    for md in test_docs:
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("contract"):
            tests_by_contract.add(doc.frontmatter["contract"])

    # Spec-Sweep
    if not config.specs_dir.exists():
        return report

    for md in sorted(config.specs_dir.rglob("*.md")):
        doc = parse_safe(md)
        if not doc:
            continue
        fm = doc.frontmatter
        sid = fm.get("id", "")
        if not sid:
            continue

        status = fm.get("status", "draft")
        if status in ("deprecated", "archived"):
            continue

        # Veraltete Specs
        updated = _parse_date(fm.get("updated"))
        if updated and updated < cutoff:
            days_old = (date.today() - updated).days
            report.issues.append(MaintenanceIssue(
                severity="stale",
                spec_id=sid,
                spec_file=md,
                message=(
                    f"Letzte Aktualisierung vor {days_old} Tagen "
                    f"(> {stale_weeks} Wochen)"
                ),
                action=f"sdd pipeline run {sid} --auto",
            ))

        # Fehlende Contracts (Drift)
        spec_contracts = fm.get("contracts") or []
        if not spec_contracts:
            report.issues.append(MaintenanceIssue(
                severity="missing_contract",
                spec_id=sid,
                spec_file=md,
                message="Spec hat keine verknüpften Contracts.",
                action=(
                    f"sdd new contract --spec {sid} --format markdown "
                    f"--title \"Contract für {sid}\""
                ),
            ))

        # Contracts ohne Tests (Drift)
        for cid in spec_contracts:
            if cid not in tests_by_contract:
                report.issues.append(MaintenanceIssue(
                    severity="missing_test",
                    spec_id=sid,
                    spec_file=md,
                    message=f"Contract {cid} hat keinen Test.",
                    action=(
                        f"sdd new test --spec {sid} --contract {cid} "
                        f"--level contract"
                    ),
                ))

    return report
