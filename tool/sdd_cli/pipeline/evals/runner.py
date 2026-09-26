"""Eval-Ablauf je Fall und Lauf (SPEC-0055 FR-04, CON-0219 INV-03), Template Method.

Fester Ablauf: Arbeitsverzeichnis anlegen und `input/repo/` kopieren → Rolle ausführen (RoleRunner,
mit Nonce) → Ausgabe anwenden → Checks → Rubrik (Rolle `judge`) → Arbeitsverzeichnis entfernen.
Rollenspezifisch sind nur die Hooks `sources`, `check_context` und `apply` (`RoleHooks`). Das
Projektverzeichnis wird nie verändert.
"""
from __future__ import annotations

import json
import secrets
import shutil
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ...compliance import extract_fr_ids
from ...llm.usage import usage_context
from ..checks import CheckEnv, CheckResult, fail, overlay, run_check, write_files
from ..providers import (
    RoleBinding,
    build_provider,
    profile_binding,
    profiles,
    resolve_binding,
)
from ..roles import CONTEXT_SOURCES, RoleDefinition, load_role
from ..runner import RoleRunner
from ..schemas import errors as schema_errors
from .cases import Case

if TYPE_CHECKING:
    from ...config import SddConfig

JUDGE_FORMAT = ('Antworte ausschließlich mit JSON: {"scores": {"<id>": <1-5>, ...}, '
                '"begruendung": "<ein Satz>"}')


class EvalError(Exception):
    """Profil, Rolle oder Kandidatendatei unbrauchbar."""


# ── Eingaben eines Falls ─────────────────────────────────────────────────────

def read_inputs(case: Case) -> dict[str, Any]:
    """Kontextquellen aus `input/<quelle>.<ext>`; JSON/YAML wird geparst. `request` ist die
    Entscheidungsanfrage des Supervisors, `repo/` das Arbeitsverzeichnis."""
    quellen: dict[str, Any] = {}
    ordner = case.dir / "input"
    for datei in sorted(p for p in ordner.iterdir() if p.is_file()):
        text = datei.read_text(encoding="utf-8")
        if datei.suffix == ".json":
            quellen[datei.stem] = json.loads(text)
        elif datei.suffix in (".yaml", ".yml"):
            import yaml

            quellen[datei.stem] = yaml.safe_load(text)
        else:
            quellen[datei.stem] = text
    repo = ordner / "repo"
    if "repo_map" not in quellen and repo.is_dir():
        quellen["repo_map"] = "\n".join(sorted(str(p.relative_to(repo)) for p in repo.rglob("*")
                                               if p.is_file()))
    return quellen


# ── Rollen-Hooks (Template Method) ───────────────────────────────────────────

class RoleHooks:
    """Standard: Quellen durchreichen, Task als Kontext, nichts schreiben."""

    def lead(self, inputs: dict) -> str:
        return ""

    def sources(self, inputs: dict) -> dict:
        return {k: v for k, v in inputs.items() if k in CONTEXT_SOURCES}

    def check_context(self, inputs: dict) -> dict:
        return {"task": inputs.get("task") or {}}

    def apply(self, output: Any, workspace: Path) -> list[str]:
        return []

    def rubric_text(self, output: Any) -> str:
        return json.dumps(output, ensure_ascii=False, indent=2)


class DecomposerHooks(RoleHooks):
    def check_context(self, inputs: dict) -> dict:
        return {"spec_frs": extract_fr_ids(str(inputs.get("spec") or ""))}


class TestAuthorHooks(RoleHooks):
    def rubric_text(self, output: Any) -> str:
        return f"{output.get('test_file')}\n\n{output.get('content')}"


class ImplementerHooks(RoleHooks):
    def apply(self, output: Any, workspace: Path) -> list[str]:
        dateien = [(f["path"], f["content"]) for f in (output or {}).get("files", [])]
        write_files(workspace, dateien)
        return [p for p, _ in dateien]


class SupervisorHooks(RoleHooks):
    def lead(self, inputs: dict) -> str:
        anfrage = inputs.get("request") or {}
        return "## Anfrage\n\n" + json.dumps(anfrage, ensure_ascii=False, indent=2)

    def check_context(self, inputs: dict) -> dict:
        return {}


HOOKS: dict[str, RoleHooks] = {"decomposer": DecomposerHooks(), "test_author": TestAuthorHooks(),
                               "implementer": ImplementerHooks(), "reviewer": RoleHooks(),
                               "supervisor": SupervisorHooks()}


# ── Ergebnisse ───────────────────────────────────────────────────────────────

@dataclass
class RunResult:
    run: int
    score: float
    passed: bool
    checks: list[dict]
    rubric: dict[str, int]
    tokens: dict
    duration_ms: int
    error: str | None = None

    def to_dict(self) -> dict:
        d = {"run": self.run, "score": round(self.score, 4), "passed": self.passed,
             "checks": self.checks, "rubric": self.rubric, "tokens": self.tokens,
             "duration_ms": self.duration_ms}
        if self.error:
            d["error"] = self.error
        return d


@dataclass
class CaseRuns:
    case: Case
    runs: list[RunResult] = field(default_factory=list)


def _tokens(usage: Any) -> dict:
    if usage is None or getattr(usage, "source", "") == "unavailable":
        return {"input_tokens": None, "output_tokens": None, "reasoning_tokens": None}
    return {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
            "reasoning_tokens": usage.reasoning_tokens}


def case_score(case: Case, checks: list[CheckResult], rubric: dict[str, int]) -> float:
    """Fall-Score nach CON-0217 INV-05; ohne Rubrikwerte zählen nur die Checks."""
    werte = [c.score for c in checks if c.score is not None]
    check_teil = sum(werte) / len(werte) if werte else 0.0
    w_checks, w_rubrik = case.weights
    if not rubric or w_rubrik == 0:
        return check_teil
    rubrik_teil = sum((v - 1) / 4 for v in rubric.values()) / len(rubric)
    return w_checks * check_teil + w_rubrik * rubrik_teil


class RateLimiter:
    """Mindestabstand zwischen Aufrufen je Endpunkt (`requests_per_minute`, FR-11)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._next: dict[tuple, float] = {}

    def wait(self, binding: RoleBinding) -> None:
        rpm = binding.params.get("requests_per_minute")
        if not rpm:
            return
        with self._lock:
            jetzt = time.monotonic()
            start = max(jetzt, self._next.get(binding.endpoint, 0.0))
            self._next[binding.endpoint] = start + 60.0 / float(rpm)
        if start > jetzt:
            time.sleep(start - jetzt)


# ── Eval ─────────────────────────────────────────────────────────────────────

@dataclass
class EvalSetup:
    role_def: RoleDefinition
    binding: RoleBinding
    profile_name: str
    judge_def: RoleDefinition | None
    judge_binding: RoleBinding | None
    warnings: list[str]


def candidate_role(path: Path, role: str) -> RoleDefinition:
    """Rollendatei aus `--version DATEI`, geprüft wie eine Rolle (CON-0199)."""
    from ..roles import RoleError, load_role_file

    if not path.is_file():
        raise EvalError(f"Kandidat {path} fehlt")
    try:
        rolle = load_role_file(path, role)
    except RoleError as exc:
        raise EvalError(f"Kandidat {path}: {exc}") from exc
    return RoleDefinition(**{**rolle.__dict__, "source": path.resolve()})


def setup(config: SddConfig, role: str, *, profile: str | None, version: Path | None,
          with_rubric: bool) -> EvalSetup:
    from ..providers import RoleConfigError
    from ..roles import RoleError

    try:
        role_def = candidate_role(version, role) if version else load_role(config.root, role)
        if profile:
            if profile not in profiles(config):
                raise EvalError(f"Profil {profile!r} fehlt in llm.profiles.")
            binding = profile_binding(config, role, profile)
        else:
            binding = resolve_binding(config, role_def)
    except (RoleError, RoleConfigError) as exc:
        raise EvalError(str(exc)) from exc
    if binding.is_session:
        raise EvalError(f"Rolle {role} ist im Modus session belegt; Evals brauchen ein Modell "
                        f"(--model PROFIL).")
    warnungen: list[str] = []
    judge_def = judge_binding = None
    if with_rubric:
        try:
            judge_def = load_role(config.root, "judge")
            judge_binding = resolve_binding(config, judge_def)
        except (RoleError, RoleConfigError) as exc:
            warnungen.append(f"Rubrik ohne Judge: {exc}")
        if judge_binding is not None and judge_binding.endpoint == binding.endpoint:
            warnungen.append("Judge und bewertetes Profil nutzen denselben Endpunkt "
                             f"({binding.provider} {binding.model}).")
    return EvalSetup(role_def, binding, profile or "config", judge_def, judge_binding,
                     warnungen)


class EvalRunner:
    def __init__(self, config: SddConfig, st: EvalSetup, *, eval_id: str | None = None,
                 concurrency: int = 2) -> None:
        self.config = config
        self.st = st
        self.eval_id = eval_id or f"eval-{secrets.token_hex(4)}"
        self.concurrency = max(1, concurrency)
        self.hooks = HOOKS.get(st.role_def.role, RoleHooks())
        self.limiter = RateLimiter()
        self._provider = build_provider(config, st.binding, st.role_def)
        self._judge = (build_provider(config, st.judge_binding, st.judge_def)
                       if st.judge_def and st.judge_binding else None)

    def run(self, cases: list[Case], runs: int) -> list[CaseRuns]:
        ergebnisse = {c.id: CaseRuns(c) for c in cases}
        jobs = [(c, n) for c in cases for n in range(1, runs + 1)]
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            for case, lauf in zip(jobs, pool.map(lambda job: self.run_once(*job), jobs),
                                  strict=True):
                ergebnisse[case[0].id].runs.append(lauf)
        for r in ergebnisse.values():
            r.runs.sort(key=lambda x: x.run)
        return list(ergebnisse.values())

    # Template Method: fester Ablauf, Hooks je Rolle
    def run_once(self, case: Case, run: int) -> RunResult:
        start = time.monotonic()
        workspace = Path(tempfile.mkdtemp(prefix=f"sdd-eval-{case.id}-"))
        try:
            inputs = read_inputs(case)
            if (case.dir / "input" / "repo").is_dir():
                overlay(case.dir / "input" / "repo", workspace)
            with usage_context(origin="role-eval", eval_id=self.eval_id, case_id=case.id):
                self.limiter.wait(self.st.binding)
                ergebnis = RoleRunner(run_id=self.eval_id, spec_id="").run(
                    self.st.role_def, self._provider, self.hooks.sources(inputs), attempt=run,
                    params=self.st.binding.params, lead=self.hooks.lead(inputs),
                    check_context=self.hooks.check_context(inputs),
                    task=inputs.get("task") if isinstance(inputs.get("task"), dict) else None)
            tokens = _tokens(ergebnis.usage)
            output = ergebnis.output
            if output is None:
                grund = "; ".join(ergebnis.problems) or "keine Ausgabe"
                return self._failed(case, run, grund, tokens, start)
            name, definition = self.st.role_def.schema_ref()
            schema = schema_errors(name, output, definition)
            if schema:
                return self._failed(case, run, "Ausgabe verletzt das Schema: " + schema[0],
                                    tokens, start)
            geschrieben = self.hooks.apply(output, workspace)
            checks = self._checks(case, output, inputs, workspace, geschrieben)
            rubrik = self._rubric(case, output) if case.rubric else {}
            return RunResult(run, case_score(case, [c for _, c in checks], rubrik),
                             not any(c.failed for _, c in checks),
                             [c.to_dict(n) for n, c in checks], rubrik, tokens,
                             int((time.monotonic() - start) * 1000))
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def _failed(self, case: Case, run: int, grund: str, tokens: dict, start: float) -> RunResult:
        checks = [fail([grund]).to_dict(n) for n, _ in case.checks]
        return RunResult(run, 0.0, False, checks, {}, tokens,
                         int((time.monotonic() - start) * 1000), error=grund)

    def _checks(self, case: Case, output: Any, inputs: dict, workspace: Path,
                written: list[str]) -> list[tuple[str, CheckResult]]:
        ctx = self.hooks.check_context(inputs)
        return [(name, run_check(name, CheckEnv(
            output=output, ctx=ctx, params=params, case_dir=case.dir, workspace=workspace,
            test_command=case.test_command, timeout=case.timeout, written=written)))
            for name, params in case.checks]

    def _rubric(self, case: Case, output: Any) -> dict[str, int]:
        """Blinde Bewertung (CON-0219 INV-07): nur Fragen und Ausgabe, kein Modell, keine Version."""
        if self._judge is None or self.st.judge_def is None or self.st.judge_binding is None:
            return {}
        fragen = "\n".join(f"- {r['id']}: {r['question']}" for r in case.rubric)
        lead = (f"Bewerte die folgende Ausgabe nach diesen Kriterien, jeweils 1 (schlecht) bis "
                f"5 (sehr gut):\n{fragen}\n\n{JUDGE_FORMAT}")
        with usage_context(origin="role-eval", eval_id=self.eval_id, case_id=case.id,
                           judged_role=self.st.role_def.role):
            self.limiter.wait(self.st.judge_binding)
            ergebnis = RoleRunner(run_id=self.eval_id, spec_id="").run(
                self.st.judge_def, self._judge, {"diff": self.hooks.rubric_text(output)},
                attempt=1, params=self.st.judge_binding.params, lead=lead)
        werte = (ergebnis.output or {}).get("scores") if ergebnis.ok else None
        if not isinstance(werte, dict):
            return {}
        ids = {r["id"] for r in case.rubric}
        return {k: int(v) for k, v in werte.items() if k in ids and isinstance(v, int)
                and 1 <= v <= 5}
