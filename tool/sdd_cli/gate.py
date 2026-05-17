"""Execution Gate – Phase State Machine (CON-0025, SPEC-0014)."""
from __future__ import annotations

import datetime
import json
from dataclasses import dataclass, field
from pathlib import Path

PHASE_ORDER = [
    "spec-draft",
    "spec-review",
    "contracts-proposed",
    "contracts-draft",
    "contracts-review",
    "tests-generated",
    "regression-ok",
    "spec-approved",
    "execute-unlocked",
]

_PHASE_PREDECESSOR: dict[str, str | None] = {
    phase: (PHASE_ORDER[i - 1] if i > 0 else None)
    for i, phase in enumerate(PHASE_ORDER)
}


@dataclass
class GateCheckResult:
    blocked: bool
    exit_code: int
    message: str


@dataclass
class PhaseAllowedResult:
    allowed: bool
    reason: str


class ExecutionGate:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _gate_json_path(self, spec_id: str) -> Path:
        return self.repo_root / ".sdd" / "pipeline" / f"{spec_id}-gate.json"

    def _load(self, spec_id: str) -> dict:
        p = self._gate_json_path(spec_id)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        return {
            "spec_id": spec_id,
            "pipeline_phase": None,
            "phase_history": [],
            "blocking_issues": [],
            "conflict_report_ref": None,
            "override": None,
        }

    def _save(self, spec_id: str, data: dict) -> None:
        p = self._gate_json_path(spec_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _now(self) -> str:
        return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # ── Public API ────────────────────────────────────────────────────────────

    def check(self, spec_id: str) -> GateCheckResult:
        """Returns blocked=False only when pipeline_phase == 'execute-unlocked'."""
        data = self._load(spec_id)
        phase = data.get("pipeline_phase")
        if phase == "execute-unlocked":
            return GateCheckResult(blocked=False, exit_code=0, message="Execute freigegeben.")

        history = {e["phase"]: e for e in data.get("phase_history", [])}
        lines = ["Execution Gate nicht bestanden.\n", "Phasen-Status:"]
        for p in PHASE_ORDER:
            entry = history.get(p)
            if entry:
                result = entry.get("result", "?")
                mark = "✓" if result == "ok" else "✗"
                lines.append(f"  {mark} {p} ({result})")
            elif p == phase:
                lines.append(f"  ✗ {p} BLOCKIERT")
            else:
                lines.append(f"  – {p} (ausstehend)")
        issues = data.get("blocking_issues", [])
        if issues:
            lines.append("\nBlockierende Probleme:")
            for issue in issues:
                lines.append(f"  → {issue}")
        return GateCheckResult(blocked=True, exit_code=2, message="\n".join(lines))

    def force_execute(self, spec_id: str, override_reason: str | None) -> GateCheckResult:
        """Execute with --force. Requires override_reason (exit 1 if missing)."""
        if not override_reason:
            return GateCheckResult(
                blocked=True,
                exit_code=1,
                message="--override-reason ist erforderlich bei --force",
            )
        data = self._load(spec_id)
        data["override"] = {
            "triggered_at": self._now(),
            "reason": override_reason,
            "blocked_phase": data.get("pipeline_phase") or "unknown",
        }
        self._save(spec_id, data)
        return GateCheckResult(blocked=False, exit_code=0, message="Override akzeptiert.")

    def can_start_phase(self, spec_id: str, phase: str) -> PhaseAllowedResult:
        """Check whether predecessor phase is complete."""
        # For tests-generated: open conflicts block regardless of predecessor state
        if phase == "tests-generated":
            open_ids = self._open_conflict_ids(spec_id)
            if open_ids:
                return PhaseAllowedResult(
                    allowed=False,
                    reason=f"Offene Konflikte: {', '.join(open_ids)}",
                )
        predecessor = _PHASE_PREDECESSOR.get(phase)
        if predecessor is None:
            return PhaseAllowedResult(allowed=True, reason="")
        data = self._load(spec_id)
        history = {e["phase"]: e for e in data.get("phase_history", [])}
        pre_entry = history.get(predecessor)
        if not (pre_entry and pre_entry.get("result") == "ok"):
            return PhaseAllowedResult(
                allowed=False,
                reason=f"Phase {predecessor!r} noch nicht abgeschlossen",
            )
        return PhaseAllowedResult(allowed=True, reason="")

    def _open_conflict_ids(self, spec_id: str) -> list[str]:
        """Return IDs of open conflicts from the conflict report, if any."""
        import json as _json
        p = self.repo_root / ".sdd" / "conflict-reports" / f"{spec_id}-conflicts.json"
        if not p.exists():
            return []
        try:
            data = _json.loads(p.read_text(encoding="utf-8"))
            return [
                c["id"] for c in data.get("conflicts", [])
                if c.get("status") == "open"
            ]
        except Exception:
            return []

    def mark_phase_started(self, spec_id: str, phase: str) -> None:
        """Remove phase and all subsequent phases from history to allow re-run."""
        data = self._load(spec_id)
        idx = PHASE_ORDER.index(phase) if phase in PHASE_ORDER else len(PHASE_ORDER)
        phases_to_keep = set(PHASE_ORDER[:idx])
        data["phase_history"] = [
            e for e in data.get("phase_history", [])
            if e.get("phase") in phases_to_keep
        ]
        # pipeline_phase = last ok phase before this one
        completed = [
            e["phase"] for e in data["phase_history"] if e.get("result") == "ok"
        ]
        data["pipeline_phase"] = completed[-1] if completed else None
        self._save(spec_id, data)

    def mark_phase_complete(
        self, spec_id: str, phase: str, result: str = "ok", **extra: object
    ) -> None:
        """Persist a completed phase entry immediately (crash-safe)."""
        data = self._load(spec_id)
        # Remove any existing entry for this phase
        data["phase_history"] = [
            e for e in data.get("phase_history", []) if e.get("phase") != phase
        ]
        entry: dict = {"phase": phase, "completed_at": self._now(), "result": result}
        entry.update(extra)
        data["phase_history"].append(entry)
        if result == "ok":
            data["pipeline_phase"] = phase
        self._save(spec_id, data)
