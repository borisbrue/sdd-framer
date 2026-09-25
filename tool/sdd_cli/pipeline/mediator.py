"""PipelineSupervisor: Mediator der Rollen-Pipeline (SPEC-0053 FR-08 bis FR-15, CON-0205).

Die Rollen kennen einander nicht. Der Mediator steuert den Ablauf als fortsetzbaren
Zustandsautomaten (`state.json` nach jedem Übergang), reicht Artefakte weiter, wendet die
PathPolicy auf jeden Schreibvorgang an und holt an S1 bis S3 eine Entscheidung ein. Der
Supervisor liefert nur Commands; ausgeführt werden sie hier.
"""
from __future__ import annotations

import difflib
import json
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .. import __version__
from ..gate import ExecutionGate
from .context import ContextError, ProjectContext
from .decisions import Answer, Pending, SessionSource, new_request, validate_command
from .path_policy import PathPolicy
from .providers import (
    SAME_MODEL_WARNING,
    RoleBinding,
    RoleConfigError,
    build_provider,
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
        self.state: dict = {}
        self._roles: dict[str, RoleDefinition] = {}
        self._memory: dict[str, _TaskMemory] = {}
        self._decomposer_feedback: list[str] = []

    # ── Einstieg ─────────────────────────────────────────────────────────────
    @classmethod
    def start(cls, config: SddConfig, spec_id: str, *, dry_run: bool = False,
              max_tasks: int | None = None,
              notify: Callable[[str], None] | None = None) -> RunOutcome:
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
        store = RunStore.create(config.root, spec_id)
        store.write_run({"run_id": store.run_id, "spec_id": spec_id, "started_at": now(),
                         "sdd_version": __version__,
                         "options": {"dry_run": dry_run, "max_tasks": max_tasks},
                         "roles": roles, "warnings": warnings})
        m = cls(config, store, notify=notify, max_tasks=max_tasks)
        m.state = {"run_id": store.run_id, "status": "running", "phase": "decompose",
                   "revisions": 0, "tasks": [], "pending_request_id": None}
        m.save()
        for w in warnings:
            store.event("warning", detail={"message": w})
            m.notify(f"⚠ {w}")
        return m.advance()

    @classmethod
    def resume(cls, config: SddConfig, run_id: str, *, max_tasks: int | None = None,
               notify: Callable[[str], None] | None = None) -> RunOutcome:
        m = cls._open(config, run_id, notify=notify, max_tasks=max_tasks)
        status = m.state["status"]
        if status == "awaiting_supervisor":
            return RunOutcome(3, "Wartet auf eine Entscheidung (sdd pipeline decide).", run_id)
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
        fehler = validate_command(command, request)
        m.log_decision(request, command, source="session", errors=fehler)
        if fehler:
            raise PipelineError("Command ungültig: " + "; ".join(fehler))
        m.close_request(request)
        m.state["status"] = "running"
        m.save()
        stopp = m.apply(request, command)
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

    def binding(self, name: str, task_state: dict | None = None) -> RoleBinding:
        b = resolve_binding(self.config, self.role(name))
        modell = ((task_state or {}).get("assignment") or {}).get(name)
        return b.with_model(modell) if modell else b

    def provider(self, binding: RoleBinding, role_def: RoleDefinition) -> Any:
        return build_provider(self.config, binding, role_def)

    def log_role_call(self, ergebnis: RoleResult, binding: RoleBinding, *,
                      task_id: str | None = None, outcome: str | None = None,
                      detail: dict | None = None) -> None:
        info = {"model": binding.model, "provider": binding.provider}
        if ergebnis.problems:
            info["problems"] = ergebnis.problems[:10]
        self.store.event("role_call", task_id=task_id, role=ergebnis.role,
                         call_id=ergebnis.call_id, attempt=ergebnis.attempt,
                         outcome=outcome or ergebnis.outcome, prompt_hash=ergebnis.prompt_hash,
                         detail={**info, **(detail or {})})

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
        return SessionSource() if supervisor_mode(self.config) == "session" else InlineSource(self)

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
            fehler = validate_command(antwort.command, request)
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
        codes = {"completed": 0, "awaiting_supervisor": 3, "halted": 1, "failed": 1}
        return RunOutcome(codes.get(status, 0), f"Run ist {status}.", self.store.run_id)

    # Phase decompose ─────────────────────────────────────────────────────────
    def _decompose(self) -> RunOutcome | None:
        role_def = self.role("decomposer")
        binding = self.binding("decomposer")
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
        tasks = ergebnis.output["tasks"]
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
        while st["state"] != "done":
            if st["state"] == "reviewed":
                self._set(st, "done")
                self.save()
                break
            if st["attempts"] >= self.max_attempts:
                stopp = self._escalate(st, task, mem)
                if stopp is not None or self.state["phase"] != "tasks":
                    return stopp
                continue
            st["attempts"] += 1
            self.save()
            if st["state"] in ("pending", "retry", "reassigned"):
                self._test_author(st, task, mem)
            elif st["state"] == "red":
                self._implementer(st, task, mem)
            elif st["state"] == "green":
                self._reviewer(st, task, mem)
        self.notify(f"  ✓ {task['id']} {task['title']}")
        return None

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

    def _call(self, role: str, st: dict, task: dict, sources: dict) -> tuple[RoleResult,
                                                                              RoleBinding]:
        binding = self.binding(role, st)
        role_def = self.role(role)
        ergebnis = self.runner.run(role_def, self.provider(binding, role_def), sources,
                                   attempt=st["attempts"], params=binding.params,
                                   check_context={"task": task}, task=task)
        return ergebnis, binding

    def _write(self, role: str, task: dict, files: list[dict],
               ergebnis: RoleResult) -> dict[str, str | None] | None:
        """Schreibt nach PathPolicy; None, wenn ein Pfad abgelehnt wurde (nichts geschrieben)."""
        abgelehnt = []
        for f in files:
            e = self.policy.check(role, f["path"], task)
            if not e.allowed:
                abgelehnt.append((f["path"], e.reason))
        if abgelehnt:
            for pfad, grund in abgelehnt:
                self.store.event("write_rejected", role=role, task_id=task["id"],
                                 detail={"path": pfad, "reason": grund,
                                         "call_id": ergebnis.call_id})
            return None
        vorher: dict[str, str | None] = {}
        for f in files:
            ziel = self.config.root / f["path"]
            vorher[f["path"]] = ziel.read_text(encoding="utf-8") if ziel.is_file() else None
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_text(f["content"], encoding="utf-8")
        return vorher

    def _restore(self, vorher: dict[str, str | None]) -> None:
        for pfad, inhalt in vorher.items():
            ziel = self.config.root / pfad
            if inhalt is None:
                ziel.unlink(missing_ok=True)
            else:
                ziel.write_text(inhalt, encoding="utf-8")

    def _test_author(self, st: dict, task: dict, mem: _TaskMemory) -> None:
        ergebnis, binding = self._call("test_author", st, task, self._sources(
            task, mem, test_output=mem.test_output))
        outcome, detail = ergebnis.outcome, {}
        if ergebnis.ok:
            files = [{"path": ergebnis.output["test_file"], "content": ergebnis.output["content"]}]
            vorher = self._write("test_author", task, files, ergebnis)
            if vorher is None:
                outcome = "gate_failed"
                mem.feedback.append(f"Schreibversuch abgelehnt: {files[0]['path']}")
            else:
                probe = self.ctx.run_tests()
                faelle = probe.for_file(task["test_file"]) if probe.ok else []
                rot = [c for c in faelle if c.status in ("failed", "error")]
                if probe.ok and rot:
                    detail = {"gate": "red", "passed": True}
                    mem.test_output = json.dumps(probe.summary(), ensure_ascii=False)
                    st["attempts"] = 0
                    self._set(st, "red")
                else:
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

    def _implementer(self, st: dict, task: dict, mem: _TaskMemory) -> None:
        sources = self._sources(task, mem, repo_map=self.ctx.repo_map(),
                                test_file=self.ctx.read(task["test_file"]) or "",
                                test_output=mem.test_output, review=mem.review)
        ergebnis, binding = self._call("implementer", st, task, sources)
        outcome, detail = ergebnis.outcome, {}
        if ergebnis.ok:
            vorher = self._write("implementer", task, ergebnis.output["files"], ergebnis)
            if vorher is None:
                outcome = "gate_failed"
                mem.feedback.append("Schreibversuch außerhalb der erlaubten Pfade abgelehnt; "
                                    f"erlaubt: {task.get('allowed_paths')}")
            else:
                probe = self.ctx.run_tests()
                mem.test_output = json.dumps(probe.summary(), ensure_ascii=False)
                if probe.ok and probe.cases and not probe.failing():
                    mem.diff = self._diff(vorher)
                    detail = {"gate": "green", "passed": True}
                    self._set(st, "green")
                else:
                    self._restore(vorher)
                    outcome = "gate_failed"
                    detail = {"gate": "green", "passed": False}
                    mem.feedback.append(f"GREEN-Gate: {mem.test_output[:500]}")
        else:
            mem.feedback.extend(ergebnis.problems[:3])
        self.log_role_call(ergebnis, binding, task_id=task["id"], outcome=outcome, detail=detail)
        self.save()

    def _diff(self, vorher: dict[str, str | None]) -> str:
        teile = []
        for pfad, alt in vorher.items():
            neu = self.ctx.read(pfad) or ""
            teile.extend(difflib.unified_diff((alt or "").splitlines(keepends=True),
                                              neu.splitlines(keepends=True),
                                              fromfile=f"a/{pfad}", tofile=f"b/{pfad}"))
        return "".join(teile)

    def _reviewer(self, st: dict, task: dict, mem: _TaskMemory) -> None:
        sources = self._sources(task, mem, diff=mem.diff or "(Diff nicht verfügbar)",
                                gate_results=[json.loads(mem.test_output)]
                                if mem.test_output else [])
        ergebnis, binding = self._call("reviewer", st, task, sources)
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

    # Phase acceptance und finalize ───────────────────────────────────────────
    def _acceptance(self) -> RunOutcome | None:
        probe = self.ctx.run_tests()
        facts = {"frs": self.ctx.fr_status(probe), "gate_results": [probe.summary()]}
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

    def _finalize(self) -> RunOutcome:
        spec_id = self.store.spec_id
        if self.ctx.is_git_repo():
            from ..finalize import SpecFinalizer

            report = SpecFinalizer(self.config).run(spec_id, skip_container=True)
            if report.error:
                self.state["status"] = "failed"
                self.store.event("transition", to="failed", detail={"reason": report.error},
                                 **{"from": "finalize"})
                self.save()
                return RunOutcome(1, f"Finalize gescheitert: {report.error}", self.store.run_id)
            ziel = report.pr_url or (str(report.pr_path) if report.pr_path else "")
        else:
            from ..frontmatter import patch_status

            patch_status(self.ctx.spec_path, "implemented")
            ziel = "kein Git-Repository: nur Status implemented gesetzt"
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
