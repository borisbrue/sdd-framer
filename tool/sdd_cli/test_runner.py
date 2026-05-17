"""Test-Runner für SPEC-0006: Test-Runs pro Spec auslösen und Ergebnisse persistieren."""
from __future__ import annotations

import json
import subprocess
import shutil
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from .config import SddConfig
from .frontmatter import parse_safe

# Dateierweiterungen, die nicht via pytest ausgeführt werden können
_UNSUPPORTED_EXTENSIONS = {".feature", ".js", ".ts", ".spec.ts"}
_PLACEHOLDER_ARTIFACT = "tests/<level>/"

MAX_RUNS_PER_SPEC = 50

TestStatus = Literal["passed", "failed", "error", "missing", "skipped"]


@dataclass
class TestResult:
    test_id: str
    artifact: str
    status: TestStatus
    duration_s: float = 0.0
    message: str = ""


@dataclass
class RunReport:
    spec_id: str
    runner: str
    started_at: str
    duration_s: float
    exit_code: int
    tests: list[TestResult] = field(default_factory=list)
    contract_coverage: dict[str, bool] = field(default_factory=dict)

    @property
    def passed(self) -> int:
        return sum(1 for t in self.tests if t.status == "passed")

    @property
    def failed(self) -> int:
        return sum(1 for t in self.tests if t.status in ("failed", "error"))

    @property
    def skipped(self) -> int:
        return sum(1 for t in self.tests if t.status in ("skipped", "missing"))

    def to_json(self) -> dict:
        d = asdict(self)
        d["passed"] = self.passed
        d["failed"] = self.failed
        d["skipped"] = self.skipped
        return d


def _find_tst_doc(config: SddConfig, tst_id: str) -> Path | None:
    for md in config.tests_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == tst_id:
            return md
    return None


def _resolve_artifact(config: SddConfig, tst_id: str) -> tuple[str, TestStatus, str]:
    """Gibt (artifact_path, status, message) zurück."""
    tst_doc_path = _find_tst_doc(config, tst_id)
    if tst_doc_path is None:
        return ("", "missing", f"TST-Dokument {tst_id} nicht gefunden.")

    doc = parse_safe(tst_doc_path)
    artifact = (doc.frontmatter.get("artifact") or "").strip().strip('"')

    if not artifact or _PLACEHOLDER_ARTIFACT in artifact:
        return (artifact, "missing", f"artifact: ist Platzhalter in {tst_id}.")

    suffix = Path(artifact).suffix
    if suffix in _UNSUPPORTED_EXTENSIONS:
        return (artifact, "skipped", f"Runner für {suffix}-Artefakte nicht unterstützt.")

    return (artifact, "passed", "")  # status wird nach Ausführung überschrieben


def _run_pytest(config: SddConfig, artifact_path: str, timeout: int) -> tuple[TestStatus, float, str]:
    """Führt pytest für ein einzelnes Artefakt aus. Gibt (status, duration_s, message) zurück."""
    runner = config.runner_command()

    abs_path = config.root / artifact_path
    if not abs_path.exists():
        return ("missing", 0.0, f"Artefakt-Datei nicht gefunden: {artifact_path}")

    # sys.executable -m pytest nutzt dieselbe Python-Umgebung wie der aufrufende Prozess
    # (z.B. web/api/.venv), sodass alle installierten Packages verfügbar sind.
    # Fallback auf bare runner wenn explizit konfiguriert und nicht "pytest".
    if runner == "pytest":
        cmd = [sys.executable, "-m", "pytest", str(abs_path), "--tb=short", "-q"]
    else:
        if not shutil.which(runner):
            raise RuntimeError(
                f"'{runner}' nicht gefunden – bitte installieren oder "
                f"test_runner.command in .sdd/config.yaml anpassen."
            )
        cmd = [runner, str(abs_path), "--tb=short", "-q"]
    cmd += config.runner_extra_args()
    start = datetime.now(timezone.utc).timestamp()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(config.root),
        )
    except subprocess.TimeoutExpired:
        duration = datetime.now(timezone.utc).timestamp() - start
        return ("error", round(duration, 3), f"Timeout nach {timeout}s.")

    duration = round(datetime.now(timezone.utc).timestamp() - start, 3)
    if result.returncode == 0:
        return ("passed", duration, "")
    output = (result.stdout + result.stderr).strip()
    # Kurze Fehlermeldung: letzte 20 non-leer Zeilen
    lines = [l for l in output.splitlines() if l.strip()]
    short = "\n".join(lines[-20:])
    return ("failed", duration, short)


def _compute_contract_coverage(config: SddConfig, spec_id: str, results: list[TestResult]) -> dict[str, bool]:
    """Bestimmt welche Contracts durch ≥ 1 grünen Test abgedeckt sind."""
    spec_doc = None
    for md in config.specs_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == spec_id:
            spec_doc = doc
            break

    if spec_doc is None:
        return {}

    contracts = spec_doc.frontmatter.get("contracts") or []
    passed_tst_ids = {t.test_id for t in results if t.status == "passed"}

    coverage: dict[str, bool] = {}
    for con_id in contracts:
        # Contract gilt als covered wenn mind. ein grüner Test ihn referenziert
        covered = False
        for md in config.tests_dir.rglob("*.md"):
            doc = parse_safe(md)
            if doc and doc.frontmatter.get("id") in passed_tst_ids:
                if doc.frontmatter.get("contract") == con_id:
                    covered = True
                    break
        coverage[con_id] = covered

    return coverage


def _persist(config: SddConfig, report: RunReport) -> Path:
    """Speichert den Run-JSON und rotiert wenn > MAX_RUNS_PER_SPEC."""
    runs_dir = config.test_runs_dir
    runs_dir.mkdir(parents=True, exist_ok=True)

    ts = report.started_at.replace(":", "-").replace(".", "-")
    out_path = runs_dir / f"{report.spec_id}-{ts}.json"
    out_path.write_text(json.dumps(report.to_json(), indent=2, ensure_ascii=False), encoding="utf-8")

    # Rotation
    existing = sorted(runs_dir.glob(f"{report.spec_id}-*.json"))
    while len(existing) > MAX_RUNS_PER_SPEC:
        existing.pop(0).unlink()

    return out_path


def run(config: SddConfig, spec_id: str) -> RunReport:
    """Führt alle Tests einer Spec aus und gibt einen RunReport zurück."""
    spec_doc = None
    for md in config.specs_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == spec_id:
            spec_doc = doc
            break

    if spec_doc is None:
        raise ValueError(f"Spec {spec_id!r} nicht gefunden.")

    tst_ids: list[str] = spec_doc.frontmatter.get("tests") or []
    if not tst_ids:
        raise ValueError(f"Spec {spec_id} hat keine Tests im Frontmatter (tests: []).")

    runner = config.runner_command()
    timeout = config.runner_timeout()
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    wall_start = datetime.now(timezone.utc).timestamp()

    results: list[TestResult] = []
    for tst_id in tst_ids:
        artifact, pre_status, pre_msg = _resolve_artifact(config, tst_id)
        if pre_status in ("missing", "skipped"):
            results.append(TestResult(tst_id, artifact, pre_status, message=pre_msg))
            continue

        status, duration, message = _run_pytest(config, artifact, timeout)
        results.append(TestResult(tst_id, artifact, status, duration, message))

    total_duration = round(datetime.now(timezone.utc).timestamp() - wall_start, 3)
    has_failure = any(r.status in ("failed", "error") for r in results)
    exit_code = 1 if has_failure else 0

    contract_coverage = _compute_contract_coverage(config, spec_id, results)

    report = RunReport(
        spec_id=spec_id,
        runner=runner,
        started_at=started_at,
        duration_s=total_duration,
        exit_code=exit_code,
        tests=results,
        contract_coverage=contract_coverage,
    )
    _persist(config, report)
    return report


def run_all(config: SddConfig) -> list[RunReport]:
    """Führt Tests für alle Specs mit nicht-leerem tests:-Frontmatter aus."""
    reports = []
    for md in sorted(config.specs_dir.rglob("*.md")):
        doc = parse_safe(md)
        if not doc:
            continue
        spec_id = doc.frontmatter.get("id")
        if not spec_id or not (doc.frontmatter.get("tests") or []):
            continue
        try:
            reports.append(run(config, spec_id))
        except Exception as exc:
            # Einzelne Spec-Fehler blockieren nicht den Gesamtlauf
            reports.append(RunReport(
                spec_id=spec_id,
                runner=config.runner_command(),
                started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                duration_s=0.0,
                exit_code=2,
                tests=[TestResult(spec_id, "", "error", message=str(exc))],
            ))
    return reports


def latest_report(config: SddConfig, spec_id: str) -> RunReport | None:
    """Lädt den neuesten gespeicherten Run-JSON für eine Spec."""
    runs_dir = config.test_runs_dir
    if not runs_dir.exists():
        return None
    candidates = sorted(runs_dir.glob(f"{spec_id}-*.json"))
    if not candidates:
        return None
    data = json.loads(candidates[-1].read_text(encoding="utf-8"))
    tests = [TestResult(**{k: v for k, v in t.items() if k in TestResult.__dataclass_fields__})
             for t in data.get("tests", [])]
    return RunReport(
        spec_id=data["spec_id"],
        runner=data["runner"],
        started_at=data["started_at"],
        duration_s=data["duration_s"],
        exit_code=data["exit_code"],
        tests=tests,
        contract_coverage=data.get("contract_coverage", {}),
    )
