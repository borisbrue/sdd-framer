"""Konfiguration und Pfad-Auflösung für ein SDD-Projekt."""
from __future__ import annotations

import copy
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yaml

SDD_DIR = ".sdd"
CONFIG_FILE = "config.yaml"

# Lokale Ergaenzung zu config.yaml, gitignored (#103). Ueberlagert die
# versionierte Konfiguration Schluessel fuer Schluessel. Gedacht fuer das, was
# nicht in die Versionierung gehoert — zuerst der PWA-Token, der die
# Bearer-Credential fuer POST /api/remote/run ist.
LOCAL_CONFIG_FILE = "config.local.yaml"

_LOKAL_KOPF = (
    "# Lokale Ergaenzung zu .sdd/config.yaml — NICHT versionieren.\n"
    "# Ueberlagert config.yaml Schluessel fuer Schluessel. Hier stehen Werte,\n"
    "# die nur auf diesem Rechner gelten, etwa pwa.auth.token.\n"
)


@dataclass
class SddConfig:
    """Geparste Projektkonfiguration.

    `raw` ist die wirksame Sicht: config.yaml, ueberlagert von
    config.local.yaml. `raw_basis` ist nur der Inhalt der versionierten Datei.
    Wer config.yaml zurueckschreibt, muss `basis` nehmen — sonst landen lokale
    Werte in der Versionierung (#103).
    """
    root: Path
    raw: dict
    raw_basis: dict | None = None

    @property
    def basis(self) -> dict:
        """Nur config.yaml, ohne lokale Ueberlagerung."""
        return self.raw_basis if self.raw_basis is not None else self.raw

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

    # ── Pipeline-Monitor der Web-UI (SPEC-0037, umgebaut in SPEC-0058) ────────

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
        basis = yaml.safe_load(f) or {}
    wirksam = _deep_merge(basis, load_local(project_root))
    return SddConfig(root=project_root, raw=wirksam, raw_basis=basis)


def _deep_merge(basis: dict, ueber: dict) -> dict:
    """Neues dict: `basis`, rekursiv ueberlagert von `ueber`. Listen ersetzen."""
    ergebnis = copy.deepcopy(basis)
    for schluessel, wert in (ueber or {}).items():
        if isinstance(wert, dict) and isinstance(ergebnis.get(schluessel), dict):
            ergebnis[schluessel] = _deep_merge(ergebnis[schluessel], wert)
        else:
            ergebnis[schluessel] = copy.deepcopy(wert)
    return ergebnis


def local_config_path(root: Path) -> Path:
    return Path(root) / SDD_DIR / LOCAL_CONFIG_FILE


def load_local(root: Path) -> dict:
    """Inhalt von config.local.yaml, oder {} wenn es sie nicht gibt."""
    pfad = local_config_path(root)
    if not pfad.is_file():
        return {}
    daten = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
    return daten if isinstance(daten, dict) else {}


def set_local(root: Path, schluessel: str, wert: object) -> Path:
    """Setzt einen Wert in config.local.yaml, z.B. `pwa.auth.token`.

    Atomar (temporaere Datei + rename) und mit Rechten 0600 — die Datei ist fuer
    Geheimnisse da. Andere Schluessel der Datei bleiben erhalten.
    """
    pfad = local_config_path(root)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    daten = load_local(root)
    knoten = daten
    teile = schluessel.split(".")
    for teil in teile[:-1]:
        if not isinstance(knoten.get(teil), dict):
            knoten[teil] = {}
        knoten = knoten[teil]
    knoten[teile[-1]] = wert

    fd, tmp = tempfile.mkstemp(dir=str(pfad.parent), suffix=".tmp")
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(_LOKAL_KOPF)
            yaml.dump(daten, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        os.replace(tmp, pfad)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return pfad
