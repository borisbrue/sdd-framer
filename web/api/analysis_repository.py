"""File-basierte Persistenz für Analyse-Ergebnisse (SPEC-0016, CON-0050)."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _safe_dir_name(doc_id: str) -> str:
    return re.sub(r'[/\\:*?"<>|]', "_", doc_id)


@dataclass
class PersistedAnalysis:
    result_id: str
    doc_id: str
    timestamp: str
    session_id: str
    dismissed_ids: list[str] = field(default_factory=list)
    questions: list[dict[str, Any]] = field(default_factory=list)
    issues: list[dict[str, Any]] = field(default_factory=list)
    suggestions: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def summary(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "timestamp": self.timestamp,
            "question_count": len(self.questions),
            "issue_count": len(self.issues),
            "dismissed_count": len(self.dismissed_ids),
        }


class AnalysisRepository:
    def __init__(self, base_dir: Path) -> None:
        self._base = base_dir

    def _doc_dir(self, doc_id: str) -> Path:
        return self._base / _safe_dir_name(doc_id)

    def save(self, analysis: PersistedAnalysis) -> Path:
        doc_dir = self._doc_dir(analysis.doc_id)
        doc_dir.mkdir(parents=True, exist_ok=True)
        path = doc_dir / f"{analysis.result_id}.json"
        path.write_text(json.dumps(analysis.to_dict(), indent=2), encoding="utf-8")
        return path

    def list(self, doc_id: str, limit: int = 50) -> list[dict[str, Any]]:
        doc_dir = self._doc_dir(doc_id)
        if not doc_dir.exists():
            return []
        files = sorted(doc_dir.glob("*.json"), reverse=True)[:limit]
        results = []
        for f in files:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                results.append({
                    "result_id":      data.get("result_id", f.stem),
                    "timestamp":      data.get("timestamp", ""),
                    "question_count": len(data.get("questions", [])),
                    "issue_count":    len(data.get("issues", [])),
                    "dismissed_count": len(data.get("dismissed_ids", [])),
                })
            except (json.JSONDecodeError, OSError):
                continue
        return results

    def get(self, doc_id: str, result_id: str) -> PersistedAnalysis | None:
        path = self._doc_dir(doc_id) / f"{result_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        return PersistedAnalysis(
            result_id=data.get("result_id", result_id),
            doc_id=data.get("doc_id", doc_id),
            timestamp=data.get("timestamp", ""),
            session_id=data.get("session_id", ""),
            dismissed_ids=data.get("dismissed_ids", []),
            questions=data.get("questions", []),
            issues=data.get("issues", []),
            suggestions=data.get("suggestions", []),
            usage=data.get("usage", {}),
        )

    def update_dismiss(self, doc_id: str, result_id: str,
                       item_id: str, dismissed: bool) -> list[str] | None:
        analysis = self.get(doc_id, result_id)
        if analysis is None:
            return None
        ids = set(analysis.dismissed_ids)
        if dismissed:
            ids.add(item_id)
        else:
            ids.discard(item_id)
        analysis.dismissed_ids = list(ids)
        self.save(analysis)
        return analysis.dismissed_ids

    @staticmethod
    def make_result_id(job_id: str) -> str:
        return f"{_now_iso()}_{job_id[:8]}"
