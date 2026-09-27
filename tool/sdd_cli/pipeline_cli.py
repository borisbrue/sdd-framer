"""`sdd pipeline run|decide|status|report` (SPEC-0053 FR-12 bis FR-15, CON-0205)."""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .config import find_project_root, load_config

console = Console()

CLAUDE_PROVIDERS = ("claude-cli", "anthropic")


def _config():
    root = find_project_root()
    if root is None:
        console.print("[red]✗[/] Kein SDD-Projekt gefunden. 'sdd init' zuerst.")
        sys.exit(2)
    return load_config(root)


def _finish(outcome) -> None:
    farbe = {0: "green", 1: "red", 3: "yellow"}.get(outcome.exit_code, "red")
    console.print(f"[{farbe}]{outcome.message}[/]")
    if outcome.run_id:
        console.print(f"  Run: [cyan]{outcome.run_id}[/]")
    sys.exit(outcome.exit_code)


@click.group("pipeline", help="Rollenbasierte Pipeline mit Supervisor (SPEC-0053).")
def pipeline_group() -> None:
    pass


@pipeline_group.command("run")
@click.argument("spec_id")
@click.option("--dry-run", is_flag=True, help="Nur Zerlegung und S1, kein Code.")
@click.option("--resume", "resume_id", default=None, help="Run am gespeicherten Zustand fortsetzen.")
@click.option("--max-tasks", type=int, default=None, help="Höchstens N Tasks bearbeiten.")
@click.option("--task", "task_id", default=None,
              help="Nur diesen Task der gespeicherten Zerlegung bearbeiten (SPEC-0061 FR-05).")
@click.option("--auto", is_flag=True,
              help="Abschluss-Kette aus pipeline.auto_steps (holdout, finalize, automerge).")
@click.option("--base-url", default=None, envvar="SDD_EVAL_BASE_URL",
              help="Ziel der Holdout-Evaluation für --auto (sonst evaluator.base_url).")
@click.option("--session", "session", multiple=True, metavar="ROLLE",
              help="Rolle nur für diesen Run im Modus session (mehrfach; SPEC-0062 FR-01).")
@click.option("--steps", default=None, metavar="LISTE",
              help="Abschluss-Schritte für --auto, kommagetrennt (überschreibt "
                   "pipeline.auto_steps).")
@click.option("--max-tokens", type=int, default=None,
              help="Token-Budget des Runs (überschreibt pipeline.budget.max_tokens).")
@click.option("--max-claude-tokens", type=int, default=None,
              help="Budget für Rollen mit claude-cli/anthropic.")
@click.option("--run-id", "run_id", default=None, hidden=True,
              help="Vorgegebene Run-ID (Web-Adapter, SPEC-0062 FR-03).")
def run_cmd(spec_id: str, dry_run: bool, resume_id: str | None, max_tasks: int | None,
            task_id: str | None, auto: bool, base_url: str | None, session: tuple[str, ...],
            steps: str | None, max_tokens: int | None = None,
            max_claude_tokens: int | None = None, run_id: str | None = None) -> None:
    from .pipeline.mediator import PipelineError, PipelineSupervisor

    cfg = _config()
    if resume_id and (session or steps is not None):
        console.print("[red]✗[/] --session und --steps gelten beim Start; --resume übernimmt die "
                      "Optionen aus run.json.")
        sys.exit(2)
    if task_id and (resume_id or auto or dry_run):
        console.print("[red]✗[/] --task lässt sich nicht mit --resume, --auto oder --dry-run "
                      "kombinieren.")
        sys.exit(2)
    try:
        if resume_id:
            if not resume_id.startswith(f"{spec_id}-"):
                raise PipelineError(f"Run {resume_id} gehört nicht zu {spec_id}.")
            outcome = PipelineSupervisor.resume(cfg, resume_id, max_tasks=max_tasks,
                                                notify=console.print)
        else:
            schritte = ([s.strip() for s in steps.split(",") if s.strip()]
                        if steps is not None else None)
            outcome = PipelineSupervisor.start(cfg, spec_id, dry_run=dry_run,
                                               max_tasks=max_tasks, task_id=task_id, auto=auto,
                                               base_url=base_url, session=session,
                                               steps=schritte, run_id=run_id,
                                               budget={"max_tokens": max_tokens,
                                                       "max_claude_tokens": max_claude_tokens},
                                               notify=console.print)
    except PipelineError as exc:
        console.print(f"[red]✗[/] {exc}")
        sys.exit(2)
    if dry_run and outcome.exit_code == 0:
        _dry_run_summary(cfg, spec_id, outcome.run_id)
    _finish(outcome)


@pipeline_group.command("decide")
@click.argument("run_id")
@click.option("--json", "command_json", required=True, help="Supervisor-Command (CON-0201).")
def decide_cmd(run_id: str, command_json: str) -> None:
    from .pipeline.decisions import parse_command
    from .pipeline.mediator import PipelineError, PipelineSupervisor

    cfg = _config()
    try:
        outcome = PipelineSupervisor.decide(cfg, run_id, parse_command(command_json),
                                            notify=console.print)
    except PipelineError as exc:
        console.print(f"[red]✗[/] {exc}")
        sys.exit(2)
    _finish(outcome)


@pipeline_group.command("done")
@click.argument("run_id")
@click.option("--json", "output_json", default=None,
              help="Ausgabe der Rolle (Pflicht für decomposer und reviewer, CON-0200).")
def done_cmd(run_id: str, output_json: str | None) -> None:
    """Bestätigt den offenen Session-Auftrag einer Arbeitsrolle (SPEC-0061 FR-02)."""
    from .pipeline.decisions import parse_command
    from .pipeline.mediator import PipelineError, PipelineSupervisor

    cfg = _config()
    ausgabe = None
    if output_json is not None:
        ausgabe = parse_command(output_json)
        if ausgabe is None:
            console.print("[red]✗[/] --json ist kein gültiges JSON.")
            sys.exit(2)
    try:
        outcome = PipelineSupervisor.done(cfg, run_id, ausgabe, notify=console.print)
    except PipelineError as exc:
        console.print(f"[red]✗[/] {exc}")
        sys.exit(2)
    _finish(outcome)


@pipeline_group.command("status")
@click.argument("run_id")
@click.option("--json", "as_json", is_flag=True,
              help="Zustand und offene Anfrage als JSON (SPEC-0058 FR-05).")
def status_cmd(run_id: str, as_json: bool) -> None:
    from .pipeline import monitor
    from .pipeline.store import RunNotFound, RunStore

    cfg = _config()
    try:
        store = RunStore.open(cfg.root, run_id)
    except RunNotFound as exc:
        console.print(f"[red]✗[/] {exc}")
        sys.exit(2)
    if as_json:
        click.echo(json.dumps(monitor.status(cfg.root, run_id), ensure_ascii=False, indent=2))
        sys.exit(0)
    state = store.read_state()
    console.print(f"Run [cyan]{run_id}[/]: Status [bold]{state['status']}[/], "
                  f"Phase {state['phase']}")
    for t in state["tasks"]:
        console.print(f"  {t['task_id']}: {t['state']} (Versuche {t['attempts']})")
    anfrage = store.read_pending() if state.get("pending_request_id") else None
    if anfrage:
        console.print(f"\n[yellow]Offene Anfrage {anfrage['request_id']}[/] an "
                      f"{anfrage['point']}"
                      + (f" für {anfrage['task_id']}" if anfrage.get("task_id") else ""))
        console.print(f"  Erlaubt: {', '.join(anfrage['allowed_commands'])}")
        console.print(f"  Datei: {store.dir / 'pending-decision.json'}")
    auftrag = store.read_work() if state.get("status") == "awaiting_session" else None
    if auftrag:
        console.print(f"\n[yellow]Offener Auftrag {auftrag['request_id']}[/] an die Rolle "
                      f"{auftrag['role']}"
                      + (f" für {auftrag['task_id']}" if auftrag.get("task_id") else ""))
        if auftrag.get("allowed_paths"):
            console.print(f"  Erlaubte Pfade: {', '.join(auftrag['allowed_paths'])}")
        console.print(f"  Datei: {store.dir / 'pending-work.json'}")
        console.print(f"  Bestätigen: sdd pipeline done {run_id}"
                      + (" --json '…'" if auftrag.get("output_schema") else ""))
    sys.exit(0)


@pipeline_group.command("report")
@click.argument("run_id")
def report_cmd(run_id: str) -> None:
    from .pipeline.store import RunNotFound, RunStore

    cfg = _config()
    try:
        store = RunStore.open(cfg.root, run_id)
    except RunNotFound as exc:
        console.print(f"[red]✗[/] {exc}")
        sys.exit(2)
    zeilen = build_report(cfg.root, store)
    table = Table(title=f"Pipeline-Report {run_id}")
    table.add_column("Rolle", no_wrap=True, min_width=11)
    for spalte in ("Modell", "Aufrufe", "Fehler", "Input-T", "Output-T", "Reasoning-T",
                   "Dauer (s)"):
        table.add_column(spalte, justify="left" if spalte == "Modell" else "right")
    for z in zeilen["roles"]:
        table.add_row(z["role"], z["model"], str(z["calls"]), str(z["failures"]),
                      f"{z['input_tokens']:,}", f"{z['output_tokens']:,}",
                      f"{z['reasoning_tokens']:,}", f"{z['duration_ms'] / 1000:.1f}")
    console.print(table)
    console.print(f"Supervisor-Eingriffe: {zeilen['interventions']} "
                  f"(davon ungültig: {zeilen['invalid_decisions']})")
    console.print(f"Claude-Anteil an den Tokens: {zeilen['claude_share']:.0%}")
    if zeilen["warnings"]:
        console.print("[yellow]Warnungen:[/] " + "; ".join(zeilen["warnings"]))
    sys.exit(0)


def build_report(root: Path, store) -> dict:
    """Aufrufe je Rolle aus events.jsonl, Tokens aus token_usage (FR-14)."""
    run = store.read_run()
    rollen: dict[str, dict] = defaultdict(lambda: {"calls": 0, "failures": 0, "input_tokens": 0,
                                                    "output_tokens": 0, "reasoning_tokens": 0,
                                                    "duration_ms": 0})
    for e in store.read_jsonl("events.jsonl"):
        if e["type"] == "role_call":
            r = rollen[e["role"]]
            r["calls"] += 1
            r["failures"] += e.get("outcome") != "ok"
    db = root / ".sdd" / "evaluations.db"
    if db.is_file():
        with sqlite3.connect(db) as con:
            con.row_factory = sqlite3.Row
            for z in con.execute("SELECT * FROM token_usage WHERE run_id = ?", (store.run_id,)):
                rolle = json.loads(z["context_json"] or "{}").get("role", "?")
                r = rollen[rolle]
                r["input_tokens"] += z["input_tokens"] or 0
                r["output_tokens"] += z["output_tokens"] or 0
                r["reasoning_tokens"] += z["reasoning_tokens"] or 0
                r["duration_ms"] += z["duration_ms"] or 0
    belegung = run.get("roles", {})
    gesamt = claude = 0
    ergebnis = []
    for rolle, r in sorted(rollen.items()):
        info = belegung.get(rolle, {})
        tokens = r["input_tokens"] + r["output_tokens"]
        gesamt += tokens
        if info.get("provider") in CLAUDE_PROVIDERS:
            claude += tokens
        ergebnis.append({"role": rolle, "model": info.get("model") or info.get("provider", "?"),
                         **r})
    entscheidungen = store.read_jsonl("decisions.jsonl")
    return {"roles": ergebnis, "claude_share": (claude / gesamt) if gesamt else 0.0,
            "interventions": sum(d.get("valid", False) for d in entscheidungen),
            "invalid_decisions": sum(not d.get("valid", False) for d in entscheidungen),
            "warnings": run.get("warnings", [])}


def _dry_run_summary(cfg, spec_id: str, run_id: str) -> None:
    """Tasks, Tokenverbrauch und geschätzte Rollenverteilung (FR-13)."""
    from .decompose import TaskDecomposer
    from .pipeline.store import RunStore

    tasks = TaskDecomposer().load(spec_id, cfg)
    table = Table(title=f"Zerlegung {spec_id}")
    for spalte in ("ID", "Titel", "Typ", "FRs", "Abhängig von"):
        table.add_column(spalte)
    for t in tasks:
        table.add_row(t.id, t.title, t.type.value, ", ".join(t.fr_ids or []),
                      ", ".join(t.dependencies) or "—")
    console.print(table)
    report = build_report(cfg.root, RunStore.open(cfg.root, run_id))
    tokens = sum(r["input_tokens"] + r["output_tokens"] for r in report["roles"])
    console.print(f"Tokens bisher: {tokens:,}")
    code = sum(1 for t in tasks if t.type.value in ("code", "test"))
    console.print(f"Geschätzte Rollenaufrufe: test_author ≥ {code}, implementer ≥ {code}, "
                  f"reviewer ≥ {code}, supervisor ≥ 2 (S1, S3) plus Eskalationen")
