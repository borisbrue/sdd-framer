"""Test-Runner für SPEC-0006: Test-Runs pro Spec auslösen und Ergebnisse persistieren."""
from __future__ import annotations

import json
import shlex
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from .config import SddConfig
from .frontmatter import parse_safe
from .test_languages import PYTHON, TestLanguage, bekannte_suffixe, language_for_path

# Artefakte, die kein ausfuehrbarer Testcode sind. Sprachdateien stehen hier nicht mehr:
# welche Endung wie laeuft, sagt test_languages (HF-0010).
_UNSUPPORTED_EXTENSIONS = {".feature"}
_PLACEHOLDER_ARTIFACT = "tests/<level>/"

MAX_RUNS_PER_SPEC = 50
PROBE_RUNNER_PREFIX = "probe:"

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
    # SPEC-0054 CON-0197 INV-05a: nur mit Testsonde gesetzt, sonst nicht im JSON.
    junit: str | None = None
    testcases: list[dict] | None = None
    git_sha: str | None = None

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
        for key in ("junit", "testcases", "git_sha"):
            if d[key] is None and not self.runner.startswith(PROBE_RUNNER_PREFIX):
                del d[key]
        d["passed"] = self.passed
        d["failed"] = self.failed
        d["skipped"] = self.skipped
        return d


def _find_tst_doc(config: SddConfig, tst_id: str) -> Path | None:
    for base in config.all_test_dirs:
        for md in base.rglob("*.md"):
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

    if language_for_path(artifact) is None:
        return (
            artifact,
            "skipped",
            f"Kein Sprachprofil für {suffix}-Testdateien. Bekannt: "
            f"{', '.join(bekannte_suffixe())}. Ergänze ein Profil in test_languages.py "
            f"oder deklariere im TST-Dokument ein artifact mit bekannter Endung.",
        )

    return (artifact, "passed", "")  # status wird nach Ausführung überschrieben


_RUNNER_CACHE: dict[tuple[str, str], list[str]] = {}


def _ist_uv_projekt(project_root: Path) -> bool:
    """uv.lock ist das eindeutige Signal; pyproject.toml allein reicht nicht."""
    return (project_root / "uv.lock").exists()


def _resolve_runner(
    runner: str, project_root: Path | None = None, language: TestLanguage | None = None
) -> list[str]:
    """Bestimmt das aufrufbare Runner-Kommando. Wirft RuntimeError, wenn keins passt.

    `sys.executable -m pytest` nutzt die Umgebung des aufrufenden Prozesses. Das ist
    im sdd-Repo selbst richtig, in einem fremden Projekt aber der Interpreter, der
    `sdd` ausfuehrt — und der hat pytest in der Regel nicht. Blankes `pytest` liegt
    ohne aktiviertes venv nicht im PATH, was bei uv-Projekten der Normalfall ist.

    In einem uv-Projekt lief das Pre-Commit-Gate deshalb nie: beide Kandidaten
    scheiterten, der Lauf meldete "Kein lauffaehiger Test-Runner gefunden" und der
    Commit ging durch. `uv run pytest` wird darum zuerst probiert, wenn eine
    uv.lock danebenliegt und uv im PATH ist — das ist die Umgebung, die das
    Projekt selbst beschreibt.

    Ohne --no-sync: seit dem venv-Schutz beim Container-Start (#74) schreibt uv
    nicht mehr in den bind-gemounteten Workspace.

    Reihenfolge: konfiguriertes Kommando, sonst uv im uv-Projekt, sonst der eigene
    Interpreter, sonst ein pytest im PATH. Das Ergebnis wird je Projekt gecacht,
    sonst kostet jeder Testlauf einen zusaetzlichen --version-Aufruf.
    """
    root = Path(project_root) if project_root is not None else Path.cwd()
    lang = language or PYTHON
    key = (runner, f"{root}|{lang.name}")
    if key in _RUNNER_CACHE:
        return _RUNNER_CACHE[key]

    candidates: list[list[str]] = []
    if runner != "pytest":
        # shlex, damit mehrwortige Kommandos wie `uv run pytest` funktionieren –
        # shutil.which("uv run pytest") schlug vorher immer fehl.
        parts = shlex.split(runner)
        if parts and shutil.which(parts[0]):
            candidates.append(parts)
    elif lang is PYTHON:
        if _ist_uv_projekt(root) and shutil.which("uv"):
            candidates.append(["uv", "run", "pytest"])
        candidates.append([sys.executable, "-m", "pytest"])
        if shutil.which("pytest"):
            candidates.append(["pytest"])
    else:
        # Der Blueprint-Default `pytest` steht in einem Projekt anderer Sprache. Statt
        # pytest auf eine .rs-Datei zu werfen, gilt das Standardkommando der Sprache.
        if lang.default_runner and shutil.which(lang.default_runner[0]):
            candidates.append(list(lang.default_runner))

    for cand in candidates:
        # Fremde Testkommandos vertragen kein `--version` hinter ihrem Unterbefehl
        # (`cargo test --version`), deshalb wird dort nur das Programm geprobt.
        probe_cmd = [*cand, "--version"] if lang is PYTHON else [cand[0], "--version"]
        try:
            probe = subprocess.run(probe_cmd, capture_output=True,
                                   timeout=60, cwd=str(root))
        except (OSError, subprocess.SubprocessError):
            continue
        if probe.returncode == 0:
            _RUNNER_CACHE[key] = cand
            return cand

    if lang is not PYTHON:
        beispiel = " ".join(lang.default_runner)
        raise RuntimeError(
            f"Kein lauffaehiger Test-Runner fuer {lang.name} gefunden "
            f"(konfiguriert: {runner!r}). Setze test_runner.command in .sdd/config.yaml, "
            f"z.B. auf {beispiel!r}."
        )

    raise RuntimeError(
        f"Kein lauffaehiger Test-Runner gefunden (konfiguriert: {runner!r}). "
        f"Installiere pytest oder setze test_runner.command in .sdd/config.yaml, "
        f"z.B. auf 'uv run pytest'."
    )


def _run_artifact_tests(
    config: SddConfig, artifact_path: str, timeout: int
) -> tuple[TestStatus, float, str]:
    """Führt die Tests eines Artefakts aus. Gibt (status, duration_s, message) zurück.

    Das Kommando baut das Sprachprofil der Datei (HF-0010): pytest bekommt den Pfad,
    cargo den Testnamen, npm den Pfad hinter `--`.
    """
    runner = config.runner_command()

    abs_path = config.root / artifact_path
    if not abs_path.exists():
        return ("missing", 0.0, f"Artefakt-Datei nicht gefunden: {artifact_path}")

    lang = language_for_path(artifact_path) or PYTHON
    cmd = lang.run_argv(_resolve_runner(runner, config.root, lang), abs_path, config.root)
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
    if result.returncode in lang.empty_run_exit_codes:
        # pytest-Exitcode 5 = keine Tests gesammelt. Das ist kein Fehlschlag,
        # sondern ein leerer Lauf – und muss davon unterscheidbar bleiben,
        # statt als rotes Ergebnis durchgereicht zu werden. Welche Codes das je
        # Sprache sind, sagt das Profil.
        return ("skipped", duration, f"Keine Tests gesammelt in {artifact_path}.")
    output = (result.stdout + result.stderr).strip()
    # Kurze Fehlermeldung: letzte 20 non-leer Zeilen
    lines = [zeile for zeile in output.splitlines() if zeile.strip()]
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
        for base in config.all_test_dirs:
            for md in base.rglob("*.md"):
                doc = parse_safe(md)
                if (doc and doc.frontmatter.get("id") in passed_tst_ids
                        and doc.frontmatter.get("contract") == con_id):
                    covered = True
                    break
            if covered:
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

    probe_setup = _test_probe(config)
    if probe_setup is not None:
        report, _ = _run_with_probe(config, spec_id, tst_ids, *probe_setup)
        return report

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

        status, duration, message = _run_artifact_tests(config, artifact, timeout)
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


# ── SPEC-0054: Testsonde aus .sdd/quality.yaml (CON-0197 INV-05a/05b) ──────────

def _test_probe(config: SddConfig):
    """(QualityConfig, Probe) der Sonde mit role tests, oder None ohne quality.yaml."""
    from .quality.config import QualityConfigError, load_quality_config

    try:
        qcfg = load_quality_config(config.root)
    except FileNotFoundError:
        return None
    except QualityConfigError as exc:
        raise RuntimeError(f".sdd/quality.yaml ungültig: {exc}") from exc
    probe = qcfg.probe_for_role("tests")
    return (qcfg, probe) if probe is not None else None


def _in_artifact(case: dict, artifact: str) -> bool:
    if case.get("file"):
        return case["file"] == artifact
    modul = artifact.removesuffix(".py").replace("/", ".")
    return case["classname"] == modul or case["classname"].startswith(modul + ".")


def _tst_status(cases: list[dict]) -> TestStatus:
    if not cases:
        return "missing"
    stati = {c["status"] for c in cases}
    if stati & {"failed", "error"}:
        return "failed"
    return "skipped" if stati == {"skipped"} else "passed"


def run_probe(config: SddConfig, qcfg, probe, keep_output: Path | None = None):
    """Führt die Testsonde aus – derselbe Pfad für `sdd test run` und `sdd quality measure`."""
    from .quality.files import collect_files
    from .quality.probe import ProbeRun

    dateien = collect_files(config.root, qcfg.paths, qcfg.exclude)
    return ProbeRun(config.root, dateien).execute(probe, keep_output=keep_output)


def run_with_probe(config: SddConfig, spec_id: str, qcfg, probe):
    """(RunReport, ProbeOutcome) für `sdd quality measure --spec`; ValueError ohne TST-Tests."""
    spec_doc = next((d for d in (parse_safe(md) for md in config.specs_dir.rglob("*.md"))
                     if d and d.frontmatter.get("id") == spec_id), None)
    tst_ids = (spec_doc.frontmatter.get("tests") or []) if spec_doc else []
    if not tst_ids:
        raise ValueError(f"Spec {spec_id} hat keine Tests im Frontmatter (tests: []).")
    return _run_with_probe(config, spec_id, tst_ids, qcfg, probe)


def _run_with_probe(config: SddConfig, spec_id: str, tst_ids: list[str], qcfg, probe):
    from .quality.diff import current_sha

    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    wall_start = datetime.now(timezone.utc).timestamp()
    stem = f"{spec_id}-{started_at.replace(':', '-').replace('.', '-')}"
    junit_pfad = config.test_runs_dir / f"{stem}.junit.xml"
    outcome = run_probe(config, qcfg, probe, keep_output=junit_pfad)
    if not outcome.ok:
        raise RuntimeError(f"Testsonde {probe.name}: {outcome.reason}")

    faelle = [{"name": c.name, "classname": c.classname, "status": c.status,
               "frs": list(c.frs), **({"file": c.file} if c.file else {})}
              for c in outcome.result.cases]
    results = []
    for tst_id in tst_ids:
        artifact, pre_status, pre_msg = _resolve_artifact(config, tst_id)
        passende = [c for c in faelle if artifact and _in_artifact(c, artifact)]
        results.append(TestResult(tst_id, artifact, _tst_status(passende),
                                  message=pre_msg if not passende else ""))
    report = RunReport(
        spec_id=spec_id,
        runner=f"{PROBE_RUNNER_PREFIX}{probe.name}",
        started_at=started_at,
        duration_s=round(datetime.now(timezone.utc).timestamp() - wall_start, 3),
        exit_code=1 if any(c["status"] in ("failed", "error") for c in faelle) else 0,
        tests=results,
        contract_coverage=_compute_contract_coverage(config, spec_id, results),
        junit=junit_pfad.relative_to(config.root).as_posix(),
        testcases=[{k: v for k, v in c.items() if k != "file"} for c in faelle],
        git_sha=current_sha(config.root),
    )
    _persist(config, report)
    return report, outcome


def latest_probe_run(config: SddConfig, spec_id: str, sha: str | None):
    """(Testfälle, Pfad) des jüngsten Laufs mit Testsonde auf demselben Git-Stand."""
    from .quality.parsers import TestCase

    runs_dir = config.test_runs_dir
    for pfad in sorted(runs_dir.glob(f"{spec_id}-*.json"), reverse=True) if runs_dir.exists() else []:
        try:
            daten = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if daten.get("testcases") is None or daten.get("git_sha") != sha:
            continue
        return [TestCase(c["name"], c.get("classname", ""), c["status"], tuple(c.get("frs") or ()),
                         c.get("file")) for c in daten["testcases"]], pfad
    return None
