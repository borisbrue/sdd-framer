"""Score-Baum (SPEC-0105).

Blätter sind Metriken, innere Knoten Teilscores. Jeder innere Knoten trägt eine n/a-Regel
(`renormalize`, `strict`, `quorum`) und aggregiert per gewichtetem Mittelwert.
"""
from __future__ import annotations

from dataclasses import dataclass, field

NA_POLICIES = ("renormalize", "strict", "quorum")


@dataclass
class MetricLeaf:
    name: str
    raw: float | None
    normalized: float | None
    weight: float = 1.0
    reason: str | None = None

    def score(self) -> float | None:
        return self.normalized

    def renormalized(self) -> bool:
        return False

    def incomplete(self) -> bool:
        return self.normalized is None

    def to_dict(self) -> dict:
        d: dict = {"name": self.name, "raw": self.raw, "normalized": _round(self.normalized),
                   "weight": self.weight}
        if self.reason is not None:
            d["reason"] = self.reason
        return d


def _weighted_mean(children: list) -> float:
    gewicht = sum(c.weight for c in children)
    return sum(c.weight * c.score() for c in children) / gewicht


@dataclass
class ScoreNode:
    name: str
    weight: float
    children: list = field(default_factory=list)
    policy: str = "renormalize"
    quorum: float = 0.5
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.policy not in NA_POLICIES:
            raise ValueError(f"unbekannte n/a-Regel {self.policy!r}")

    def _gewichtete(self) -> list:
        return [c for c in self.children if c.weight > 0]

    def score(self) -> float | None:
        kinder = self._gewichtete()
        vorhanden = [c for c in kinder if c.score() is not None]
        if not vorhanden:
            return None
        fehlend = len(kinder) - len(vorhanden)
        if self.policy == "strict" and fehlend:
            return None
        if self.policy == "quorum" and fehlend / len(kinder) > self.quorum:
            return None
        return max(0.0, min(1.0, _weighted_mean(vorhanden)))

    def renormalized(self) -> bool:
        return self.score() is not None and any(c.score() is None for c in self._gewichtete())

    def incomplete(self) -> bool:
        return self.score() is None or any(c.incomplete() for c in self.children)

    def na_reason(self) -> str | None:
        if self.score() is not None:
            return None
        if self.reason:
            return self.reason
        gruende = [c.reason if isinstance(c, MetricLeaf) else c.na_reason()
                   for c in self._gewichtete() if c.score() is None]
        gruende = [g for g in gruende if g]
        if not self._gewichtete():
            return "keine Messwerte"
        return "; ".join(dict.fromkeys(gruende)) or "keine Messwerte"

    def to_dict(self) -> dict:
        d: dict = {"name": self.name, "weight": self.weight, "score": _round(self.score())}
        if self.renormalized():
            d["renormalized"] = True
        grund = self.na_reason()
        if grund:
            d["reason"] = grund
        knoten = [c.to_dict() for c in self.children if isinstance(c, ScoreNode)]
        metriken = [c.to_dict() for c in self.children if isinstance(c, MetricLeaf)]
        if knoten:
            d["children"] = knoten
        if metriken:
            d["metrics"] = metriken
        return d


def _round(wert: float | None) -> float | None:
    return None if wert is None else round(wert, 4)
