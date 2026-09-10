"""Execution Gate – Phase State Machine (CON-0025, SPEC-0014)."""
from __future__ import annotations

import datetime
import json
from dataclasses import dataclass
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


def _phase_rank(phase: str | None) -> int:
    """Position einer Phase in PHASE_ORDER. None und Unbekanntes ergeben -1."""
    if phase is None:
        return -1
    try:
        return PHASE_ORDER.index(phase)
    except ValueError:
        return -1


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
        # Zustandsbasierte Phasen nachziehen, bevor der Vorgänger geprüft wird.
        self.evaluate_condition_phases(spec_id)
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

    # ── Zustandsbasierte Phasen (CON-0025 Phase 1 und 4) ──────────────────────
    #
    # Die meisten Gate-Phasen werden von einem Befehl abgeschlossen. Zwei nicht:
    # CON-0025 nennt als Auslöser für Phase 1 "Datei erstellt" und für Phase 4
    # "Dateien angelegt" – das sind Zustände, keine Aktionen. Sie werden deshalb
    # hier ausgewertet, statt auf einen Befehl zu warten, den es nicht gibt.

    def evaluate_condition_phases(self, spec_id: str) -> list[str]:
        """Schließt zustandsbasierte Phasen ab, deren Exit-Kriterium erfüllt ist.

        Gibt die Namen der dabei neu abgeschlossenen Phasen zurück. Idempotent:
        eine bereits abgeschlossene Phase wird nicht erneut geschrieben.
        """
        newly_completed: list[str] = []
        data = self._load(spec_id)
        done = {
            e["phase"] for e in data.get("phase_history", [])
            if e.get("result") == "ok"
        }

        if "spec-draft" not in done and self._spec_draft_satisfied(spec_id):
            self.mark_phase_complete(spec_id, "spec-draft")
            newly_completed.append("spec-draft")
            done.add("spec-draft")

        # Phase 4 setzt Phase 3 voraus – ohne Vorschlagsliste gibt es nichts zu prüfen.
        if (
            "contracts-draft" not in done
            and "contracts-proposed" in done
            and self._contracts_draft_satisfied(spec_id)
        ):
            self.mark_phase_complete(spec_id, "contracts-draft")
            newly_completed.append("contracts-draft")

        return newly_completed

    def _spec_draft_satisfied(self, spec_id: str) -> bool:
        """Phase 1 – Exit: die Spec existiert und trägt die Pflichtfelder."""
        doc = self._find_doc(self.repo_root / ".sdd" / "specs", spec_id)
        if doc is None:
            return False
        required = ("id", "title", "status", "owner", "version")
        return all(doc.frontmatter.get(f) for f in required)

    def _contracts_draft_satisfied(self, spec_id: str) -> bool:
        """Phase 4 – Exit: alle vorgeschlagenen Contracts existieren.

        "Existieren" heißt: das Contract-Dokument ist da, und sein artifact zeigt
        auf eine vorhandene Datei. Ein Contract, dessen Artefakt fehlt, ist noch
        nicht geschrieben – genau der Zustand, den Phase 4 abgrenzen soll.
        """
        proposed = self._proposed_contract_ids(spec_id)
        if not proposed:
            return False
        contracts_dir = self.repo_root / ".sdd" / "contracts"
        for cid in proposed:
            doc = self._find_doc(contracts_dir, cid)
            if doc is None:
                return False
            artifact = doc.frontmatter.get("artifact")
            if artifact and not (self.repo_root / str(artifact)).exists():
                return False
        return True

    def _proposed_contract_ids(self, spec_id: str) -> list[str]:
        """Die in Phase 3 gemeldeten Contract-IDs aus der Phasenhistorie."""
        data = self._load(spec_id)
        for entry in data.get("phase_history", []):
            if entry.get("phase") == "contracts-proposed" and entry.get("result") == "ok":
                return [str(c) for c in (entry.get("proposed") or [])]
        return []

    def _find_doc(self, base: Path, doc_id: str):
        """Sucht das Dokument mit der gegebenen ID unterhalb von base."""
        from .frontmatter import parse_safe

        if not base.exists():
            return None
        for md in base.rglob("*.md"):
            if "_archive" in md.parts:
                continue
            doc = parse_safe(md)
            if doc and doc.frontmatter.get("id") == doc_id:
                return doc
        return None

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
        if result == "ok" and _phase_rank(phase) >= _phase_rank(data.get("pipeline_phase")):
            # pipeline_phase nur vorwaerts bewegen. evaluate_condition_phases()
            # schliesst Phasen nachtraeglich ab und laeuft aus can_start_phase()
            # heraus, also aus einem Lesepfad. Ohne diesen Guard ueberschreibt ein
            # spaet erfuelltes contracts-draft ein bereits gesetztes
            # execute-unlocked und blockiert das Gate erneut.
            #
            # Die Historie bleibt davon unberuehrt: sie traegt den Abschluss
            # weiterhin, nur der gemeldete Stand faellt nicht zurueck.
            data["pipeline_phase"] = phase
        self._save(spec_id, data)
