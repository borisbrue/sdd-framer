"""Suite-Arten des Benchmarks (SPEC-0056 FR-02 bis FR-04, CON-0223), Template Method.

Jede Aufgabe folgt `prepare` → `run` → `measure` → `teardown` in einem frischen temporären
Verzeichnis. Suite-Arten melden sich über `@register(kind)` an; `sdd bench run` findet sie über
`kind` (OCP). `roles` misst mit den Rollen-Evals (`q_kind: eval`), `regen` mit Tests und Gates
(`q_kind: quality`).
"""
from __future__ import annotations

import ast
import io
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .. import __version__
from ..config import SddConfig
from .config import CLAUDE_PROVIDERS, CONFIG, Assignment, BenchError, Matrix, Suite, overlay
from .meter import Meter

DEFAULT_WEIGHTS = {"requirements": 0.5, "architecture": 0.25, "code_quality": 0.25}
REPO_MAP_LIMIT = 300


@dataclass
class Job:
    """Ein Lauf: Suite, Belegung (oder Rolle × Profil) und Wiederholung."""

    suite: Suite
    run_id: str
    assignment: str
    roles: dict[str, str]
    repetition: int
    params: dict = field(default_factory=dict)  # suite-spezifisch, z. B. task oder role/profile


class BenchTask:
    """Fester Ablauf; Unterklassen implementieren nur die Hooks."""

    q_kind = "quality"

    def __init__(self, config: SddConfig, matrix: Matrix, job: Job, artifacts: Path) -> None:
        self.config, self.matrix, self.job, self.artifacts = config, matrix, job, artifacts
        self.meter = Meter(max_tokens=matrix.budget.get("max_tokens"),
                           max_claude_tokens=matrix.budget.get("max_claude_tokens"))
        self.workspace: Path | None = None

    # Template Method
    def execute(self) -> dict:
        start = time.monotonic()
        self.workspace = Path(tempfile.mkdtemp(prefix="sdd-bench-"))
        ausgang, fehler, messung = "completed", None, {}
        try:
            self.prepare(self.workspace)
            self.run(self.workspace)
            messung = self.measure(self.workspace)
        except BenchError:
            raise
        except Exception as exc:  # Endpunkt weg, Werkzeug fehlt: Ausgang error, Lauf zählt
            ausgang, fehler = "error", f"{type(exc).__name__}: {exc}"
        finally:
            self.teardown(self.workspace)
        if self.meter.exceeded and ausgang == "completed":
            ausgang = "halted: budget"
        return self.record(ausgang, fehler, messung, int((time.monotonic() - start) * 1000))

    def prepare(self, workspace: Path) -> None:
        return None

    def run(self, workspace: Path) -> None:
        raise NotImplementedError

    def measure(self, workspace: Path) -> dict:
        raise NotImplementedError

    def teardown(self, workspace: Path) -> None:
        shutil.rmtree(workspace, ignore_errors=True)

    # Record (CON-0222)
    def bindings(self) -> dict[str, dict]:
        return {}

    def record(self, ausgang: str, fehler: str | None, messung: dict, dauer: int) -> dict:
        tokens = {r: t.to_dict() for r, t in self.meter.tokens.items()}
        rollen = self.bindings()
        for rolle, modell in self.meter.server_models.items():
            if rolle in rollen:
                rollen[rolle]["server_model"] = modell
        claude_rollen = {r for r, b in rollen.items() if b.get("provider") in CLAUDE_PROVIDERS}
        daten = {"kind": "bench-record", "run_id": self.job.run_id, "suite": self.job.suite.name,
                 "suite_kind": self.job.suite.kind,
                 "suite_version": str(self.job.suite.data.get("version", "")),
                 "q_kind": self.q_kind, "assignment": self.job.assignment, "roles": rollen,
                 "repetition": self.job.repetition, "outcome": ausgang, "Q": None,
                 "tokens": tokens,
                 "T_in": sum(t["input"] for t in tokens.values()),
                 "T_out": sum(t["output"] for t in tokens.values()),
                 "T_reason": sum(t["reasoning"] for t in tokens.values()),
                 "T_claude": sum(t["input"] + t["output"] for r, t in tokens.items()
                                 if r in claude_rollen),
                 "estimated": any(t["estimated"] for t in tokens.values()),
                 "duration_ms": dauer, "sdd_version": __version__,
                 "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                 "artifacts": str(self.artifacts), **self.defaults(), **messung}
        if fehler:
            daten["error"] = fehler
        return daten

    def defaults(self) -> dict:
        return {}


REGISTRY: dict[str, type[BenchTask]] = {}


def register(kind: str):
    def deko(cls: type[BenchTask]) -> type[BenchTask]:
        REGISTRY[kind] = cls
        return cls
    return deko


def task_class(kind: str) -> type[BenchTask]:
    if kind not in REGISTRY:
        raise BenchError(f"Unbekannte Suite-Art {kind!r} (bekannt: {', '.join(sorted(REGISTRY))}).")
    return REGISTRY[kind]


def _binding_info(cfg: SddConfig, role: str, ref: str) -> dict:
    from ..pipeline.facade import role_binding
    from ..pipeline.roles import load_role

    rolle = load_role(cfg.root, role)
    b = role_binding(cfg, rolle)
    return {"profile": ref, "provider": b.provider, "model": b.model,
            "params": {k: v for k, v in b.params.items()}, "server_model": None,
            "endpoint": b.base_url, "role_version": rolle.version}


# ── Suite roles (FR-03) ──────────────────────────────────────────────────────

@register("roles")
class RolesTask(BenchTask):
    q_kind = "eval"

    def run(self, workspace: Path) -> None:
        from ..pipeline.evals.cases import list_cases, role_home
        from ..pipeline.evals.report import build_report
        from ..pipeline.evals.runner import EvalRunner, setup

        rolle, ref = self.job.params["role"], self.job.params["profile"]
        cfg = overlay(self.config, self.matrix, {rolle: ref})
        faelle = list_cases(role_home(self.config.root, rolle))
        if not faelle:
            raise BenchError(f"Rolle {rolle} hat keine Golden Cases.")
        st = setup(cfg, rolle, profile=ref, version=None,
                   with_rubric=any(f.rubric for f in faelle))
        runs = int(self.job.suite.data.get("runs", 1))
        ergebnisse = EvalRunner(cfg, st, wrap=self.meter.wrap).run(faelle, runs)
        self.report = build_report(st, ergebnisse, runs=runs, include_holdout=False,
                                   role_file=None).to_dict()
        self.artifacts.mkdir(parents=True, exist_ok=True)
        (self.artifacts / "eval-report.json").write_text(
            json.dumps(self.report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self._cfg = cfg

    def measure(self, workspace: Path) -> dict:
        total, holdout = self.report["total"], self.report["holdout"]
        return {"Q": total["mean"], "pass_at_1": total["pass_at_1"],
                "pass_all": total["pass_all"], "holdout_Q": holdout.get("mean")}

    def defaults(self) -> dict:
        return {"role": self.job.params["role"], "profile": self.job.params["profile"],
                "pass_at_1": None, "pass_all": None}

    def bindings(self) -> dict[str, dict]:
        rolle, ref = self.job.params["role"], self.job.params["profile"]
        cfg = getattr(self, "_cfg", None) or overlay(self.config, self.matrix, {rolle: ref})
        return {rolle: _binding_info(cfg, rolle, ref)}


# ── Suite regen (FR-04) ──────────────────────────────────────────────────────

def _archive(project: Path, commit: str, include: list[str], ziel: Path) -> None:
    befehl = ["git", "-C", str(project), "archive", "--format=tar", commit, *include]
    r = subprocess.run(befehl, capture_output=True)
    if r.returncode != 0:
        raise BenchError(f"git archive {commit}: {r.stderr.decode(errors='replace').strip()}")
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tar:
        tar.extractall(ziel, filter="data")


def _junit(pfad: Path) -> tuple[int, int] | None:
    if not pfad.is_file():
        return None
    try:
        wurzel = ET.parse(pfad).getroot()
    except ET.ParseError:
        return None
    faelle = list(wurzel.iter("testcase"))
    rot = [c for c in faelle if c.find("failure") is not None or c.find("error") is not None]
    uebersprungen = [c for c in faelle if c.find("skipped") is not None]
    gesamt = len(faelle) - len(uebersprungen)
    return gesamt - len(rot), gesamt


@register("regen")
class RegenTask(BenchTask):
    q_kind = "quality"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.meter.rate_limit = True
        self.attempts = 0
        self.failed = 0
        self.test_result: tuple[int, int] = (0, 0)
        self.written: list[str] = []

    @property
    def task(self) -> dict:
        return self.job.params["task"]

    def prepare(self, workspace: Path) -> None:
        daten = self.job.suite.data
        projekt = (self.config.root / daten.get("project", ".")).resolve()
        _archive(projekt, daten["commit"], list(daten.get("include") or []), workspace)
        modul = workspace / self.task["module"]
        if not modul.is_file():
            raise BenchError(f"Modul {self.task['module']} fehlt am Commit {daten['commit']}.")
        quelle = modul.read_text(encoding="utf-8")
        try:
            self.purpose = ast.get_docstring(ast.parse(quelle)) or ""
        except SyntaxError:
            self.purpose = ""
        self.reference = quelle  # Proxy: bleibt außerhalb jedes Rollenkontexts
        modul.unlink()

    def _command(self, workspace: Path, junit: Path) -> str:
        return str(self.job.suite.data["test_command"]).format(
            python=sys.executable, tests=" ".join(self.task["tests"]), junit=str(junit))

    def _tests(self, workspace: Path) -> tuple[bool, str, tuple[int, int] | None]:
        junit = workspace / ".bench-junit.xml"
        junit.unlink(missing_ok=True)
        zeitlimit = int(self.job.suite.data.get("timeout_seconds", 600))
        try:
            r = subprocess.run(self._command(workspace, junit), shell=True, cwd=workspace,
                               capture_output=True, text=True, timeout=zeitlimit)
            ausgabe, ok = (r.stdout + r.stderr)[-4000:], r.returncode == 0
        except subprocess.TimeoutExpired:
            ausgabe, ok = f"Zeitlimit {zeitlimit} s überschritten", False
        return ok, ausgabe, _junit(junit)

    def run(self, workspace: Path) -> None:
        from ..pipeline.facade import role_provider, run_role
        from ..pipeline.roles import load_role

        cfg = overlay(self.config, self.matrix, self.job.roles)
        self._cfg = cfg
        rolle = load_role(cfg.root, "implementer")
        provider = self.meter.wrap(role_provider(cfg, rolle), self._binding(cfg, rolle),
                                   "implementer")
        modul = self.task["module"]
        tests = "\n\n".join(f"# {t}\n{(workspace / t).read_text(encoding='utf-8')}"
                            for t in self.task["tests"] if (workspace / t).is_file())
        dateien = sorted(str(p.relative_to(workspace)) for p in workspace.rglob("*")
                         if p.is_file())
        task = {"id": "R01", "title": f"Modul {modul} neu schreiben",
                "description": self.purpose or f"Stelle {modul} so her, dass die Tests grün sind.",
                "type": "code", "complexity": "medium", "fr_ids": ["FR-01"], "dependencies": [],
                "test_file": self.task["tests"][0], "test_command": self.job.suite.data[
                    "test_command"], "allowed_paths": [modul]}
        rueckmeldung: list[str] = []
        ausgabe = ""
        for versuch in range(1, int(self.job.suite.data.get("attempts", 2)) + 1):
            if self.meter.exceeded:
                break
            self.attempts = versuch
            sources = {"task": task, "test_file": tests, "test_output": ausgabe or None,
                       "repo_map": "\n".join(dateien[:REPO_MAP_LIMIT]),
                       "history": rueckmeldung}
            ergebnis = run_role(rolle, provider, sources, run_id=self.job.run_id,
                                attempt=versuch, params=self._binding(cfg, rolle).params,
                                check_context={"task": task}, task=task)
            for f in (ergebnis.output or {}).get("files", []):
                if f["path"] == modul:
                    ziel = workspace / modul
                    ziel.parent.mkdir(parents=True, exist_ok=True)
                    ziel.write_text(f["content"], encoding="utf-8")
                    self.written = [modul]
            ok, ausgabe, zaehlung = self._tests(workspace)
            self.test_result = zaehlung or ((1, 1) if ok else (0, 1))
            if ok:
                break
            self.failed += 1
            rueckmeldung = [f"Versuch {versuch}: Tests rot", *ergebnis.problems[:3]]
        self.artifacts.mkdir(parents=True, exist_ok=True)
        if (workspace / modul).is_file():
            shutil.copy2(workspace / modul, self.artifacts / Path(modul).name)
        (self.artifacts / "test-output.txt").write_text(ausgabe, encoding="utf-8")

    @staticmethod
    def _binding(cfg: SddConfig, rolle: Any) -> Any:
        from ..pipeline.facade import role_binding

        return role_binding(cfg, rolle)

    def measure(self, workspace: Path) -> dict:
        from ..pipeline.facade import measure_changed

        gruen, gesamt = self.test_result
        q_req = gruen / gesamt if gesamt else 0.0
        q_arch = q_code = None
        if self.written:
            gates = measure_changed(workspace, self._cfg.raw, self.written)
            arch, lint = gates["architecture"], gates["lint"]
            q_arch = None if arch["status"] == "n/a" else (1.0 if arch["status"] == "ok" else 0.0)
            if lint["status"] != "n/a":
                q_code = 1.0 if lint["status"] == "ok" else max(0.0,
                                                               1 - 0.2 * len(lint["findings"]))
        gewichte = {**DEFAULT_WEIGHTS, **(self.job.suite.data.get("weights") or {})}
        teile = {"requirements": q_req, "architecture": q_arch, "code_quality": q_code}
        vorhanden = {k: v for k, v in teile.items() if v is not None and gewichte.get(k)}
        summe = sum(gewichte[k] for k in vorhanden)
        q = sum(gewichte[k] * v for k, v in vorhanden.items()) / summe if summe else None
        return {"Q": None if q is None else round(q, 4), "Q_req": round(q_req, 4),
                "Q_arch": q_arch, "Q_code": q_code, "frs_total": gesamt, "frs_met": gruen,
                "attempts": self.attempts, "failed_attempts": self.failed,
                "task": self.task["module"]}

    def defaults(self) -> dict:
        return {"task": self.task["module"], "Q_req": None, "Q_arch": None, "Q_code": None,
                "frs_total": 0, "frs_met": 0, "attempts": self.attempts,
                "failed_attempts": self.failed, "git_sha": self.job.suite.data.get("commit")}

    def bindings(self) -> dict[str, dict]:
        cfg = getattr(self, "_cfg", None) or overlay(self.config, self.matrix, self.job.roles)
        ref = self.job.roles.get("implementer", CONFIG)
        return {"implementer": _binding_info(cfg, "implementer", ref)}


def jobs_for(suite: Suite, matrix: Matrix, *, only: str | None = None,
             repetitions: int | None = None,
             allowed: dict[str, set[str]] | None = None) -> tuple[list[Job], list[str]]:
    """Läufe einer Suite; `allowed` filtert Belegungen nach dem Stufenmodell (FR-05)."""
    wdh = repetitions or matrix.repetitions
    jobs: list[Job] = []
    gefiltert: list[str] = []
    if suite.kind == "roles":
        rollen = suite.data.get("roles") or ["decomposer", "test_author", "implementer",
                                              "reviewer", "supervisor"]
        for rolle in rollen:
            for ref in matrix.profile_refs:
                for n in range(1, wdh + 1):
                    rid = f"{suite.name}-{rolle}-{ref.replace('@', '-')}-r{n}"
                    jobs.append(Job(suite, rid, f"{rolle}:{ref}", {rolle: ref}, n,
                                    {"role": rolle, "profile": ref}))
        return jobs, gefiltert
    belegungen: list[Assignment] = [a for a in matrix.assignments if not only or a.name == only]
    for a in belegungen:
        if allowed and any(ref not in allowed.get(rolle, {ref}) for rolle, ref in a.roles.items()
                           if ref != CONFIG):
            gefiltert.append(a.name)
            continue
        for t in suite.data.get("tasks") or [{}]:
            for n in range(1, wdh + 1):
                modul = str(t.get("module", "")).replace("/", "_").removesuffix(".py")
                rid = f"{suite.name}-{a.name}-{modul}-r{n}" if modul else \
                    f"{suite.name}-{a.name}-r{n}"
                jobs.append(Job(suite, rid, a.name, a.roles, n, {"task": t}))
    return jobs, gefiltert
