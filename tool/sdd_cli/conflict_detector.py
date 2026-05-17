"""Contract Conflict Detection (CON-0026, SPEC-0014)."""
from __future__ import annotations

import datetime
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ConflictReport:
    spec_id: str
    generated_at: str
    new_contracts: list[str]
    conflicts: list[dict]
    impact_summary: dict

    def to_dict(self) -> dict:
        return {
            "spec_id": self.spec_id,
            "generated_at": self.generated_at,
            "new_contracts": self.new_contracts,
            "conflicts": self.conflicts,
            "impact_summary": self.impact_summary,
        }


class ContractCache:
    """File-hash–based cache for contract data."""

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    def load(self, path: Path) -> dict:
        content = path.read_text(encoding="utf-8")
        h = hashlib.sha256(content.encode()).hexdigest()
        key = str(path)
        cached = self._store.get(key)
        if cached and cached["_hash"] == h:
            return cached
        data: dict[str, Any] = {"_path": str(path), "_hash": h, "_content": content}
        # Parse YAML frontmatter
        try:
            import re
            import yaml
            m = re.match(r"^---\n(.*?)\n---\n?(.*)", content, re.DOTALL)
            if m:
                fm = yaml.safe_load(m.group(1)) or {}
                data.update(fm)
                data["_body"] = m.group(2)
        except Exception:
            pass
        self._store[key] = data
        return data


class ConflictDetector:
    """Analyses new contracts against the workspace for conflicts."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)
        self._cache = ContractCache()

    # ── Report persistence ────────────────────────────────────────────────────

    def _report_path(self, spec_id: str) -> Path:
        return self.repo_root / ".sdd" / "conflict-reports" / f"{spec_id}-conflicts.json"

    def _load_report(self, spec_id: str) -> dict:
        p = self._report_path(spec_id)
        if not p.exists():
            raise FileNotFoundError(f"Kein Konfliktbericht für {spec_id}")
        return json.loads(p.read_text(encoding="utf-8"))

    def _save_report(self, spec_id: str, data: dict) -> None:
        p = self._report_path(spec_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _now(self) -> str:
        return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # ── Workspace scanning ────────────────────────────────────────────────────

    def _load_workspace_contracts(self) -> list[dict]:
        contracts_dir = self.repo_root / ".sdd" / "contracts"
        if not contracts_dir.exists():
            return []
        result = []
        for md in sorted(contracts_dir.rglob("*.md")):
            data = self._cache.load(md)
            status = data.get("status", "")
            if status in ("active", "draft") and data.get("id"):
                result.append(data)
        return result

    def _find_contract(self, con_id: str) -> Path | None:
        contracts_dir = self.repo_root / ".sdd" / "contracts"
        if not contracts_dir.exists():
            return None
        for md in contracts_dir.rglob("*.md"):
            data = self._cache.load(md)
            if data.get("id") == con_id:
                return md
        return None

    # ── LLM analysis (injectable for testing) ────────────────────────────────

    def _llm_analyze(
        self, new_contract: dict, existing_contracts: list[dict]
    ) -> list[dict]:
        """Calls LLM to find conflicts. Returns list of conflict dicts.

        Override this method in tests via patch.object().
        """
        if not existing_contracts:
            return []
        try:
            from sdd_cli.config import load_config
            from sdd_cli.llm.factory import get_completion_provider
            cfg = load_config(self.repo_root)
            provider = get_completion_provider(cfg, "analyzer")
        except Exception:
            return []

        existing_summaries = "\n".join(
            f"- {c.get('id')}: {c.get('title', '')} (type={c.get('type', '')}, "
            f"format={c.get('format', '')}, status={c.get('status', '')})"
            for c in existing_contracts
        )
        prompt = (
            f"Analysiere den neuen Contract:\n"
            f"ID: {new_contract.get('id')}\nTitel: {new_contract.get('title')}\n"
            f"Typ: {new_contract.get('type')}, Format: {new_contract.get('format')}\n"
            f"Inhalt (Auszug):\n{new_contract.get('_body', '')[:800]}\n\n"
            f"Bestehende Contracts im Workspace:\n{existing_summaries}\n\n"
            "Identifiziere semantische Konflikte (endpoint-overlap, field-contradiction, "
            "behavior-contradiction, scope-overlap, dependency-gap). "
            "Antworte als JSON-Array: [{\"type\": \"...\", \"conflicting_contract\": \"CON-XXXX\", "
            "\"detail\": \"...\", \"severity\": \"low|medium|high\"}] "
            "oder [] wenn keine Konflikte gefunden."
        )
        try:
            result = provider.complete(prompt, max_tokens=1024)
            import re
            match = re.search(r"\[.*\]", result.text, re.DOTALL)
            if match:
                items = json.loads(match.group(0))
                return items
        except Exception:
            pass
        return []

    # ── Public API ────────────────────────────────────────────────────────────

    def analyze(self, spec_id: str, new_contracts: list[str]) -> ConflictReport:
        """Run conflict analysis for all new contracts against the workspace."""
        workspace = self._load_workspace_contracts()
        new_ids = set(new_contracts)
        existing = [c for c in workspace if c.get("id") not in new_ids]

        all_conflicts: list[dict] = []
        counter = 1

        for con_id in new_contracts:
            path = self._find_contract(con_id)
            if not path:
                continue
            con_data = self._cache.load(path)
            raw = self._llm_analyze(con_data, existing)
            for item in raw:
                cf: dict = {
                    "id": f"CF-{spec_id.replace('SPEC-', '')}-{counter:03d}",
                    "type": item.get("type", "scope-overlap"),
                    "severity": item.get("severity", "medium"),
                    "new_contract": con_id,
                    "conflicting_contract": item.get("conflicting_contract", ""),
                    "detail": item.get("detail", ""),
                    "affected_specs": item.get("affected_specs", []),
                    "required_action": item.get("required_action", ""),
                    "status": "open",
                    "resolution": None,
                }
                all_conflicts.append(cf)
                counter += 1

        summary = {
            "total_conflicts": len(all_conflicts),
            "high":   sum(1 for c in all_conflicts if c["severity"] == "high"),
            "medium": sum(1 for c in all_conflicts if c["severity"] == "medium"),
            "low":    sum(1 for c in all_conflicts if c["severity"] == "low"),
            "affected_specs_count": len(
                {s for c in all_conflicts for s in c.get("affected_specs", [])}
            ),
        }
        report = ConflictReport(
            spec_id=spec_id,
            generated_at=self._now(),
            new_contracts=list(new_contracts),
            conflicts=all_conflicts,
            impact_summary=summary,
        )
        self._save_report(spec_id, report.to_dict())
        return report

    def resolve(self, spec_id: str, cf_id: str, action: str) -> None:
        """Mark a conflict as resolved with given action."""
        data = self._load_report(spec_id)
        for c in data["conflicts"]:
            if c["id"] == cf_id:
                c["status"] = "resolved"
                c["resolution"] = {"action": action, "resolved_at": self._now()}
                break
        self._save_report(spec_id, data)

    def acknowledge(self, spec_id: str, cf_id: str, reason: str | None) -> None:
        """Acknowledge a conflict with mandatory reason."""
        if not reason:
            raise ValueError("reason ist erforderlich für acknowledge")
        data = self._load_report(spec_id)
        for c in data["conflicts"]:
            if c["id"] == cf_id:
                c["status"] = "acknowledged"
                c["resolution"] = {
                    "action": "acknowledged",
                    "reason": reason,
                    "resolved_at": self._now(),
                }
                break
        self._save_report(spec_id, data)

    def list_conflicts(
        self, spec_id: str, status_filter: str | None = None
    ) -> list[dict]:
        """Return conflicts from report, optionally filtered by status."""
        try:
            data = self._load_report(spec_id)
        except FileNotFoundError:
            return []
        conflicts = data.get("conflicts", [])
        if status_filter:
            conflicts = [c for c in conflicts if c.get("status") == status_filter]
        return conflicts
