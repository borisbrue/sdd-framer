"""PipelineSupervisor: Mediator der Rollen-Pipeline (SPEC-0053 FR-08 bis FR-15, CON-0205).

Die Rollen kennen einander nicht. Der Mediator steuert den Ablauf als fortsetzbaren
Zustandsautomaten (`state.json` nach jedem Übergang), reicht Artefakte weiter, wendet die
PathPolicy auf jeden Schreibvorgang an und holt an S1 bis S3 eine Entscheidung ein. Der
Supervisor liefert nur Commands; ausgeführt werden sie hier.

SPEC-0061: Arbeitsrollen können im Modus `session` laufen (Auftrag in `pending-work.json`,
Bestätigung mit `sdd pipeline done`); für alle Modi gilt derselbe Rollenvertrag (CON-0213 INV-01).
Belegungen hängen optional von der Komplexität des Tasks ab, Gates laufen pro Task, und
`--auto` führt die Abschluss-Kette aus (CON-0214).
"""
from __future__ import annotations

import difflib
import hashlib
import json
import secrets
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .. import __version__
from ..gate import ExecutionGate
from . import budget as budget_mod
from . import gates as task_gates_mod
from . import steps as auto_steps_mod
from .context import ContextError, ProjectContext
from .decisions import Answer, Pending, SessionSource, new_request, validate_command
from .path_policy import PathPolicy
from .providers import (
    SAME_MODEL_WARNING,
    SESSION,
    RoleBinding,
    RoleConfigError,
    all_bindings,
    build_provider,
    profile_binding,
    resolve_binding,
    same_model_conflict,
    supervisor_mode,
)
from .roles import DEFAULT_ROLES, RoleDefinition, RoleError, load_role
from .runner import RoleResult, RoleRunner
from .store import RunStore, now

if TYPE_CHECKING:
    from ..config import SddConfig

MAX_REVISIONS = 2
MAX_ATTEMPTS = 3
MAX_REOPEN = 2
WRITING_ROLES = ("test_author", "implementer")
JSON_ROLES = ("decomposer", "reviewer")  # Session-Ergebnis kommt als --json (FR-02)
SNAPSHOT_EXCLUDE = ["**/node_modules/**", "**/__pycache__/**", "**/.venv/**"]
COMPLEXITY_SIZE = {"low": ("S", 2000), "medium": ("M", 5000), "high": ("L", 10000)}


class PipelineError(Exception):
    """Vorbedingung verletzt oder Run unbekannt (Exit 2)."""


@dataclass
class RunOutcome:
    exit_code: int
    message: str
    run_id: str = ""


@dataclass
class _TaskMemory:
    """Rückmeldungen innerhalb eines Laufs; Hinweise des Supervisors stehen in decisions.jsonl."""
    feedback: list[str] = field(default_factory=list)
    test_output: str = ""
    review: Any = None
    diff: str = ""
    changed: list[str] = field(default_factory=list)


class InlineSource:
    """Die Supervisor-Rolle antwortet über ihren Provider (FR-15 `inline`)."""

    name = "inline"

    def __init__(self, mediator: PipelineSupervisor) -> None:
        self.mediator = mediator

    def decide(self, request: dict, *, attempt: int) -> Answer | Pending:
        m = self.mediator
        role_def = m.role("supervisor")
        binding = m.binding("supervisor")
        vorne = {"task_id": request["task_id"]} if request.get("task_id") else {}
        lead = "## Anfrage\n\n" + json.dumps({**vorne, **request}, ensure_ascii=False, indent=2)
        sources = {"spec": m.ctx.spec_text, "history": m.decision_history()}
        ergebnis = m.runner.run(role_def, m.provider(binding, role_def), sources, attempt=attempt,
                                params=binding.params, lead=lead)
        m.log_role_call(ergebnis, binding, task_id=request.get("task_id"))
        if ergebnis.outcome == "error":
            return Answer(None, raw="; ".join(ergebnis.problems), call_id=ergebnis.call_id,
                          outcome="error")
        command = ergebnis.output if ergebnis.output is not None else ergebnis.raw
        return Answer(command, raw=ergebnis.raw, call_id=ergebnis.call_id,
                      outcome=ergebnis.outcome)


class PipelineSupervisor:
    def __init__(self, config: SddConfig, store: RunStore, *,
                 notify: Callable[[str], None] | None = None,
                 max_tasks: int | None = None) -> None:
        self.config = config
        self.store = store
        self.ctx = ProjectContext(config.root, store.spec_id)
        self.runner = RoleRunner(run_id=store.run_id, spec_id=store.spec_id)
        self.policy = PathPolicy.from_config(config.root, config.raw)
        self.notify = notify or (lambda _msg: None)
        self.max_tasks = max_tasks
        pipeline = config.raw.get("pipeline") or {}
        self.max_revisions = int(pipeline.get("max_revisions", MAX_REVISIONS))
        self.max_attempts = int(pipeline.get("max_attempts", MAX_ATTEMPTS))
        self.max_reopen = int(pipeline.get("max_reopen", MAX_REOPEN))
        self.state: dict = {}
        self._roles: dict[str, RoleDefinition] = {}
        self._memory: dict[str, _TaskMemory] = {}
        self._decomposer_feedback: list[str] = []

    # ── Einstieg ─────────────────────────────────────────────────────────────
    @classmethod
    def start(cls, config: SddConfig, spec_id: str, *, dry_run: bool = False,
              max_tasks: int | None = None, task_id: str | None = None, auto: bool = False,
              base_url: str | None = None, session: tuple[str, ...] | list[str] = (),
              steps: list[str] | None = None, run_id: str | None = None,
              budget: dict | None = None,
              notify: Callable[[str], None] | None = None) -> RunOutcome:
        cls._check_run_options(session, steps, auto)
        budget_fehler = [*budget_mod.option_errors(budget or {}),
                         *(m for _, _, m in budget_mod.issues(config.raw))]
        if budget_fehler:
            raise PipelineError("Budget ungültig: " + "; ".join(budget_fehler))
        ctx = ProjectContext(config.root, spec_id)
        try:
            status = ctx.status
        except ContextError as exc:
            raise PipelineError(str(exc)) from exc
        if status != "approved":
            raise PipelineError(f"{spec_id} hat Status {status!r}; erwartet 'approved'.")
        if not ExecutionGate(config.root).is_phase_complete(spec_id, "execute-unlocked"):
            raise PipelineError(f"{spec_id}: Gate-Phase execute-unlocked fehlt "
                                f"(sdd spec approve {spec_id}).")
        roles, warnings = cls._check_roles(config)
        if task_id and (auto or dry_run):
            raise PipelineError("--task lässt sich nicht mit --auto oder --dry-run kombinieren.")
        if task_id:
            from ..decompose import TaskDecomposer

            ids = {t.id for t in TaskDecomposer().load(spec_id, config)}
            if not ids:
                raise PipelineError(f"{spec_id}: keine gespeicherte Zerlegung "
                                    f"(.sdd/tasks/{spec_id}.json); erst sdd pipeline run --dry-run.")
            if task_id not in ids:
                raise PipelineError(f"{spec_id}: Task {task_id} gibt es nicht "
                                    f"(vorhanden: {', '.join(sorted(ids))}).")
        try:
            store = RunStore.create(config.root, spec_id, run_id)
        except (ValueError, FileExistsError) as exc:
            raise PipelineError(f"Run-ID {run_id}: {exc}") from exc
        optionen = {"dry_run": dry_run, "max_tasks": max_tasks}
        if task_id:
            optionen["task"] = task_id
        if auto:
            optionen.update(auto=True, base_url=base_url)
        if steps is not None:
            optionen["steps"] = list(steps)
        if budget and any(v is not None for v in budget.values()):
            optionen["budget"] = {k: v for k, v in budget.items() if v is not None}
        if session:
            optionen["session"] = sorted(set(session))
            for rolle in optionen["session"]:
                roles[rolle] = {"mode": SESSION, "source": "--session",
                                "role_version": roles[rolle]["role_version"]}
        store.write_run({"run_id": store.run_id, "spec_id": spec_id, "started_at": now(),
                         "sdd_version": __version__, "options": optionen,
                         "roles": roles, "warnings": warnings})
        m = cls(config, store, notify=notify, max_tasks=max_tasks)
        m.state = {"run_id": store.run_id, "status": "running", "phase": "decompose",
                   "revisions": 0, "tasks": [], "pending_request_id": None}
        if task_id:
            m.state.update(phase="tasks",
                           tasks=[{"task_id": task_id, "state": "pending", "attempts": 0}])
        m.save()
        for w in warnings:
            store.event("warning", detail={"message": w})
            m.notify(f"⚠ {w}")
        return m.advance()

    @staticmethod
    def _check_run_options(session: tuple[str, ...] | list[str], steps: list[str] | None,
                           auto: bool) -> None:
        """Run-Optionen `--session` und `--steps` (SPEC-0062 FR-01, CON-0216 INV-01/02)."""
        unbekannt = sorted(set(session) - set(DEFAULT_ROLES))
        if unbekannt:
            raise PipelineError(f"--session: unbekannte Rolle {', '.join(unbekannt)} "
                                f"(bekannt: {', '.join(DEFAULT_ROLES)}).")
        if steps is None:
            return
        if not auto:
            raise PipelineError("--steps gilt nur zusammen mit --auto.")
        falsch = [s for s in steps if s not in auto_steps_mod.DEFAULT_AUTO_STEPS]
        if falsch:
            raise PipelineError(f"--steps: unbekannter Schritt {', '.join(falsch)} "
                                f"(erlaubt: {', '.join(auto_steps_mod.DEFAULT_AUTO_STEPS)}).")

    @classmethod
    def resume(cls, config: SddConfig, run_id: str, *, max_tasks: int | None = None,
               notify: Callable[[str], None] | None = None) -> RunOutcome:
        m = cls._open(config, run_id, notify=notify, max_tasks=max_tasks)
        status = m.state["status"]
        if status == "awaiting_supervisor":
            return RunOutcome(3, "Wartet auf eine Entscheidung (sdd pipeline decide).", run_id)
        if status == "awaiting_session":
            return RunOutcome(3, "Wartet auf die Session (sdd pipeline done).", run_id)
        if status in ("halted", "failed"):
            return RunOutcome(1, f"Run ist {status}.", run_id)
        if status == "completed":
            return RunOutcome(0, "Run ist bereits abgeschlossen.", run_id)
        return m.advance()

    @classmethod
    def decide(cls, config: SddConfig, run_id: str, command: Any, *,
               notify: Callable[[str], None] | None = None) -> RunOutcome:
        m = cls._open(config, run_id, notify=notify)
        request = m.store.read_pending()
        if not m.state.get("pending_request_id") or request is None \
                or request.get("request_id") != m.state["pending_request_id"]:
            raise PipelineError(f"Run {run_id} hat keine offene Entscheidungsanfrage.")
        fehler = validate_command(command, request, m.task_ids())
        m.log_decision(request, command, source="session", errors=fehler)
        if fehler:
            raise PipelineError("Command ungültig: " + "; ".join(fehler))
        m.close_request(request)
        m.state["status"] = "running"
        m.save()
        stopp = m.apply(request, command)
        return stopp or m.advance()

    @classmethod
    def done(cls, config: SddConfig, run_id: str, output: Any = None, *,
             notify: Callable[[str], None] | None = None) -> RunOutcome:
        """Schließt den offenen Session-Auftrag ab und setzt den Run fort (FR-02, CON-0213)."""
        m = cls._open(config, run_id, notify=notify)
        auftrag = m.store.read_work()
        if m.state.get("status") != "awaiting_session" or auftrag is None:
            raise PipelineError(f"Run {run_id} hat keinen offenen Session-Auftrag.")
        rolle = auftrag["role"]
        role_def = m.role(rolle)
        if rolle in JSON_ROLES:
            if output is None:
                raise PipelineError(f"Rolle {rolle}: --json mit der Ausgabe ist Pflicht.")
            kontext = ({"spec_frs": m.ctx.spec_frs} if rolle == "decomposer" else
                       {"task": m._load_tasks().get(auftrag.get("task_id") or "", {})})
            fehler = RoleRunner._validate(role_def, output, kontext)
            if fehler:
                raise PipelineError("Ausgabe ungültig: " + "; ".join(fehler[:5]))
        m.store.archive_work(auftrag["request_id"])
        m.state["status"] = "running"
        m.save()
        stopp = m._continue_session(auftrag, output)
        return stopp or m.advance()

    @classmethod
    def _open(cls, config: SddConfig, run_id: str, **kw: Any) -> PipelineSupervisor:
        from .store import RunNotFound

        try:
            store = RunStore.open(config.root, run_id)
        except RunNotFound as exc:
            raise PipelineError(str(exc)) from exc
        m = cls(config, store, **kw)
        m.state = store.read_state()
        return m

    @staticmethod
    def _check_roles(config: SddConfig) -> tuple[dict, list[str]]:
        roles: dict[str, dict] = {}
        for rolle in DEFAULT_ROLES:
            try:
                role_def = load_role(config.root, rolle)
                binding = resolve_binding(config, role_def)
                all_bindings(config, role_def)  # unbekannte Profile verhindern den Start
            except (RoleError, RoleConfigError, RuntimeError) as exc:
                raise PipelineError(str(exc)) from exc
            eintrag = {**binding.describe(), "role_version": role_def.version}
            if rolle == "supervisor":
                eintrag["mode"] = supervisor_mode(config)
            roles[rolle] = eintrag
        warnings = [SAME_MODEL_WARNING] if same_model_conflict(config) else []
        return roles, warnings

    # ── Zustand und Protokoll ────────────────────────────────────────────────
    def save(self) -> None:
        self.store.write_state(self.state)

    def transition(self, *, to: str, frm: str | None = None, task_id: str | None = None,
                   role: str | None = None, reason: str | None = None) -> None:
        self.store.event("transition", task_id=task_id, role=role, to=to,
                         detail={"reason": reason} if reason else None, **{"from": frm})

    def role(self, name: str) -> RoleDefinition:
        if name not in self._roles:
            self._roles[name] = load_role(self.config.root, name)
        return self._roles[name]

    def binding(self, name: str, task_state: dict | None = None,
                task: dict | None = None) -> RoleBinding:
        """Belegung eines Aufrufs (CON-0213 INV-04): --session → reassign → by_complexity → Rolle
        → Legacy."""
        if name in self.session_roles():
            return profile_binding(self.config, name, SESSION)
        modell = ((task_state or {}).get("assignment") or {}).get(name)
        if modell:
            return resolve_binding(self.config, self.role(name)).with_model(modell)
        return resolve_binding(self.config, self.role(name), (task or {}).get("complexity"))

    def task_ids(self) -> set[str]:
        return {t["task_id"] for t in self.state.get("tasks", [])}

    def options(self) -> dict:
        return self.store.read_run().get("options") or {}

    def session_roles(self) -> set[str]:
        return set(self.options().get("session") or ())

    def auto_steps(self) -> list[str]:
        """`--steps` des Runs, sonst `pipeline.auto_steps` (CON-0216 INV-02)."""
        schritte = self.options().get("steps")
        return list(schritte) if schritte is not None else auto_steps_mod.auto_steps(
            self.config.raw)

    def provider(self, binding: RoleBinding, role_def: RoleDefinition) -> Any:
        return budget_mod.GuardedProvider(build_provider(self.config, binding, role_def),
                                          self._halted_by_budget)

    # Budget (SPEC-0063 FR-01, CON-0225) ─────────────────────────────────────
    def _halted_by_budget(self) -> bool:
        return bool(self.state.get("budget_halt"))

    def check_budget(self) -> None:
        """Nach einem Rollenaufruf: Budget überschritten → Run hält (INV-03)."""
        if self.state.get("status") != "running" or self._halted_by_budget():
            return
        run = self.store.read_run()
        grenzen = budget_mod.limits(self.config.raw, (run.get("options") or {}).get("budget"))
        if not grenzen:
            return
        stand = budget_mod.usage(self.config.root, self.store.run_id,
                                 budget_mod.claude_roles(run.get("roles") or {}))
        grenze = budget_mod.exceeded(grenzen, stand)
        if grenze:
            self.state["budget_halt"] = grenze
            self.halt(budget_mod.REASON, limit=grenze, **stand)

    def log_role_call(self, ergebnis: RoleResult, binding: RoleBinding, *,
                      task_id: str | None = None, outcome: str | None = None,
                      detail: dict | None = None) -> None:
        info = {"model": binding.model, "provider": binding.provider}
        if ergebnis.problems:
            info["problems"] = ergebnis.problems[:10]
        if ergebnis.failed_checks:
            info["failed_checks"] = ergebnis.failed_checks  # Quelle für `sdd role case capture`
        self.store.event("role_call", task_id=task_id, role=ergebnis.role,
                         call_id=ergebnis.call_id, attempt=ergebnis.attempt,
                         outcome=outcome or ergebnis.outcome, prompt_hash=ergebnis.prompt_hash,
                         detail={**info, **(detail or {})})
        self.check_budget()

    def log_decision(self, request: dict, command: Any, *, source: str,
                     errors: list[str]) -> None:
        eintrag = {"request_id": request["request_id"], "point": request["point"],
                   "source": source, "valid": not errors,
                   "command": command if isinstance(command, dict) else {"raw": str(command)}}
        if errors:
            eintrag["error"] = "; ".join(errors)
        self.store.decision(eintrag)

    def decisions(self) -> list[dict]:
        return self.store.read_jsonl("decisions.jsonl")

    def decision_history(self, task_id: str | None = None) -> list[str]:
        """Bisherige gültige Entscheidungen als Text; mit task_id nur Hinweise für den Task."""
        zeilen = []
        for d in self.decisions():
            c = d.get("command") or {}
            if not d.get("valid"):
                continue
            if task_id is not None:
                if c.get("command") == "retry_with_hint" and c.get("task_id") == task_id:
                    zeilen.append(f"Hinweis des Supervisors: {c['hint']}")
                elif c.get("command") == "reopen" and task_id in c.get("task_ids", []):
                    zeilen.append(f"Nach der Abnahme wieder geöffnet: {c['hint']}")
                continue
            zeilen.append(f"{c.get('point')} {c.get('command')}: {c.get('reason')}")
        return zeilen

    def usage_totals(self) -> dict:
        db = self.config.root / ".sdd" / "evaluations.db"
        if not db.is_file():
            return {}
        with sqlite3.connect(db) as con:
            zeile = con.execute(
                "SELECT COALESCE(SUM(input_tokens),0), COALESCE(SUM(output_tokens),0), "
                "COALESCE(SUM(reasoning_tokens),0), COUNT(*) FROM token_usage "
                "WHERE run_id = ?", (self.store.run_id,)).fetchone()
        return {"input_tokens": zeile[0], "output_tokens": zeile[1],
                "reasoning_tokens": zeile[2], "calls": zeile[3]}

    # ── Entscheidungen ───────────────────────────────────────────────────────
    def source(self) -> Any:
        if "supervisor" in self.session_roles() or supervisor_mode(self.config) == SESSION:
            return SessionSource()
        return InlineSource(self)

    def ask(self, request: dict) -> dict | RunOutcome:
        """Anfrage persistieren, Quelle fragen, validieren (CON-0202 INV-02, CON-0205 INV-03)."""
        request.setdefault("facts", {}).setdefault("tokens", self.usage_totals())
        self.store.write_pending(request)
        self.state["pending_request_id"] = request["request_id"]
        self.save()
        quelle = self.source()
        for versuch in (1, 2):
            antwort = quelle.decide(request, attempt=versuch)
            if isinstance(antwort, Pending):
                self.state["status"] = "awaiting_supervisor"
                self.save()
                return RunOutcome(3, f"{request['point']}: Entscheidung erforderlich "
                                     f"(sdd pipeline decide {self.store.run_id} --json …).",
                                  self.store.run_id)
            fehler = validate_command(antwort.command, request, self.task_ids())
            self.log_decision(request, antwort.command, source=quelle.name, errors=fehler)
            if not fehler:
                self.close_request(request)
                self.save()
                return antwort.command
            self.notify(f"⚠ Ungültige Entscheidung an {request['point']}: {'; '.join(fehler)}")
        self.close_request(request)
        return self.halt("zweite ungültige Entscheidung", point=request["point"])

    def close_request(self, request: dict) -> None:
        self.store.archive_pending(request["request_id"])
        self.state["pending_request_id"] = None

    def halt(self, reason: str, **detail: Any) -> RunOutcome:
        self.state["status"] = "halted"
        self.store.event("transition", to="halted", detail={"reason": reason, **detail},
                         **{"from": self.state.get("phase")})
        self.save()
        return RunOutcome(1, f"Run angehalten: {reason}", self.store.run_id)

    def apply(self, request: dict, command: dict) -> RunOutcome | None:
        """Führt ein gültiges Command aus (Command Pattern, FR-08)."""
        name = command["command"]
        self.store.event("decision", detail={"request_id": request["request_id"],
                                             "command": name})
        if name == "halt":
            return self.halt(command["reason"], point=request["point"])
        if name == "approve":
            return self._approve(request)
        if name == "revise":
            if self.state.get("revisions", 0) >= self.max_revisions:
                return self.halt(f"max_revisions ({self.max_revisions}) erreicht")
            self.state["revisions"] = self.state.get("revisions", 0) + 1
            self._decomposer_feedback = [f"Supervisor verlangt Überarbeitung: {command['reason']}"]
            self.save()
            return None
        if name == "redecompose":
            self.state.update(phase="decompose", tasks=[])
            self._decomposer_feedback = [f"Neuzerlegung verlangt: {command['reason']}"]
            self.transition(to="redecompose", task_id=request.get("task_id"),
                            reason=command["reason"])
            self.save()
            return None
        if name == "accept_frs":
            return self._accept(command)
        if name == "reopen":
            return self._reopen(command)
        task_state = self._task_state(command.get("task_id") or request.get("task_id"))
        if name == "retry_with_hint":
            task_state["attempts"] = 0
            self.transition(frm=task_state["state"], to="retry", task_id=task_state["task_id"],
                            reason=command["reason"])
        elif name == "reassign":
            task_state.setdefault("assignment", {})[command["role"]] = command["model"]
            task_state["attempts"] = 0
            self.transition(frm=task_state["state"], to="reassigned", role=command["role"],
                            task_id=task_state["task_id"], reason=command["reason"])
        self.save()
        return None

    # ── Ablauf ───────────────────────────────────────────────────────────────
    def advance(self) -> RunOutcome:
        while True:
            if self.state["status"] != "running":
                return self._outcome_for_status()
            phase = self.state["phase"]
            if phase == "decompose":
                stopp = self._decompose()
            elif phase == "tasks":
                stopp = self._tasks()
            elif phase == "acceptance":
                stopp = self._acceptance()
            elif phase == "finalize":
                stopp = self._finalize()
            else:
                return self._outcome_for_status()
            if stopp is not None:
                return stopp

    def _outcome_for_status(self) -> RunOutcome:
        status = self.state["status"]
        codes = {"completed": 0, "awaiting_supervisor": 3, "awaiting_session": 3, "halted": 1,
                 "failed": 1}
        return RunOutcome(codes.get(status, 0), f"Run ist {status}.", self.store.run_id)

    # Phase decompose ─────────────────────────────────────────────────────────
    def _decompose(self) -> RunOutcome | None:
        role_def = self.role("decomposer")
        binding = self.binding("decomposer")
        if binding.is_session:
            return self._request_work("decomposer", None, None, self._decomposer_feedback,
                                      {"spec": self._rel(self.ctx.spec_path),
                                       "agents_md": "AGENTS.md" if self.ctx.agents_md else None})
        provider = self.provider(binding, role_def)
        feedback = list(self._decomposer_feedback)
        ergebnis = None
        for versuch in range(1, self.max_attempts + 1):
            sources = {"spec": self.ctx.spec_text, "contracts": self.ctx.contracts_text,
                       "agents_md": self.ctx.agents_md, "repo_map": self.ctx.repo_map(),
                       "history": feedback}
            ergebnis = self.runner.run(role_def, provider, sources, attempt=versuch,
                                       params=binding.params,
                                       check_context={"spec_frs": self.ctx.spec_frs})
            self.log_role_call(ergebnis, binding)
            if ergebnis.ok:
                break
            feedback = [*self._decomposer_feedback,
                        *(f"Rollen-Check: {p}" for p in ergebnis.problems)]
            self.notify(f"  decomposer: Versuch {versuch} ungültig – {ergebnis.problems[:3]}")
        if ergebnis is None or not ergebnis.ok:
            return self.halt("Zerlegung nach max_attempts nicht gültig",
                             problems=(ergebnis.problems if ergebnis else [])[:10])
        return self._s1(ergebnis.output["tasks"])

    def _s1(self, tasks: list[dict]) -> RunOutcome | None:
        self.notify(f"  decomposer: {len(tasks)} Tasks")
        request = new_request("S1", {"tasks": tasks, "fr_coverage": self._fr_coverage(tasks)})
        antwort = self.ask(request)
        if isinstance(antwort, RunOutcome):
            return antwort
        return self.apply(request, antwort)

    def _fr_coverage(self, tasks: list[dict]) -> dict:
        return {fr: [t["title"] for t in tasks if fr in t.get("fr_ids", [])]
                for fr in self.ctx.spec_frs}

    def _approve(self, request: dict) -> RunOutcome | None:
        from ..decompose import TaskDecomposer

        roh = request["facts"]["tasks"]
        tasks = to_tasks(self.store.spec_id, roh, run_id=self.store.run_id)
        TaskDecomposer().save(tasks, self.config)
        self.state["tasks"] = [{"task_id": t.id, "state": "pending", "attempts": 0}
                               for t in topological(tasks)]
        self.transition(frm="decompose", to="tasks", reason="S1 approve")
        if self.store.read_run().get("options", {}).get("dry_run"):
            self.state.update(status="completed", phase="done")
            self.save()
            return RunOutcome(0, f"Dry-Run: {len(tasks)} Tasks freigegeben.", self.store.run_id)
        self.state["phase"] = "tasks"
        self.save()
        return None

    # Phase tasks ─────────────────────────────────────────────────────────────
    def _tasks(self) -> RunOutcome | None:
        tasks = self._load_tasks()
        bearbeitet = 0
        for task_state in self.state["tasks"]:
            if task_state["state"] == "done":
                continue
            if self.max_tasks is not None and bearbeitet >= self.max_tasks:
                self.save()
                return RunOutcome(0, f"Nach {bearbeitet} Task(s) pausiert; fortsetzen mit "
                                     f"--resume {self.store.run_id}.", self.store.run_id)
            stopp = self._work(task_state, tasks[task_state["task_id"]])
            if stopp is not None or self.state["phase"] != "tasks":
                return stopp
            bearbeitet += 1
        if self.options().get("task"):
            # --task: ein Task, ohne Abnahme und Abschluss (CON-0213 INV-07)
            self.state.update(status="completed", phase="done")
            self.transition(frm="tasks", to="done", reason="--task")
            self.save()
            return RunOutcome(0, f"Task {self.options()['task']} abgeschlossen.",
                              self.store.run_id)
        self.state["phase"] = "acceptance"
        self.transition(frm="tasks", to="acceptance")
        self.save()
        return None

    def _load_tasks(self) -> dict[str, dict]:
        from ..decompose import TaskDecomposer

        return {t.id: t.to_dict() for t in TaskDecomposer().load(self.store.spec_id, self.config)}

    def _task_state(self, task_id: str | None) -> dict:
        for t in self.state["tasks"]:
            if t["task_id"] == task_id:
                return t
        raise PipelineError(f"Task {task_id} gehört nicht zu diesem Run.")

    def _work(self, st: dict, task: dict) -> RunOutcome | None:
        mem = self._memory.setdefault(st["task_id"], _TaskMemory())
        typ = task.get("type") or "code"
        while st["state"] != "done":
            if st["state"] == "reviewed":
                self._set(st, "done")
                self.save()
                break
            if st["state"] == "pending" and typ in ("config", "doc"):
                # FR-06: config/doc brauchen keinen Test vorab.
                self._set(st, "red", reason=f"Task-Typ {typ}: ohne test_author")
                self.save()
                continue
            if st["attempts"] >= self.max_attempts:
                stopp = self._escalate(st, task, mem)
                if stopp is not None or self.state["phase"] != "tasks":
                    return stopp
                continue
            st["attempts"] += 1
            self.save()
            stopp = self._stage(st, task, mem)
            if stopp is not None:
                return stopp
        self.notify(f"  ✓ {task['id']} {task['title']}")
        return None

    def _role_for(self, st: dict) -> str:
        if st["state"] in ("pending", "retry", "reassigned"):
            return "test_author"
        return "implementer" if st["state"] == "red" else "reviewer"

    def _sources_for(self, role: str, task: dict, mem: _TaskMemory) -> dict:
        if role == "test_author":
            return self._sources(task, mem, test_output=mem.test_output)
        if role == "implementer":
            return self._sources(task, mem, repo_map=self.ctx.repo_map(),
                                 test_file=self.ctx.read(task.get("test_file") or "") or "",
                                 test_output=mem.test_output, review=mem.review)
        return self._sources(task, mem, diff=mem.diff or "(Diff nicht verfügbar)",
                             gate_results=[json.loads(mem.test_output)] if mem.test_output else [])

    def _stage(self, st: dict, task: dict, mem: _TaskMemory) -> RunOutcome | None:
        """Ein Versuch einer Arbeitsrolle; LLM sofort, Session über einen Auftrag (Strategy)."""
        rolle = self._role_for(st)
        binding = self.binding(rolle, st, task)
        sources = self._sources_for(rolle, task, mem)
        if binding.is_session:
            basis = None
            if rolle == "implementer" and (task.get("type") or "code") in ("config", "doc"):
                basis = self._failing()
            return self._request_work(rolle, st, task, mem.feedback[-6:], {
                "spec": self._rel(self.ctx.spec_path), "task": task,
                "test_file": task.get("test_file"), "test_output": mem.test_output or None,
                "review": mem.review, "diff": mem.diff or None,
                "history": self.decision_history(task_id=task["id"])}, failing=basis)
        role_def = self.role(rolle)
        basis = self._failing() if rolle == "implementer" and (
            task.get("type") or "code") in ("config", "doc") else None
        ergebnis = self.runner.run(role_def, self.provider(binding, role_def), sources,
                                   attempt=st["attempts"], params=binding.params,
                                   check_context={"task": task}, task=task)
        self._apply(rolle, st, task, mem, ergebnis, binding, baseline=basis)
        return None

    def _apply(self, rolle: str, st: dict, task: dict, mem: _TaskMemory, ergebnis: RoleResult,
               binding: RoleBinding, *, session_files: list[str] | None = None,
               baseline: list[str] | None = None) -> None:
        if rolle == "test_author":
            self._apply_test_author(st, task, mem, ergebnis, binding, session_files)
        elif rolle == "implementer":
            self._apply_implementer(st, task, mem, ergebnis, binding, session_files, baseline)
        else:
            self._apply_reviewer(st, task, mem, ergebnis, binding)

    def _set(self, st: dict, neu: str, reason: str | None = None) -> None:
        alt = st["state"]
        st["state"] = neu
        self.transition(frm=alt, to=neu, task_id=st["task_id"], reason=reason)

    def _escalate(self, st: dict, task: dict, mem: _TaskMemory) -> RunOutcome | None:
        request = new_request("S2", {"task": {k: task.get(k) for k in (
            "id", "title", "fr_ids", "test_file", "allowed_paths")}, "state": st["state"],
            "attempts": st["attempts"], "errors": mem.feedback[-6:],
            "gate_results": [{"probe": "tests", "output": mem.test_output[-2000:]}]
            if mem.test_output else []}, task_id=st["task_id"])
        antwort = self.ask(request)
        if isinstance(antwort, RunOutcome):
            return antwort
        mem.feedback.clear()
        return self.apply(request, antwort)

    def _sources(self, task: dict, mem: _TaskMemory, **extra: Any) -> dict:
        hinweise = self.decision_history(task_id=task["id"])
        return {"spec": self.ctx.spec_text, "contracts": self.ctx.contracts_text,
                "agents_md": self.ctx.agents_md, "task": task,
                "history": [*hinweise, *mem.feedback[-4:]], **extra}

    def _write(self, role: str, task: dict, files: list[dict],
               ergebnis: RoleResult) -> dict[str, str | None] | None:
        """Schreibt nach PathPolicy; None, wenn ein Pfad abgelehnt wurde (nichts geschrieben)."""
        abgelehnt = [(f["path"], e.reason) for f in files
                     if not (e := self.policy.check(role, f["path"], task)).allowed]
        if abgelehnt:
            self._log_rejected(role, task, abgelehnt, ergebnis.call_id)
            return None
        vorher: dict[str, str | None] = {}
        for f in files:
            ziel = self.config.root / f["path"]
            vorher[f["path"]] = ziel.read_text(encoding="utf-8") if ziel.is_file() else None
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_text(f["content"], encoding="utf-8")
        return vorher

    def _log_rejected(self, role: str, task: dict, abgelehnt: list[tuple[str, str | None]],
                      call_id: str) -> None:
        for pfad, grund in abgelehnt:
            self.store.event("write_rejected", role=role, task_id=task["id"],
                             detail={"path": pfad, "reason": grund, "call_id": call_id})

    def _check_session(self, role: str, task: dict, files: list[str], call_id: str,
                       mem: _TaskMemory) -> bool:
        """Rollenvertrag für Session-Dateien (CON-0213 INV-01); True, wenn alles erlaubt war."""
        abgelehnt = [(f, e.reason) for f in files
                     if not (e := self.policy.check(role, f, task)).allowed]
        if abgelehnt:
            self._log_rejected(role, task, abgelehnt, call_id)
            for pfad, grund in abgelehnt:
                mem.feedback.append(f"Bitte zurücksetzen: {pfad} ({grund}); erlaubt: "
                                    f"{task.get('allowed_paths') if role == 'implementer' else task.get('test_file')}")
        return not abgelehnt

    def _restore(self, vorher: dict[str, str | None] | None) -> None:
        for pfad, inhalt in (vorher or {}).items():
            ziel = self.config.root / pfad
            if inhalt is None:
                ziel.unlink(missing_ok=True)
            else:
                ziel.write_text(inhalt, encoding="utf-8")

    def _failing(self) -> list[str]:
        probe = self.ctx.run_tests()
        return [f"{c.classname}.{c.name}" for c in probe.failing()] if probe.ok else []

    def _apply_test_author(self, st: dict, task: dict, mem: _TaskMemory, ergebnis: RoleResult,
                           binding: RoleBinding, session_files: list[str] | None) -> None:
        outcome, detail = ergebnis.outcome, {}
        test_task = (task.get("type") or "code") == "test"
        if ergebnis.ok:
            vorher: dict[str, str | None] | None = {}
            if session_files is None:
                files = [{"path": ergebnis.output["test_file"],
                          "content": ergebnis.output["content"]}]
                vorher = self._write("test_author", task, files, ergebnis)
                if vorher is None:
                    mem.feedback.append(f"Schreibversuch abgelehnt: {files[0]['path']}")
            elif not self._check_session("test_author", task, session_files, ergebnis.call_id,
                                         mem):
                vorher = None
            if vorher is None:
                outcome = "gate_failed"
            else:
                probe = self.ctx.run_tests()
                faelle = probe.for_file(task["test_file"]) if probe.ok else []
                rot = [c for c in faelle if c.status in ("failed", "error")]
                bestanden = probe.ok and (bool(faelle) if test_task else bool(rot))
                if bestanden:
                    detail = {"gate": "red", "passed": True} if not test_task else \
                        {"gate": "test", "passed": True}
                    mem.test_output = json.dumps(probe.summary(), ensure_ascii=False)
                    st["attempts"] = 0
                    # FR-06: ein reiner Test-Task geht ohne Implementer zum Review.
                    self._set(st, "green" if test_task else "red")
                    if test_task:
                        mem.diff = self.ctx.read(task["test_file"]) or ""
                else:
                    if session_files is None:
                        self._restore(vorher)
                    outcome = "gate_failed"
                    grund = (probe.reason if not probe.ok else
                             "Test ist ohne Implementierung grün" if faelle else
                             "Testsonde meldet den neuen Test nicht")
                    detail = {"gate": "red", "passed": False, "reason": grund}
                    mem.feedback.append(f"RED-Gate: {grund}")
        else:
            mem.feedback.extend(ergebnis.problems[:3])
        self.log_role_call(ergebnis, binding, task_id=task["id"], outcome=outcome, detail=detail)
        self.save()

    def _apply_implementer(self, st: dict, task: dict, mem: _TaskMemory, ergebnis: RoleResult,
                           binding: RoleBinding, session_files: list[str] | None,
                           baseline: list[str] | None) -> None:
        outcome, detail = ergebnis.outcome, {}
        if ergebnis.ok:
            vorher: dict[str, str | None] | None
            if session_files is None:
                vorher = self._write("implementer", task, ergebnis.output["files"], ergebnis)
                geaendert = [f["path"] for f in ergebnis.output["files"]]
                if vorher is None:
                    mem.feedback.append("Schreibversuch außerhalb der erlaubten Pfade abgelehnt; "
                                        f"erlaubt: {task.get('allowed_paths')}")
            else:
                geaendert = session_files
                vorher = {} if self._check_session("implementer", task, session_files,
                                                   ergebnis.call_id, mem) else None
            if vorher is None:
                outcome = "gate_failed"
            else:
                gruen, detail = self._green(task, mem, baseline)
                if gruen:
                    ergebnisse = task_gates_mod.run_task_gates(self.config.root, self.config.raw,
                                                               geaendert)
                    for g in ergebnisse:
                        self.store.event("gate", task_id=task["id"], role="implementer",
                                         detail=g.event_detail())
                    blockiert = [g for g in ergebnisse if g.blocks]
                    if blockiert:
                        gruen = False
                        detail = {"gate": blockiert[0].gate, "passed": False}
                        mem.feedback.extend(f"{g.gate}-Gate: {'; '.join(g.findings[:3])}"
                                            for g in blockiert)
                if gruen:
                    mem.diff = self._diff(vorher) if vorher else ""
                    mem.changed = list(geaendert)
                    self._set(st, "green")
                else:
                    if session_files is None:
                        self._restore(vorher)
                    outcome = "gate_failed"
        else:
            mem.feedback.extend(ergebnis.problems[:3])
        self.log_role_call(ergebnis, binding, task_id=task["id"], outcome=outcome, detail=detail)
        self.save()

    def _green(self, task: dict, mem: _TaskMemory, baseline: list[str] | None) -> tuple[bool,
                                                                                        dict]:
        """GREEN-Gate: code/test alle Tests grün; config/doc keine neuen Fehler (FR-06)."""
        probe = self.ctx.run_tests()
        mem.test_output = json.dumps(probe.summary(), ensure_ascii=False)
        if (task.get("type") or "code") in ("config", "doc"):
            neu = [f"{c.classname}.{c.name}" for c in probe.failing()
                   if f"{c.classname}.{c.name}" not in (baseline or [])] if probe.ok else []
            gruen = probe.ok and not neu
        else:
            gruen = probe.ok and bool(probe.cases) and not probe.failing()
        if not gruen:
            mem.feedback.append(f"GREEN-Gate: {mem.test_output[:500]}")
        return gruen, {"gate": "green", "passed": gruen}

    def _diff(self, vorher: dict[str, str | None]) -> str:
        teile = []
        for pfad, alt in vorher.items():
            neu = self.ctx.read(pfad) or ""
            teile.extend(difflib.unified_diff((alt or "").splitlines(keepends=True),
                                              neu.splitlines(keepends=True),
                                              fromfile=f"a/{pfad}", tofile=f"b/{pfad}"))
        return "".join(teile)

    def _apply_reviewer(self, st: dict, task: dict, mem: _TaskMemory, ergebnis: RoleResult,
                        binding: RoleBinding) -> None:
        if ergebnis.ok and ergebnis.output["verdict"] == "pass":
            self._set(st, "reviewed")
            st["attempts"] = 0
        elif ergebnis.ok:
            mem.review = ergebnis.output["findings"]
            mem.feedback.append("Review: fail")
            self._set(st, "red", reason="Review fail")
        else:
            mem.feedback.extend(ergebnis.problems[:3])
        self.log_role_call(ergebnis, binding, task_id=task["id"])
        self.save()

    # Session-Aufträge (SPEC-0061 FR-01 bis FR-03) ─────────────────────────────
    def _rel(self, pfad) -> str:
        try:
            return str(pfad.relative_to(self.config.root))
        except ValueError:
            return str(pfad)

    def _snapshot(self) -> dict[str, str]:
        from ..quality.files import collect_files

        return {f: hashlib.sha256((self.config.root / f).read_bytes()).hexdigest()
                for f in collect_files(self.config.root, ["**"], SNAPSHOT_EXCLUDE)}

    def _request_work(self, rolle: str, st: dict | None, task: dict | None,
                      feedback: list[str], sources: dict,
                      failing: list[str] | None = None) -> RunOutcome:
        """Persistiert einen Auftrag an eine Session-Arbeitsrolle (CON-0212 INV-05)."""
        request_id = f"work-{secrets.token_hex(4)}"
        erlaubt: list[str] = []
        if task and rolle == "test_author" and task.get("test_file"):
            erlaubt = [task["test_file"]]
        elif task and rolle == "implementer":
            erlaubt = list(task.get("allowed_paths") or [])
        auftrag = {"kind": "work", "request_id": request_id, "role": rolle,
                   "task_id": task["id"] if task else None,
                   "attempt": st["attempts"] if st else 1, "created_at": now(),
                   "allowed_paths": erlaubt, "test_file": (task or {}).get("test_file"),
                   "sources": {k: v for k, v in sources.items() if v not in (None, "", [], {})},
                   "feedback": list(feedback),
                   "output_schema": (self.role(rolle).output_schema if rolle in JSON_ROLES
                                     else None),
                   "snapshot": f"{request_id}.snapshot.json"}
        self.store.write_work(auftrag, {"files": self._snapshot(), "failing": failing or []})
        self.state["status"] = "awaiting_session"
        self.transition(frm=(st or {}).get("state", self.state.get("phase")),
                        to="awaiting_session", task_id=(task or {}).get("id"), role=rolle)
        self.save()
        return RunOutcome(3, f"{rolle}: Auftrag an die Session – Ergebnis bestätigen mit "
                             f"sdd pipeline done {self.store.run_id}"
                             + (" --json '…'" if rolle in JSON_ROLES else "") + ".",
                          self.store.run_id)

    def _changed_since(self, auftrag: dict) -> list[str]:
        vorher = self.store.read_snapshot(auftrag).get("files", {})
        jetzt = self._snapshot()
        return sorted({f for f, h in jetzt.items() if vorher.get(f) != h} |
                      {f for f in vorher if f not in jetzt})

    def _continue_session(self, auftrag: dict, output: Any) -> RunOutcome | None:
        rolle = auftrag["role"]
        binding = RoleBinding(rolle, "session", "", None, None, {}, "session")
        call_id = f"session-{auftrag['request_id']}"
        if rolle == "decomposer":
            ergebnis = RoleResult(rolle, call_id, 1, "ok", output=output)
            self.log_role_call(ergebnis, binding)
            return self._s1(output["tasks"])
        st = self._task_state(auftrag["task_id"])
        task = self._load_tasks()[auftrag["task_id"]]
        mem = self._memory.setdefault(st["task_id"], _TaskMemory(feedback=list(
            auftrag.get("feedback") or [])))
        attempt = max(1, st["attempts"])
        if rolle == "reviewer":
            ergebnis = RoleResult(rolle, call_id, attempt, "ok", output=output)
            self._apply_reviewer(st, task, mem, ergebnis, binding)
            return None
        geaendert = self._changed_since(auftrag)
        if rolle == "test_author":
            inhalt = self.ctx.read(task.get("test_file") or "")
            ergebnis = RoleResult(rolle, call_id, attempt, "ok" if inhalt is not None else
                                  "invalid_output",
                                  output={"test_file": task.get("test_file"), "content": inhalt,
                                          "fr_ids": task.get("fr_ids")},
                                  problems=[] if inhalt is not None else
                                  [f"Testdatei {task.get('test_file')} fehlt"])
            self._apply_test_author(st, task, mem, ergebnis, binding, geaendert)
        else:
            ergebnis = RoleResult(rolle, call_id, attempt, "ok",
                                  output={"files": [], "explanation": "Session"})
            basis = self.store.read_snapshot(auftrag).get("failing") or []
            self._apply_implementer(st, task, mem, ergebnis, binding, geaendert, basis)
        return None

    # Phase acceptance und finalize ───────────────────────────────────────────
    def _acceptance(self) -> RunOutcome | None:
        probe = self.ctx.run_tests()
        facts = {"frs": self.ctx.fr_status(probe), "gate_results": [probe.summary()]}
        optionen = self.options()
        if optionen.get("auto") and "holdout" in self.auto_steps():
            base_url = optionen.get("base_url") or (
                (self.config.raw.get("evaluator") or {}).get("base_url"))
            ergebnis = auto_steps_mod.holdout_step(self.config, self.store.spec_id, base_url)
            self.store.event("gate", detail=ergebnis.event_detail())
            facts["holdout"] = auto_steps_mod.holdout_facts(ergebnis)
        request = new_request("S3", facts)
        antwort = self.ask(request)
        if isinstance(antwort, RunOutcome):
            return antwort
        return self.apply(request, antwort)

    def _accept(self, command: dict) -> RunOutcome | None:
        bewertet = {f["id"]: f["status"] for f in command["frs"]}
        fehlend = [fr for fr in self.ctx.spec_frs if bewertet.get(fr, "fehlt") == "fehlt"]
        if fehlend:
            return self.halt("Abnahme: FRs fehlen", frs=fehlend)
        self.state["phase"] = "finalize"
        self.transition(frm="acceptance", to="finalize")
        self.save()
        return None

    def _reopen(self, command: dict) -> RunOutcome | None:
        """S3 reopen (FR-09): Tasks zurück auf red, Hinweis als history, S3 erneut."""
        anzahl = sum(1 for d in self.decisions() if d.get("valid")
                     and (d.get("command") or {}).get("command") == "reopen")
        if anzahl > self.max_reopen:
            return self.halt(f"max_reopen ({self.max_reopen}) erreicht")
        for task_id in command["task_ids"]:
            st = self._task_state(task_id)
            st["attempts"] = 0
            self._set(st, "red", reason=f"reopen: {command['hint']}")
        self.state["phase"] = "tasks"
        self.transition(frm="acceptance", to="tasks", reason="S3 reopen")
        self.save()
        return None

    def _finalize(self) -> RunOutcome:
        """Nach S3: ohne --auto nur finalize, mit --auto die Kette (CON-0214 INV-01)."""
        spec_id = self.store.spec_id
        schritte = self.auto_steps() if self.options().get("auto") else ["finalize"]
        danach = [s for s in schritte if s not in auto_steps_mod.BEFORE_ACCEPTANCE]
        ergebnisse = auto_steps_mod.after_acceptance(self.config, spec_id, danach)
        for r in ergebnisse:
            self.store.event("gate", detail=r.event_detail())
        gescheitert = next((r for r in ergebnisse if r.status == "failed"), None)
        if gescheitert:
            self.state["status"] = "failed"
            self.store.event("transition", to="failed", detail={"reason": gescheitert.reason},
                             **{"from": "finalize"})
            self.save()
            return RunOutcome(1, f"{gescheitert.step} gescheitert: {gescheitert.reason}",
                              self.store.run_id)
        pr = next((r.data.get("pr") for r in ergebnisse if r.data.get("pr")), "")
        ziel = pr or "ohne PR"
        self.state.update(status="completed", phase="done")
        self.transition(frm="finalize", to="done", reason=ziel)
        self.save()
        return RunOutcome(0, f"{spec_id} abgeschlossen ({ziel}).", self.store.run_id)


# ── Zerlegung → Tasks nach CON-0096 ──────────────────────────────────────────

def to_tasks(spec_id: str, roh: list[dict], *, run_id: str | None = None) -> list:
    """Rollenausgabe (CON-0200) → Tasks nach CON-0096 mit fr_ids/allowed_paths (CON-0203).

    Titel werden zu IDs `T01`, `T02`, …; Abhängigkeiten verweisen danach auf diese IDs.
    `context_size` und `estimated_tokens` folgen aus der Komplexität.
    """
    from ..task_model import Complexity, ContextSize, Task, TaskType

    ids = {t["title"]: f"T{i:02d}" for i, t in enumerate(roh, 1)}
    tasks = []
    for t in roh:
        groesse, tokens = COMPLEXITY_SIZE.get(t.get("complexity", "medium"), ("M", 5000))
        tasks.append(Task(
            id=ids[t["title"]], spec_id=spec_id, title=t["title"], description=t["description"],
            type=TaskType(t["type"]), complexity=Complexity(t["complexity"]),
            context_size=ContextSize(groesse), estimated_tokens=tokens,
            dependencies=[ids[d] for d in t.get("dependencies", []) if d in ids],
            test_ids=[t["test_file"]] if t.get("test_file") else [],
            test_file=t.get("test_file"), test_command=t.get("test_command"),
            fr_ids=list(t.get("fr_ids", [])), allowed_paths=list(t.get("allowed_paths", [])),
            run_id=run_id))
    return tasks


def topological(tasks: list) -> list:
    """Tasks in Abhängigkeitsreihenfolge (stabil, Wellen von vorne nach hinten)."""
    rest = list(tasks)
    fertig: set[str] = set()
    ordnung = []
    while rest:
        welle = [t for t in rest if all(d in fertig for d in t.dependencies)] or rest[:1]
        for t in welle:
            ordnung.append(t)
            fertig.add(t.id)
            rest.remove(t)
    return ordnung
