"""Pattern-Usage-Aggregation (SPEC-0049).

Strategy: austauschbare PatternSource-Quellen (Katalog, Code-Scan).
Facade: PatternUsageService kapselt Quellen + Merge hinter usage().
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# Pattern-Name vor " Pattern"; Folgewörter nur Connector (of/the/…) oder großgeschrieben,
# damit "Chain of Responsibility Pattern" greift, Prosa wie "this uses the X Pattern" aber nicht.
_ANNOTATION = re.compile(
    r"([A-Z][A-Za-z]*(?:\s+(?:of|the|and|to|for|[A-Z][A-Za-z]*))*)\s+Pattern\b"
)
_SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js"}
_DEFAULT_SCAN_ROOTS = ("tool/sdd_cli", "web")


def _normalize(name: str) -> str:
    return name.replace(" ", "").lower()


@dataclass
class CodeLocation:
    file: str
    line: int
    annotation: str

    def to_dict(self) -> dict:
        return {"file": self.file, "line": self.line, "annotation": self.annotation}


@dataclass
class SpecRef:
    spec_id: str
    reason: str

    def to_dict(self) -> dict:
        return {"spec_id": self.spec_id, "reason": self.reason}


@dataclass
class PatternUsage:
    pattern_name: str
    specs: list[SpecRef]
    refactoring_guru_url: str | None = None
    code_locations: list[CodeLocation] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "pattern_name": self.pattern_name,
            "specs": [s.to_dict() for s in self.specs],
            "refactoring_guru_url": self.refactoring_guru_url,
            "code_locations": [c.to_dict() for c in self.code_locations],
        }


class CatalogPatternSource:
    """Liest akzeptierte Patterns aus _catalog.json, gruppiert nach Name (FR-02)."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def grouped(self) -> dict[str, dict]:
        cat = self._root / ".sdd" / "patterns" / "_catalog.json"
        if not cat.exists():
            return {}
        try:
            data = json.loads(cat.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        result: dict[str, dict] = {}
        for e in data.get("accepted_patterns", []):
            name = e.get("pattern_name")
            if not name:
                continue
            entry = result.setdefault(name, {"specs": [], "url": None})
            entry["specs"].append(SpecRef(e.get("spec_id", ""), e.get("acceptance_reason", "")))
            if not entry["url"] and e.get("refactoring_guru_url"):
                entry["url"] = e["refactoring_guru_url"]
        return result


class CodeAnnotationScanner:
    """Findet `<PatternName> Pattern`-Annotationen in den Source-Roots (FR-03/FR-04)."""

    def __init__(self, roots: list[Path]) -> None:
        self._roots = [Path(r) for r in roots]

    def scan(self) -> dict[str, list[CodeLocation]]:
        found: dict[str, list[CodeLocation]] = {}
        for root in self._roots:
            if not root.exists():
                continue
            for f in sorted(root.rglob("*")):
                if not f.is_file() or f.suffix not in _SOURCE_SUFFIXES:
                    continue
                try:
                    lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
                except OSError:
                    continue
                for i, line in enumerate(lines, 1):
                    m = _ANNOTATION.search(line)
                    if not m:
                        continue
                    found.setdefault(_normalize(m.group(1)), []).append(
                        CodeLocation(file=str(f), line=i, annotation=line.strip())
                    )
        return found


class PatternUsageService:
    """Facade: aggregiert Katalog-Quelle + Code-Scan zu einer PatternUsage-Liste (FR-05)."""

    def __init__(self, root: Path, scan_roots: list[Path] | None = None) -> None:
        self._root = Path(root)
        if scan_roots is not None:
            self._scan_roots = [Path(r) for r in scan_roots]
        else:
            self._scan_roots = [self._root / r for r in _DEFAULT_SCAN_ROOTS]

    def usage(self) -> list[PatternUsage]:
        grouped = CatalogPatternSource(self._root).grouped()
        scanned = CodeAnnotationScanner(self._scan_roots).scan()
        result: list[PatternUsage] = []
        for name, entry in grouped.items():
            result.append(PatternUsage(
                pattern_name=name,
                specs=entry["specs"],
                refactoring_guru_url=entry["url"],
                code_locations=scanned.get(_normalize(name), []),
            ))
        return result
