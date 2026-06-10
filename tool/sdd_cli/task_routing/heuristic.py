"""complexity_score Heuristik für Task-Routing (FR-01, SPEC-0045)."""
from __future__ import annotations

from typing import Any

# Gewichtungen für die Heuristik
_WEIGHT_FILES = 5       # pro betroffenem File
_WEIGHT_LINES = 0.1     # pro geschätzter Zeile
_WEIGHT_CONTRACTS = 10  # pro abhängigem Contract


def compute_complexity_score(task: Any) -> int:
    """Berechnet complexity_score (0–100) aus Heuristik-Features.

    Features:
      - affected_files:      Anzahl betroffener Dateien
      - estimated_lines:     Geschätzte geänderte Zeilen
      - dependent_contracts: Anzahl abhängiger Contracts

    Gibt integer 0–100 zurück (geclampt).
    """
    files = len(getattr(task, "affected_files", None) or [])
    lines = getattr(task, "estimated_lines", 0) or 0
    contracts = getattr(task, "dependent_contracts", 0) or 0

    raw = (
        files * _WEIGHT_FILES
        + lines * _WEIGHT_LINES
        + contracts * _WEIGHT_CONTRACTS
    )
    return max(0, min(100, int(raw)))
