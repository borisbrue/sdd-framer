"""Lineare Normierung von Metriken auf [0, 1] (SPEC-0054 FR-08, CON-0196)."""
from __future__ import annotations

BUILTIN_NORMALIZATION: dict[str, tuple[float, float]] = {
    "lint_per_kloc": (0, 10),
    "type_errors": (0, 20),
    "suppressions": (0, 10),
    "test_ratio": (1.0, 0.0),
}


def normalize(raw: float, good: float, bad: float) -> float:
    """`good < bad`: kleiner ist besser; `good > bad`: größer ist besser."""
    if good == bad:
        raise ValueError("good und bad dürfen nicht gleich sein")
    wert = (bad - raw) / (bad - good) if good < bad else (raw - bad) / (good - bad)
    return max(0.0, min(1.0, wert))
