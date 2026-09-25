"""Einstellungen unter `quality:` in `.sdd/config.yaml` (SPEC-0054 FR-10, CON-0196)."""
from __future__ import annotations

from dataclasses import dataclass, field

from .config import ConfigProblem
from .gates import validate_gate

DEFAULT_ROOT_WEIGHTS = {"requirements": 0.5, "architecture": 0.25, "code_quality": 0.25,
                        "judge": 0.0}
DEFAULT_SEVERITY_WEIGHTS = {"error": 1.0, "warn": 0.25}
FINALIZE_MODES = ("warn", "block", "off")


@dataclass
class QualitySettings:
    root_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_ROOT_WEIGHTS))
    holdout_weight: float = 0.5
    metric_weights: dict[str, float] = field(default_factory=dict)
    architecture_threshold: float = 5.0
    severity_weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_SEVERITY_WEIGHTS))
    gates: list[str] = field(default_factory=list)
    finalize: str = "warn"
    # SPEC-0059 FR-06 / CON-0209 INV-06: `sdd arch check` im Pre-Commit-Hook.
    arch_pre_commit: object = True

    def metric_weight(self, name: str) -> float:
        return float(self.metric_weights.get(name, 1.0))

    @classmethod
    def from_raw(cls, raw_config: dict) -> QualitySettings:
        q = (raw_config or {}).get("quality") or {}
        weights = q.get("weights") or {}
        root = dict(DEFAULT_ROOT_WEIGHTS)
        for key in root:
            if isinstance(weights.get(key), (int, float)):
                root[key] = float(weights[key])
        req = weights.get("requirements")
        holdout = req.get("holdout", 0.5) if isinstance(req, dict) else 0.5
        cq = weights.get("code_quality")
        arch = q.get("architecture") or {}
        return cls(
            root_weights=root,
            holdout_weight=float(holdout),
            metric_weights={k: float(v) for k, v in cq.items()} if isinstance(cq, dict) else {},
            architecture_threshold=float(arch.get("threshold", 5)),
            severity_weights={**DEFAULT_SEVERITY_WEIGHTS,
                              **{k: float(v) for k, v in (arch.get("severity_weights") or {}).items()}},
            gates=[str(g) for g in (q.get("gates") or [])],
            finalize=str(q.get("finalize", "warn")),
            arch_pre_commit=q.get("arch_pre_commit", True),
        )


def settings_problems(settings: QualitySettings) -> list[ConfigProblem]:
    """Regelgruppe `quality` (CON-0196 INV-07): Gates, Gewichte, Schwelle, Finalize-Modus."""
    probleme = [ConfigProblem(f"quality.gates[{i}]", f"{g!r}: {fehler}")
                for i, g in enumerate(settings.gates) if (fehler := validate_gate(g))]
    gewichte = {**settings.root_weights, "requirements.holdout": settings.holdout_weight,
                **{f"code_quality.{k}": v for k, v in settings.metric_weights.items()}}
    probleme += [ConfigProblem(f"quality.weights.{k}", "Gewicht darf nicht negativ sein")
                 for k, v in gewichte.items() if v < 0]
    if not 0 <= settings.holdout_weight <= 1:
        probleme.append(ConfigProblem("quality.weights.requirements.holdout",
                                      "Wert in [0, 1] erwartet"))
    if settings.architecture_threshold <= 0:
        probleme.append(ConfigProblem("quality.architecture.threshold", "muss größer 0 sein"))
    if not isinstance(settings.arch_pre_commit, bool):
        probleme.append(ConfigProblem("quality.arch_pre_commit", "true oder false erwartet"))
    if settings.finalize not in FINALIZE_MODES:
        probleme.append(ConfigProblem("quality.finalize",
                                      f"erlaubt: {', '.join(FINALIZE_MODES)}"))
    return probleme
