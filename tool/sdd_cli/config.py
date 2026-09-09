"""Konfiguration und Pfad-Auflösung für ein SDD-Projekt."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import yaml


SDD_DIR = ".sdd"
CONFIG_FILE = "config.yaml"


@dataclass
class SddConfig:
    """Geparste Projektkonfiguration."""
    root: Path
    raw: dict

    @property
    def sdd_dir(self) -> Path:
        return self.root / SDD_DIR

    @property
    def templates_dir(self) -> Path:
        return self.sdd_dir / "templates"

    @property
    def schemas_dir(self) -> Path:
        return self.sdd_dir / "schemas"

    @property
    def specs_dir(self) -> Path:
        return self.sdd_dir / "specs"

    @property
    def contracts_dir(self) -> Path:
        return self.sdd_dir / "contracts"

    @property
    def tests_dir(self) -> Path:
        """SDD/LLM-Tests (Contract-Tests, Holdout-Szenarien etc.)."""
        return self.sdd_dir / "tests"

    @property
    def project_tests_dir(self) -> Path:
        """Framework-Tests (pytest etc.) im Projektwurzelverzeichnis."""
        return self.root / "tests"

    @property
    def all_test_dirs(self) -> list[Path]:
        """Alle Verzeichnisse, in denen TST-Dokumente liegen können."""
        return [d for d in [self.tests_dir, self.project_tests_dir] if d.exists()]

    @property
    def adr_dir(self) -> Path:
        """Ablageort der ADRs. Konfigurierbar wie traceability.output_path."""
        return self.root / self.raw.get("adr", {}).get("output_dir", "docs/adr")

    @property
    def docs_dir(self) -> Path:
        return self.sdd_dir / "docs"

    @property
    def projects_dir(self) -> Path:
        return self.sdd_dir / "projects"

    @property
    def holdout_dir(self) -> Path:
        return self.sdd_dir / "holdout"

    @property
    def evaluations_dir(self) -> Path:
        return self.sdd_dir / "evaluations"

    @property
    def test_runs_dir(self) -> Path:
        return self.sdd_dir / "test-runs"

    def id_padding(self) -> int:
        return self.raw.get("ids", {}).get("padding", 4)

    def prefix(self, kind: str) -> str:
        _defaults = {
            "spec": "SPEC", "contract": "CON", "test": "TST",
            "project": "PRJ", "holdout": "HOL",
        }
        return self.raw.get("ids", {}).get(f"{kind}_prefix", _defaults.get(kind, kind.upper()))

    def validation_rule(self, name: str, default=True):
        return self.raw.get("validation", {}).get(name, default)

    def llm_timeout(self) -> int:
        """Zeitlimit fuer einen einzelnen LLM-Aufruf in Sekunden.

        Gegenstueck zu test_runner.timeout_per_spec. Der Regression-Check
        brauchte fuer reale Specs mehrere Minuten; der frueher fest verdrahtete
        Wert von 120s war systematisch zu knapp.
        """
        try:
            return max(1, int((self.raw.get("llm") or {}).get("timeout_seconds", 600)))
        except (TypeError, ValueError):
            return 600

    def runner_command(self) -> str:
        return self.raw.get("test_runner", {}).get("command", "pytest")

    def runner_extra_args(self) -> list[str]:
        return self.raw.get("test_runner", {}).get("extra_args", [])

    def runner_timeout(self) -> int:
        return self.raw.get("test_runner", {}).get("timeout_per_spec", 120)

    def obsidian_raw(self) -> dict:
        return self.raw.get("obsidian", {})

    # ── SPEC-0015: SOLID Gate & Pattern Suggestions ───────────────────────────

    def solid_gate_enabled(self) -> bool:
        return self.raw.get("solid_gate", {}).get("enabled", True)

    def solid_gate_mode(self) -> str:
        """'warn' | 'block'"""
        return self.raw.get("solid_gate", {}).get("mode", "warn")

    def pattern_suggestions_enabled(self) -> bool:
        return self.raw.get("pattern_suggestions", {}).get("enabled", True)

    def pattern_suggestions_max(self) -> int:
        return int(self.raw.get("pattern_suggestions", {}).get("max_suggestions", 4))

    # ── SPEC-0037: Autopilot + DAG-Monitor ───────────────────────────────────

    def autopilot_config(self) -> dict:
        return self.raw.get("autopilot", {})

    def dag_monitor_sse_heartbeat(self) -> int:
        return int(self.raw.get("dag_monitor", {}).get("sse_heartbeat_seconds", 15))

    def dag_monitor_max_runs_history(self) -> int:
        return int(self.raw.get("dag_monitor", {}).get("max_runs_history", 5))


def find_project_root(start: Path | None = None) -> Path | None:
    """Sucht aufwärts nach einem Verzeichnis mit .sdd/config.yaml."""
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / SDD_DIR / CONFIG_FILE).is_file():
            return candidate
    return None


def load_config(root: Path | None = None) -> SddConfig:
    """Lädt die Projektkonfiguration. Wirft, wenn kein Projekt gefunden wird."""
    project_root = root or find_project_root()
    if project_root is None:
        raise FileNotFoundError(
            "Kein SDD-Projekt gefunden. Führe `sdd init` aus, um eines anzulegen."
        )
    config_path = project_root / SDD_DIR / CONFIG_FILE
    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return SddConfig(root=project_root, raw=raw)
