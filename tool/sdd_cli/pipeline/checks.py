"""Check-Registry für Rollen-Gates und Rollen-Evals (SPEC-0055 FR-03, CON-0219 INV-01/02).

Strategy: Jeder Check ist eine benannte Funktion `check(env) -> CheckResult` mit Deklaration der
Kontexte (`gate`, `eval`), der benötigten Fall-Bestandteile und eines Parameterschemas. Das
Pipeline-Gate (SPEC-0053) nutzt nur Checks mit Kontext `gate`, die ohne Fall auskommen; die Evals
nutzen alle. Ausführungsbasierte Checks starten den `test_command` des Falls in einem
Arbeitsverzeichnis, sprachneutral und mit Zeitlimit.
"""
from __future__ import annotations

import fnmatch
import json
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

GATE = "gate"
EVAL = "eval"
COMPLEXITY_ORDER = ("low", "medium", "high")
DEFAULT_TIMEOUT = 120


@dataclass(frozen=True)
class CheckResult:
    status: str  # pass | fail | n/a
    score: float | None
    details: list[str] = field(default_factory=list)

    @property
    def failed(self) -> bool:
        return self.status == "fail"

    def to_dict(self, name: str) -> dict:
        return {"name": name, "status": self.status, "score": self.score,
                "details": self.details[:20]}


def ok(score: float = 1.0) -> CheckResult:
    return CheckResult("pass", score)


def fail(details: list[str], score: float = 0.0) -> CheckResult:
    return CheckResult("fail", score, details)


def na(reason: str) -> CheckResult:
    return CheckResult("n/a", None, [reason])


def _from_problems(probleme: list[str]) -> CheckResult:
    return fail(probleme) if probleme else ok()


@dataclass
class CheckEnv:
    """Alles, was ein Check sehen darf: Ausgabe, Kontext und – im Eval – den Fall."""

    output: Any
    ctx: Mapping = field(default_factory=dict)
    params: Mapping = field(default_factory=dict)
    case_dir: Path | None = None
    workspace: Path | None = None
    test_command: str | None = None
    timeout: int = DEFAULT_TIMEOUT
    written: list[str] = field(default_factory=list)

    def part(self, name: str) -> Path | None:
        if self.case_dir is None:
            return None
        pfad = self.case_dir / name
        return pfad if pfad.exists() else None

    def expected(self, name: str) -> Any:
        pfad = self.part("expected")
        datei = pfad / name if pfad else None
        return json.loads(datei.read_text(encoding="utf-8")) if datei and datei.is_file() else None


@dataclass(frozen=True)
class CheckSpec:
    name: str
    func: Callable[[CheckEnv], CheckResult]
    contexts: frozenset[str]
    requires: tuple[str, ...] = ()
    params: Mapping = field(default_factory=dict)  # JSON-Schema-Properties der Parameter
    executes: bool = False

    def param_errors(self, params: Any) -> list[str]:
        schema = {"type": "object", "additionalProperties": False, "properties": dict(self.params)}
        return [f"{self.name}: {e.message}" for e in Draft202012Validator(schema).iter_errors(
            params if params is not None else {})]


# ── Ausführung im Arbeitsverzeichnis ─────────────────────────────────────────

@dataclass(frozen=True)
class CommandResult:
    code: int | None
    output: str
    timed_out: bool = False

    @property
    def passed(self) -> bool:
        return self.code == 0 and not self.timed_out


def run_command(command: str, cwd: Path, timeout: int) -> CommandResult:
    try:
        r = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        ausgabe = exc.stdout if isinstance(exc.stdout, str) else ""
        return CommandResult(None, ausgabe, timed_out=True)
    return CommandResult(r.returncode, (r.stdout + r.stderr)[-4000:])


def overlay(src: Path, dst: Path) -> None:
    """Kopiert `src` rekursiv über `dst` (bestehende Dateien werden ersetzt)."""
    for datei in sorted(p for p in src.rglob("*") if p.is_file()):
        ziel = dst / datei.relative_to(src)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(datei, ziel)


def write_files(root: Path, files: list[tuple[str, str]]) -> None:
    for rel, inhalt in files:
        ziel = root / rel
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(inhalt, encoding="utf-8")


class _Scratch:
    """Frisches Arbeitsverzeichnis aus `input/repo/`, optional mit Referenz und Dateien."""

    def __init__(self, env: CheckEnv, *, reference: bool, files: list[tuple[str, str]]):
        self.env, self.reference, self.files = env, reference, files
        self.dir: Path | None = None

    def __enter__(self) -> Path:
        self.dir = Path(tempfile.mkdtemp(prefix="sdd-check-"))
        repo = self.env.part("input/repo")
        if repo:
            overlay(repo, self.dir)
        if self.reference and (ref := self.env.part("reference")):
            overlay(ref, self.dir)
        write_files(self.dir, self.files)
        return self.dir

    def __exit__(self, *exc: object) -> None:
        if self.dir:
            shutil.rmtree(self.dir, ignore_errors=True)


def _test_run(env: CheckEnv, cwd: Path) -> CommandResult | CheckResult:
    if not env.test_command:
        return na("Fall ohne test_command")
    return run_command(env.test_command, cwd, env.timeout)


def _timeout(r: CommandResult, env: CheckEnv) -> CheckResult | None:
    return fail([f"Zeitlimit {env.timeout} s überschritten"]) if r.timed_out else None


def _test_file(env: CheckEnv) -> list[tuple[str, str]]:
    out = env.output or {}
    return [(out["test_file"], out["content"])] if out.get("test_file") else []


# ── decomposer ───────────────────────────────────────────────────────────────

def _tasks(env: CheckEnv) -> list[dict]:
    return list((env.output or {}).get("tasks", []))


def _fr_coverage(env: CheckEnv) -> CheckResult:
    frs = list(env.ctx.get("spec_frs", []))
    if not frs:
        return ok()
    abgedeckt = {fr for t in _tasks(env) for fr in t.get("fr_ids", [])}
    fehlend = [fr for fr in frs if fr not in abgedeckt]
    anteil = (len(frs) - len(fehlend)) / len(frs)
    if anteil >= float(env.params.get("min", 1.0)):
        return ok(anteil)
    return fail([f"{fr} ist von keinem Task abgedeckt" for fr in fehlend], anteil)


def _deps_resolvable(env: CheckEnv) -> CheckResult:
    titel = {t["title"] for t in _tasks(env)}
    return _from_problems([f"Task {t['title']!r}: Abhängigkeit {d!r} existiert nicht"
                           for t in _tasks(env) for d in t.get("dependencies", [])
                           if d not in titel])


def _acyclic(env: CheckEnv) -> CheckResult:
    kanten = {t["title"]: list(t.get("dependencies", [])) for t in _tasks(env)}
    zustand: dict[str, int] = {}

    def zyklisch(knoten: str) -> bool:
        if zustand.get(knoten) == 1:
            return True
        if zustand.get(knoten) == 2 or knoten not in kanten:
            return False
        zustand[knoten] = 1
        if any(zyklisch(n) for n in kanten[knoten]):
            return True
        zustand[knoten] = 2
        return False

    return (fail(["Die Abhängigkeiten der Tasks enthalten einen Zyklus"])
            if any(zyklisch(k) for k in kanten) else ok())


def _test_file_per_code_task(env: CheckEnv) -> CheckResult:
    gesehen: dict[str, str] = {}
    probleme = []
    for t in _tasks(env):
        datei = t.get("test_file")
        if t.get("type") == "code" and datei:
            if datei in gesehen:
                probleme.append(f"Tasks {gesehen[datei]!r} und {t['title']!r} teilen die "
                                f"Testdatei {datei}")
            gesehen[datei] = t["title"]
    return _from_problems(probleme)


def _task_count(env: CheckEnv) -> CheckResult:
    n = len(_tasks(env))
    unten, oben = env.params.get("min"), env.params.get("max")
    if unten is not None and n < unten:
        return fail([f"{n} Tasks, erwartet mindestens {unten}"])
    if oben is not None and n > oben:
        return fail([f"{n} Tasks, erwartet höchstens {oben}"])
    return ok()


def _index(tasks: list[dict], muster: str) -> int | None:
    import re

    return next((i for i, t in enumerate(tasks) if re.search(muster, t["title"], re.IGNORECASE)),
                None)


def _ordered_before(env: CheckEnv) -> CheckResult:
    tasks = _tasks(env)
    erst, dann = _index(tasks, env.params["first"]), _index(tasks, env.params["then"])
    if erst is None or dann is None:
        fehlt = env.params["first"] if erst is None else env.params["then"]
        return fail([f"kein Task passt zu {fehlt!r}"])
    return ok() if erst < dann else fail(
        [f"{tasks[dann]['title']!r} steht vor {tasks[erst]['title']!r}"])


def _max_complexity(env: CheckEnv) -> CheckResult:
    grenze = COMPLEXITY_ORDER.index(env.params["value"])
    zu_gross = [t["title"] for t in _tasks(env)
                if COMPLEXITY_ORDER.index(t.get("complexity", "low")) > grenze]
    return _from_problems([f"Task {t!r} ist komplexer als {env.params['value']}"
                           for t in zu_gross])


# ── test_author ──────────────────────────────────────────────────────────────

def _test_file_matches_task(env: CheckEnv) -> CheckResult:
    erwartet = (env.ctx.get("task") or {}).get("test_file")
    ist = (env.output or {}).get("test_file")
    if erwartet and ist != erwartet:
        return fail([f"test_file muss {erwartet} sein, nicht {ist}"])
    return ok()


def _fr_marker_present(env: CheckEnv) -> CheckResult:
    frs = list((env.ctx.get("task") or {}).get("fr_ids", []))
    inhalt = (env.output or {}).get("content", "")
    fehlend = [fr for fr in frs if fr not in inhalt]
    return _from_problems([f"Test nennt {fr} nicht" for fr in fehlend])


def _red_against_stub(env: CheckEnv) -> CheckResult:
    with _Scratch(env, reference=False, files=_test_file(env)) as ws:
        r = _test_run(env, ws)
    if isinstance(r, CheckResult):
        return r
    if r.timed_out:
        return fail([f"Zeitlimit {env.timeout} s überschritten"])
    return fail(["Test ist gegen den Stub grün"]) if r.passed else ok()


def _green_against_reference(env: CheckEnv) -> CheckResult:
    with _Scratch(env, reference=True, files=_test_file(env)) as ws:
        r = _test_run(env, ws)
    if isinstance(r, CheckResult):
        return r
    return _timeout(r, env) or (ok() if r.passed else fail(
        ["Test ist gegen die Referenzlösung rot", r.output[-1500:]]))


def _mutation_kill_rate(env: CheckEnv) -> CheckResult:
    patches = sorted((env.part("mutants") or Path("/nonexistent")).glob("*.patch"))
    if not patches:
        return na("keine Mutanten")
    getoetet, ueberlebt = 0, []
    for patch in patches:
        with _Scratch(env, reference=True, files=_test_file(env)) as ws:
            angewandt = run_command(f"git apply --unsafe-paths {json.dumps(str(patch))}", ws, 30)
            if not angewandt.passed:
                return fail([f"Mutant {patch.name} lässt sich nicht anwenden: "
                             f"{angewandt.output[-300:]}"])
            r = _test_run(env, ws)
        if isinstance(r, CheckResult):
            return r
        if r.passed:
            ueberlebt.append(patch.name)
        else:
            getoetet += 1
    quote = getoetet / len(patches)
    if quote >= float(env.params.get("min", 1.0)):
        return ok(quote)
    return fail([f"Mutant {m} überlebt" for m in ueberlebt], quote)


# ── implementer ──────────────────────────────────────────────────────────────

def _paths_allowed(env: CheckEnv) -> CheckResult:
    task = env.ctx.get("task") or {}
    erlaubt = list(task.get("allowed_paths") or [])
    verboten = {task.get("test_file")} - {None}
    probleme = []
    for f in (env.output or {}).get("files", []):
        pfad = f["path"]
        if pfad in verboten or pfad.startswith(".sdd/") or not any(
                fnmatch.fnmatch(pfad, m) for m in erlaubt):
            probleme.append(f"{pfad} liegt außerhalb von allowed_paths")
    return _from_problems(probleme)


def _hidden_tests_pass(env: CheckEnv) -> CheckResult:
    versteckt = env.part("hidden")
    if env.workspace is None or versteckt is None:
        return na("kein Arbeitsverzeichnis oder keine versteckten Tests")
    overlay(versteckt, env.workspace)
    r = _test_run(env, env.workspace)
    if isinstance(r, CheckResult):
        return r
    return _timeout(r, env) or (ok() if r.passed else fail(
        ["versteckte Tests sind rot", r.output[-1500:]]))


def _arch_violations(env: CheckEnv) -> CheckResult:
    if env.workspace is None or not (env.workspace / ".sdd/architecture.yaml").is_file():
        return na("Fall ohne .sdd/architecture.yaml")
    from .gates import architecture_gate

    ergebnis = architecture_gate(env.workspace, {}, list(env.written))
    if ergebnis.status == "n/a":
        return na(ergebnis.reason)
    return ok() if ergebnis.status == "ok" else fail(ergebnis.findings or [ergebnis.reason])


def _quality_score(env: CheckEnv) -> CheckResult:
    if env.workspace is None or not (env.workspace / ".sdd/quality.yaml").is_file():
        return na("Fall ohne .sdd/quality.yaml")
    from ..quality.measure import measure

    try:
        wert = measure(env.workspace).report.get("score")
    except Exception as exc:  # Messung ist optional; jeder Fehler macht den Check n/a
        return na(f"Messung fehlgeschlagen: {exc}")
    if wert is None:
        return na("kein Gesamtscore")
    return ok(wert) if wert >= float(env.params.get("min", 0.0)) else fail(
        [f"Qualitätsscore {wert:.2f} unter {env.params['min']}"], wert)


# ── reviewer ─────────────────────────────────────────────────────────────────

def _findings(env: CheckEnv) -> list[dict]:
    return list((env.output or {}).get("findings", []))


def _seeded_bug_recall(env: CheckEnv) -> CheckResult:
    erwartet = (env.expected("findings.json") or {}).get("bugs") or []
    if not erwartet:
        return na("keine erwarteten Befunde")
    toleranz = int(env.params.get("tolerance", 3))

    def gefunden(bug: dict) -> bool:
        for f in _findings(env):
            if f.get("file") != bug["file"]:
                continue
            zeile = f.get("line")
            if bug.get("line") and zeile and abs(zeile - bug["line"]) <= toleranz:
                return True
            if any(w.lower() in f.get("reason", "").lower() for w in bug.get("keywords", [])):
                return True
        return False

    verpasst = [b for b in erwartet if not gefunden(b)]
    quote = (len(erwartet) - len(verpasst)) / len(erwartet)
    probleme = [f"Fehler in {b['file']}:{b.get('line', '?')} nicht gefunden" for b in verpasst]
    if (env.output or {}).get("verdict") != "fail":
        probleme.append("Urteil ist nicht fail")
    if quote >= float(env.params.get("min", 1.0)) and (env.output or {}).get("verdict") == "fail":
        return ok(quote)
    return fail(probleme, quote)


def _clean_diff_precision(env: CheckEnv) -> CheckResult:
    befunde = _findings(env)
    if (env.output or {}).get("verdict") == "pass" and not befunde:
        return ok()
    return fail([f"Fehlalarm: {f.get('file')}: {f.get('reason')}" for f in befunde]
                or ["Urteil ist fail ohne Befund"], 1 / (1 + len(befunde)))


# ── supervisor ───────────────────────────────────────────────────────────────

def _decision_matches(env: CheckEnv) -> CheckResult:
    erwartet = env.expected("decision.json") or {}
    ist = env.output or {}
    probleme = [f"{k}: {ist.get(k)!r} statt {v!r}" for k, v in erwartet.items()
                if k in ("point", "command", "task_id") and ist.get(k) != v]
    if "task_ids" in erwartet and sorted(ist.get("task_ids") or []) != sorted(
            erwartet["task_ids"]):
        probleme.append(f"task_ids: {ist.get('task_ids')!r} statt {erwartet['task_ids']!r}")
    return _from_problems(probleme)


def _reason_mentions(env: CheckEnv) -> CheckResult:
    begriffe = list(env.params.get("terms", []))
    if not begriffe:
        return na("keine Begriffe")
    text = str((env.output or {}).get("reason", "")).lower()
    fehlend = [b for b in begriffe if b.lower() not in text]
    anteil = (len(begriffe) - len(fehlend)) / len(begriffe)
    genug = not fehlend if env.params.get("all", True) else anteil > 0
    return ok(anteil) if genug else fail([f"Begründung nennt {b!r} nicht" for b in fehlend],
                                         anteil)


# ── Registry ─────────────────────────────────────────────────────────────────

_BEIDE = frozenset({GATE, EVAL})
_EVAL = frozenset({EVAL})
_ZAHL = {"type": "number", "minimum": 0, "maximum": 1}
_INT = {"type": "integer", "minimum": 0}

REGISTRY: dict[str, CheckSpec] = {s.name: s for s in (
    CheckSpec("json_schema", lambda env: ok(), _BEIDE),  # läuft vorab, s. RoleRunner._validate
    CheckSpec("fr_coverage", _fr_coverage, _BEIDE, params={"min": _ZAHL}),
    CheckSpec("acyclic", _acyclic, _BEIDE),
    CheckSpec("deps_resolvable", _deps_resolvable, _BEIDE),
    CheckSpec("test_file_per_code_task", _test_file_per_code_task, _BEIDE),
    CheckSpec("test_file_matches_task", _test_file_matches_task, _BEIDE),
    CheckSpec("task_count", _task_count, _EVAL, params={"min": _INT, "max": _INT}),
    CheckSpec("ordered_before", _ordered_before, _EVAL,
              params={"first": {"type": "string"}, "then": {"type": "string"}}),
    CheckSpec("max_complexity", _max_complexity, _EVAL,
              params={"value": {"enum": list(COMPLEXITY_ORDER)}}),
    CheckSpec("fr_marker_present", _fr_marker_present, _BEIDE),
    CheckSpec("red_against_stub", _red_against_stub, _EVAL, executes=True),
    CheckSpec("green_against_reference", _green_against_reference, _EVAL, ("reference",),
              executes=True),
    CheckSpec("mutation_kill_rate", _mutation_kill_rate, _EVAL, ("reference", "mutants"),
              params={"min": _ZAHL}, executes=True),
    CheckSpec("paths_allowed", _paths_allowed, _BEIDE),
    CheckSpec("hidden_tests_pass", _hidden_tests_pass, _EVAL, ("hidden",), executes=True),
    CheckSpec("arch_violations", _arch_violations, _EVAL),
    CheckSpec("quality_score", _quality_score, _EVAL, params={"min": _ZAHL}),
    CheckSpec("seeded_bug_recall", _seeded_bug_recall, _EVAL, ("expected",),
              params={"min": _ZAHL, "tolerance": _INT}),
    CheckSpec("clean_diff_precision", _clean_diff_precision, _EVAL),
    CheckSpec("decision_matches", _decision_matches, _EVAL, ("expected",)),
    CheckSpec("reason_mentions", _reason_mentions, _EVAL,
              params={"terms": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                      "all": {"type": "boolean"}}),
)}

# Parameter ohne sinnvollen Default; ein Fall muss sie setzen.
REQUIRED_PARAMS = {"ordered_before": ("first", "then"), "max_complexity": ("value",),
                   "reason_mentions": ("terms",)}


def unknown_checks(checks: list[str] | tuple[str, ...]) -> list[str]:
    return [c for c in checks if c not in REGISTRY]


def not_gate_capable(checks: list[str] | tuple[str, ...]) -> list[str]:
    return [c for c in checks if c in REGISTRY and GATE not in REGISTRY[c].contexts]


def check_errors(name: str, params: Any, available: set[str], *,
                 has_test_command: bool) -> list[str]:
    """Fehler eines Check-Eintrags in `case.yaml` (CON-0217 INV-03/04)."""
    spec = REGISTRY.get(name)
    if spec is None:
        return [f"unbekannter Check {name!r}"]
    fehler = spec.param_errors(params)
    fehler += [f"{name}: Parameter {p!r} fehlt" for p in REQUIRED_PARAMS.get(name, ())
               if p not in (params or {})]
    fehler += [f"{name}: Fall braucht {teil}/" for teil in spec.requires if teil not in available]
    if spec.executes and not has_test_command:
        fehler.append(f"{name}: Fall braucht test_command")
    return fehler


def gate_problems(checks: tuple[str, ...], output: Any, ctx: Mapping) -> tuple[list[str],
                                                                                   list[str]]:
    """Gate der Pipeline: (Probleme, Namen der gescheiterten Checks)."""
    probleme: list[str] = []
    gescheitert: list[str] = []
    for name in checks:
        spec = REGISTRY.get(name)
        if spec is None:
            probleme.append(f"unbekannter Rollen-Check {name!r}")
            gescheitert.append(name)
            continue
        if GATE not in spec.contexts:
            probleme.append(f"Rollen-Check {name!r} ist im Gate nicht nutzbar")
            gescheitert.append(name)
            continue
        ergebnis = spec.func(CheckEnv(output=output, ctx=ctx))
        if ergebnis.failed:
            probleme.extend(ergebnis.details)
            gescheitert.append(name)
    return probleme, gescheitert


def run_check(name: str, env: CheckEnv) -> CheckResult:
    spec = REGISTRY.get(name)
    if spec is None:
        return fail([f"unbekannter Check {name!r}"])
    return spec.func(env)
