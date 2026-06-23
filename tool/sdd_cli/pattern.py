"""Pattern-Vorschlag und Pattern-Register – SPEC-0015.

Architekturmuster:
  - Registry Pattern: .sdd/patterns/ speichert Pattern-Entscheidungen pro SPEC
  - LLM-basierte Vorschläge mit Refactoring Guru als Referenzrahmen
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import SddConfig

PATTERNS_DIR = ".sdd/patterns"
CATALOG_FILE = "_catalog.json"

REFACTORING_GURU_BASE = "https://refactoring.guru/design-patterns/"

_VALID_CATEGORIES = frozenset({"Creational", "Structural", "Behavioral"})
_VALID_EFFORTS = frozenset({"low", "medium", "high"})
_VALID_PRIORITIES = frozenset({"recommended", "optional", "consider"})
_VALID_STATUSES = frozenset({"accepted", "rejected", "under-review"})


# ─────────────────────────────────────────────────────────────────────────────
# Data Structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PatternSuggestion:
    pattern_name: str
    category: str          # Creational|Structural|Behavioral
    refactoring_guru_url: str
    applies_to: str
    rationale: str
    alternative: str
    effort: str            # low|medium|high
    priority: str          # recommended|optional|consider

    def to_dict(self) -> dict:
        return {
            "pattern_name": self.pattern_name,
            "category": self.category,
            "refactoring_guru_url": self.refactoring_guru_url,
            "applies_to": self.applies_to,
            "rationale": self.rationale,
            "alternative": self.alternative,
            "effort": self.effort,
            "priority": self.priority,
        }


@dataclass
class PatternSuggestionResult:
    artifact_id: str
    artifact_type: str   # spec|contract
    generated_at: str
    pattern_suggestions: list[PatternSuggestion] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "generated_at": self.generated_at,
            "pattern_suggestions": [p.to_dict() for p in self.pattern_suggestions],
        }


# ─────────────────────────────────────────────────────────────────────────────
# LLM Pattern Suggester
# ─────────────────────────────────────────────────────────────────────────────

class PatternSuggester:
    """Schlägt passende Design Patterns via LLM vor (Refactoring Guru Katalog)."""

    def __init__(
        self,
        provider: object,
        max_suggestions: int = 4,
        registry: "PatternRegistry | None" = None,
    ) -> None:
        self._provider = provider
        self._max = max(1, min(4, max_suggestions))
        self._registry = registry

    def suggest(
        self,
        artifact_text: str,
        artifact_id: str,
        artifact_type: str = "spec",
    ) -> PatternSuggestionResult:
        catalog_context = ""
        if self._registry is not None:
            catalog_context = self._registry.catalog_summary(exclude_spec_id=artifact_id)
        prompt = _build_pattern_prompt(
            artifact_text, artifact_id, artifact_type, self._max, catalog_context=catalog_context
        )
        now = _utc_now()
        try:
            result = self._provider.complete(prompt, max_tokens=2048)
            suggestions = _parse_pattern_response(result.text, artifact_id)
        except Exception:
            suggestions = []

        return PatternSuggestionResult(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            generated_at=now,
            pattern_suggestions=suggestions[: self._max],
        )


def create_suggester(config: "SddConfig") -> PatternSuggester | None:
    """Gibt PatternSuggester zurück, oder None wenn deaktiviert."""
    if not config.pattern_suggestions_enabled():
        return None
    from .llm.factory import get_completion_provider
    provider = get_completion_provider(config, "completion")
    registry = PatternRegistry(config.root)
    return PatternSuggester(provider, max_suggestions=config.pattern_suggestions_max(), registry=registry)


# ─────────────────────────────────────────────────────────────────────────────
# Registry Pattern: PatternRegistry
# ─────────────────────────────────────────────────────────────────────────────

class PatternRegistry:
    """Persistiert Pattern-Entscheidungen unter .sdd/patterns/."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root
        self._dir = project_root / PATTERNS_DIR

    def _spec_file(self, spec_id: str) -> Path:
        return self._dir / f"{spec_id}-patterns.json"

    def load(self, spec_id: str) -> dict:
        path = self._spec_file(spec_id)
        if not path.exists():
            return {"spec_id": spec_id, "generated_at": _utc_now(), "patterns": []}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"spec_id": spec_id, "generated_at": _utc_now(), "patterns": []}

    def _save(self, spec_id: str, data: dict) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._spec_file(spec_id)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def accept(
        self,
        spec_id: str,
        pattern_name: str,
        reason: str,
        url: str | None = None,
    ) -> None:
        data = self.load(spec_id)
        now = _utc_now()
        patterns: list[dict] = data.get("patterns", [])
        entry = _find_pattern(patterns, pattern_name)
        if entry is None:
            entry = {"pattern_name": pattern_name}
            patterns.append(entry)
        entry.update({
            "status": "accepted",
            "decided_at": now,
            "acceptance_reason": reason,
            "rejection_reason": None,
            "refactoring_guru_url": url,
        })
        data["patterns"] = patterns
        self._save(spec_id, data)
        self._update_catalog(spec_id, pattern_name, now, reason, url)

    def reject(
        self,
        spec_id: str,
        pattern_name: str,
        reason: str,
        url: str | None = None,
    ) -> None:
        data = self.load(spec_id)
        now = _utc_now()
        patterns: list[dict] = data.get("patterns", [])
        entry = _find_pattern(patterns, pattern_name)
        if entry is None:
            entry = {"pattern_name": pattern_name}
            patterns.append(entry)
        entry.update({
            "status": "rejected",
            "decided_at": now,
            "acceptance_reason": None,
            "rejection_reason": reason,
            "refactoring_guru_url": url,
        })
        data["patterns"] = patterns
        self._save(spec_id, data)
        self._remove_from_catalog(spec_id, pattern_name)

    def list_patterns(self, spec_id: str | None = None) -> list[dict]:
        """Gibt alle Pattern-Einträge zurück, optional gefiltert nach spec_id."""
        if spec_id:
            data = self.load(spec_id)
            return [
                {"spec_id": spec_id, **p}
                for p in data.get("patterns", [])
            ]

        results: list[dict] = []
        if not self._dir.exists():
            return results
        for f in sorted(self._dir.glob("SPEC-*-patterns.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                sid = data.get("spec_id", "")
                for p in data.get("patterns", []):
                    results.append({"spec_id": sid, **p})
            except (json.JSONDecodeError, OSError):
                continue
        return results

    def _update_catalog(
        self,
        spec_id: str,
        pattern_name: str,
        accepted_at: str,
        reason: str | None,
        url: str | None,
    ) -> None:
        catalog = self._load_catalog()
        now = _utc_now()
        accepted = catalog.get("accepted_patterns", [])
        existing = next(
            (e for e in accepted if e["spec_id"] == spec_id and e["pattern_name"] == pattern_name),
            None,
        )
        if existing is None:
            accepted.append({
                "pattern_name": pattern_name,
                "spec_id": spec_id,
                "accepted_at": accepted_at,
                "acceptance_reason": reason,
                "refactoring_guru_url": url,
            })
        else:
            existing.update({
                "accepted_at": accepted_at,
                "acceptance_reason": reason,
                "refactoring_guru_url": url,
            })
        catalog["last_updated"] = now
        catalog["accepted_patterns"] = accepted
        self._save_catalog(catalog)

    def _remove_from_catalog(self, spec_id: str, pattern_name: str) -> None:
        catalog = self._load_catalog()
        accepted = catalog.get("accepted_patterns", [])
        catalog["accepted_patterns"] = [
            e for e in accepted
            if not (e["spec_id"] == spec_id and e["pattern_name"] == pattern_name)
        ]
        catalog["last_updated"] = _utc_now()
        self._save_catalog(catalog)

    def _load_catalog(self) -> dict:
        path = self._dir / CATALOG_FILE
        if not path.exists():
            return {"last_updated": _utc_now(), "accepted_patterns": []}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"last_updated": _utc_now(), "accepted_patterns": []}

    def _save_catalog(self, data: dict) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._dir / CATALOG_FILE
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def catalog_summary(
        self,
        max_entries: int = 10,
        exclude_spec_id: str | None = None,
    ) -> str:
        """Kompakte, LLM-taugliche Textzusammenfassung des globalen Katalogs."""
        catalog = self._load_catalog()
        entries = catalog.get("accepted_patterns", [])
        if exclude_spec_id is not None:
            entries = [e for e in entries if e.get("spec_id") != exclude_spec_id]
        # Sekundärschlüssel (Listenposition) bricht Ties bei gleicher Sekunden-Genauigkeit
        # von accepted_at zugunsten der zuletzt eingefügten (= neuesten) Einträge auf.
        indexed = sorted(
            enumerate(entries),
            key=lambda pair: (pair[1].get("accepted_at", ""), pair[0]),
            reverse=True,
        )
        entries = [e for _, e in indexed][:max_entries]
        lines = [
            f"- {e.get('pattern_name')} ({e.get('spec_id')}): {_truncate(e.get('acceptance_reason') or '')}"
            for e in entries
        ]
        return "\n".join(lines)


def _truncate(reason: str, limit: int = 120) -> str:
    if len(reason) <= limit:
        return reason
    return reason[:limit] + "…"


# ─────────────────────────────────────────────────────────────────────────────
# Prompt Construction
# ─────────────────────────────────────────────────────────────────────────────

def _build_pattern_prompt(
    text: str,
    artifact_id: str,
    artifact_type: str,
    max_suggestions: int,
    catalog_context: str = "",
) -> str:
    catalog_block = ""
    if catalog_context:
        catalog_block = (
            "BEREITS AKZEPTIERTE PATTERNS IM PROJEKT:\n"
            f"{catalog_context}\n"
            "Referenziere/verwende bei thematischer Nähe ein oben gelistetes Pattern "
            "statt ein neues vorzuschlagen.\n\n"
        )
    return (
        "Du bist ein Software-Architekt der GoF-Design-Patterns und architekturelle Patterns "
        "auf Spezifikations- und Contract-Ebene empfiehlt.\n"
        f"Analysiere das folgende Artefakt und schlage {max_suggestions} passende Patterns vor.\n"
        "Verwende den Refactoring Guru Katalog als Referenzrahmen "
        "(https://refactoring.guru/design-patterns/).\n\n"
        "Für jeden Vorschlag:\n"
        "  - Erkläre WARUM das Pattern hier passt (mindestens 1 Satz)\n"
        "  - Nenne eine abgelehnte Alternative mit Begründung\n"
        "  - Verlinke die Refactoring Guru Seite des Patterns\n\n"
        f"ARTEFAKT-TYP: {artifact_type}\n"
        f"ARTEFAKT-ID: {artifact_id}\n"
        "INHALT:\n"
        f"{text}\n\n"
        f"{catalog_block}"
        "AUSGABE-FORMAT:\n"
        "Antworte AUSSCHLIESSLICH als valides JSON (kein Markdown, kein Text davor/danach):\n"
        "{\n"
        '  "artifact_id": "' + artifact_id + '",\n'
        '  "artifact_type": "' + artifact_type + '",\n'
        '  "generated_at": "ISO 8601 UTC",\n'
        '  "pattern_suggestions": [\n'
        '    {\n'
        '      "pattern_name": "Strategy",\n'
        '      "category": "Creational|Structural|Behavioral",\n'
        '      "refactoring_guru_url": "https://refactoring.guru/design-patterns/...",\n'
        '      "applies_to": "Wo im Artefakt passt es",\n'
        '      "rationale": "Warum dieses Pattern hier sinnvoll ist (mind. 10 Zeichen)",\n'
        '      "alternative": "Welches Pattern abgelehnt wurde und warum (mind. 10 Zeichen)",\n'
        '      "effort": "low|medium|high",\n'
        '      "priority": "recommended|optional|consider"\n'
        '    }\n'
        "  ]\n"
        "}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Response Parsing
# ─────────────────────────────────────────────────────────────────────────────

def _parse_pattern_response(text: str, artifact_id: str) -> list[PatternSuggestion]:
    cleaned = _extract_json(text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return []

    suggestions: list[PatternSuggestion] = []
    seen_names: set[str] = set()

    for item in data.get("pattern_suggestions", [])[:4]:
        name = str(item.get("pattern_name", "")).strip()
        if not name or name in seen_names:
            continue
        category = str(item.get("category", "Behavioral")).strip()
        if category not in _VALID_CATEGORIES:
            category = "Behavioral"
        url = str(item.get("refactoring_guru_url", "")).strip()
        if not url.startswith("https://refactoring.guru/"):
            slug = name.lower().replace(" ", "-")
            url = f"{REFACTORING_GURU_BASE}{slug}"
        applies_to = str(item.get("applies_to", artifact_id)).strip() or artifact_id
        rationale = str(item.get("rationale", "")).strip()
        alternative = str(item.get("alternative", "")).strip()
        if len(rationale) < 10 or len(alternative) < 10:
            continue
        effort = str(item.get("effort", "medium")).lower()
        if effort not in _VALID_EFFORTS:
            effort = "medium"
        priority = str(item.get("priority", "optional")).lower()
        if priority not in _VALID_PRIORITIES:
            priority = "optional"

        suggestions.append(PatternSuggestion(
            pattern_name=name,
            category=category,
            refactoring_guru_url=url,
            applies_to=applies_to,
            rationale=rationale,
            alternative=alternative,
            effort=effort,
            priority=priority,
        ))
        seen_names.add(name)

    return suggestions


def _extract_json(text: str) -> str:
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r"(\{.*\})", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _find_pattern(patterns: list[dict], name: str) -> dict | None:
    return next((p for p in patterns if p.get("pattern_name") == name), None)
