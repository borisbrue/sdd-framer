"""PathPolicy: Schreibrechte je Rolle, Task und Pfad."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str | None = None


def normalize(path: str) -> str | None:
    raise NotImplementedError


class PathPolicy:
    def __init__(self, protected_paths=()) -> None:
        raise NotImplementedError

    @classmethod
    def from_config(cls, raw_config):
        raise NotImplementedError

    def check(self, role: str, path: str, task) -> PolicyDecision:
        raise NotImplementedError
