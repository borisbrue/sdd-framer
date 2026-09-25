"""Baseline bekannter Architekturverstöße (SPEC-0054 FR-07, CON-0198)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path

from ..schemas import validator

BASELINE_FILE = Path(".sdd") / "quality" / "arch-baseline.json"
PLACEHOLDER_REASON = "TODO"


class BaselineError(Exception):
    pass


def _schluessel(rule: str, file: str, symbol: str) -> tuple[str, str, str]:
    return rule, file, symbol


@dataclass
class Baseline:
    entries: list[dict] = field(default_factory=list)
    stale: int = 0

    @classmethod
    def load(cls, root: Path) -> Baseline:
        pfad = root / BASELINE_FILE
        if not pfad.is_file():
            return cls([])
        try:
            daten = json.loads(pfad.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise BaselineError(f"{BASELINE_FILE}: kein gültiges JSON: {exc}") from exc
        fehler = next(iter(validator("arch-baseline").iter_errors(daten)), None)
        if fehler is not None:
            raise BaselineError(f"{BASELINE_FILE}: {fehler.message}")
        return cls(list(daten["entries"]))

    def _keys(self) -> set[tuple[str, str, str]]:
        return {_schluessel(e["rule"], e["file"], e["symbol"]) for e in self.entries}

    def apply(self, violations: list) -> list:
        keys = self._keys()
        ergebnis, getroffen = [], set()
        for v in violations:
            k = _schluessel(v.rule, v.file, v.symbol)
            if k in keys:
                getroffen.add(k)
                v = replace(v, severity="warn", baselined=True)
            ergebnis.append(v)
        self.stale = len(keys - getroffen)
        return ergebnis

    def merged_with(self, violations: list) -> Baseline:
        """Vorhandene Einträge bleiben mit ihrem Grund; neue error-Verstöße kommen mit TODO dazu."""
        eintraege = [dict(e) for e in self.entries]
        keys = self._keys()
        for v in violations:
            k = _schluessel(v.rule, v.file, v.symbol)
            if v.severity == "error" and not v.baselined and k not in keys:
                keys.add(k)
                eintraege.append({"rule": v.rule, "file": v.file, "symbol": v.symbol,
                                  "reason": PLACEHOLDER_REASON})
        return Baseline(eintraege)

    def write(self, root: Path) -> Path:
        pfad = root / BASELINE_FILE
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(json.dumps({"version": 1, "entries": self.entries}, indent=2,
                                   ensure_ascii=False) + "\n", encoding="utf-8")
        return pfad
