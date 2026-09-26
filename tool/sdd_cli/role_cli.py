"""`sdd role eval|compare|accept|case` (SPEC-0055, CON-0219, CON-0220).

Holdout-Fälle erscheinen ohne `--include-holdout` nur als Anzahl und Aggregat (ReportProxy).
Exit-Codes: 0 Erfolg bzw. `accept`, 1 `reject`, 2 ungültige Eingaben.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .config import find_project_root, load_config

console = Console()


def _config():
    root = find_project_root()
    if root is None:
        console.print("[red]✗[/] Kein SDD-Projekt gefunden. 'sdd init' zuerst.")
        sys.exit(2)
    return load_config(root)


def _fail(message: str, code: int = 2) -> None:
    console.print(f"[red]✗[/] {message}")
    sys.exit(code)


@click.group("role", help="Rollen-Evals: Golden Cases, Eval, Ratchet (SPEC-0055).")
def role_group() -> None:
    pass


@role_group.command("eval", help="Rolle auf ihren Golden Cases messen (Score, Streuung, Tokens).")
@click.argument("role")
@click.option("--model", "profile", default=None, help="Profil aus llm.profiles.")
@click.option("--version", "version", type=click.Path(path_type=Path), default=None,
              help="Kandidatendatei der Rolle statt der geladenen Rolle.")
@click.option("--runs", default=3, show_default=True, type=click.IntRange(1, 20))
@click.option("--case", "case_ids", multiple=True, help="Nur diese Fälle (mehrfach).")
@click.option("--include-holdout", is_flag=True,
              help="Holdout-Fälle einzeln ausweisen (nie im Tuning-Dialog).")
@click.option("--concurrency", default=2, show_default=True, type=click.IntRange(1, 32))
@click.option("--dry-run", is_flag=True, help="Nur Aufrufzahl und geschätzte Tokens.")
@click.option("--json", "as_json", is_flag=True, help="Report als JSON ausgeben.")
def eval_cmd(role: str, profile: str | None, version: Path | None, runs: int,
             case_ids: tuple[str, ...], include_holdout: bool, concurrency: int, dry_run: bool,
             as_json: bool) -> None:
    from .pipeline.evals import cases as cases_mod
    from .pipeline.evals.report import build_report, estimate, persist
    from .pipeline.evals.runner import EvalError, EvalRunner, setup

    cfg = _config()
    home = cases_mod.role_home(cfg.root, role)
    faelle = cases_mod.list_cases(home)
    if case_ids:
        faelle = [f for f in faelle if f.id in case_ids]
        if not faelle:
            _fail(f"keiner der Fälle {', '.join(case_ids)} gehört zu {role}")
    ungueltig = [(f, p) for f in faelle if (p := cases_mod.case_problems(f))]
    if ungueltig:
        for fall, probleme in ungueltig:
            name = "Holdout-Fall" if fall.holdout else fall.id
            console.print(f"[red]✗[/] {name}: {probleme[0] if not fall.holdout else 'ungültig'}")
        sys.exit(2)
    if not faelle:
        _fail(f"Rolle {role} hat keine Fälle ({home.cases_dir}).")
    mit_rubrik = any(f.rubric for f in faelle)
    aufrufe = len(faelle) * runs * (2 if mit_rubrik else 1)
    if dry_run:
        tokens = estimate(cfg.root, role, len(faelle) * runs)
        console.print(f"{len(faelle)} Fälle × {runs} Läufe: {aufrufe} Aufrufe"
                      + (f", geschätzt {tokens} Tokens" if tokens else ""))
        return
    try:
        st = setup(cfg, role, profile=profile, version=version, with_rubric=mit_rubrik)
        ergebnisse = EvalRunner(cfg, st, concurrency=concurrency).run(faelle, runs)
    except EvalError as exc:
        _fail(str(exc))
    proxy = build_report(st, ergebnisse, runs=runs, include_holdout=include_holdout,
                         role_file=st.role_def.source)
    pfad = persist(cfg.root, home, proxy)
    daten = proxy.to_dict()
    if as_json:
        print(json.dumps(daten, ensure_ascii=False, indent=2))
        return
    _print_report(daten)
    console.print(f"  Report: [cyan]{pfad.relative_to(cfg.root)}[/]")


def _print_report(daten: dict) -> None:
    table = Table(title=f"Eval {daten['role']} {daten['role_version']} · "
                        f"{daten['profile']['name']}")
    for spalte in ("Fall", "Score", "±", "pass", "pass^k", "Tokens out"):
        table.add_column(spalte)
    for c in daten["visible"]:
        tokens = [r["tokens"].get("output_tokens") for r in c["runs"]]
        table.add_row(c["id"], f"{c['score']:.2f}", f"{c['std']:.2f}",
                      "✓" if c["passed"] else "✗", "✓" if c["pass_all"] else "✗",
                      str(sum(t for t in tokens if t) or "–"))
    console.print(table)
    holdout = daten["holdout"]
    if isinstance(holdout, dict):
        mittel = "–" if holdout["mean"] is None else f"{holdout['mean']:.2f}"
        console.print(f"Holdout: {holdout['cases']} Fälle, Score {mittel}")
    total = daten["total"]
    console.print(f"Gesamt: Score {total['mean']}, pass@1 {total['pass_at_1']}, "
                  f"pass^k {total['pass_all']}")
    for w in daten.get("warnings", []):
        console.print(f"[yellow]⚠[/] {w}")


@role_group.command("compare", help="Zwei Reports nach der Ratchet-Regel vergleichen (accept/reject).")
@click.argument("report_a", type=click.Path(path_type=Path))
@click.argument("report_b", type=click.Path(path_type=Path))
@click.option("--json", "as_json", is_flag=True)
def compare_cmd(report_a: Path, report_b: Path, as_json: bool) -> None:
    from .pipeline.evals.ratchet import RatchetError, compare, load, summary

    try:
        urteil = compare(load(report_a), load(report_b))
    except RatchetError as exc:
        _fail(str(exc))
    if as_json:
        print(json.dumps(summary(urteil), ensure_ascii=False, indent=2))
    else:
        for d in urteil.deltas:
            vorher = "–" if d["before"] is None else f"{d['before']:.2f}"
            nachher = "–" if d["after"] is None else f"{d['after']:.2f}"
            console.print(f"  {d['id']}: {vorher} → {nachher}")
        farbe = "green" if urteil.accept else "red"
        console.print(f"[{farbe}]{urteil.label}[/]")
        for g in urteil.reasons:
            console.print(f"  - {g}")
    sys.exit(0 if urteil.accept else 1)


@role_group.command("accept", help="Kandidatenversion übernehmen: Version, Baseline, CHANGELOG.")
@click.argument("role")
@click.option("--report", "report", type=click.Path(path_type=Path), required=True)
@click.option("--force", is_flag=True, help="Auch bei reject übernehmen (mit --reason).")
@click.option("--reason", default=None)
def accept_cmd(role: str, report: Path, force: bool, reason: str | None) -> None:
    from .pipeline.evals.cases import role_home
    from .pipeline.evals.ratchet import RatchetError, accept

    if force and not reason:
        _fail("--force verlangt --reason.")
    cfg = _config()
    try:
        ergebnis = accept(role_home(cfg.root, role), report, force=force, reason=reason)
    except RatchetError as exc:
        _fail(str(exc))
    if not ergebnis.new_version:
        console.print("[red]reject[/] – nichts übernommen:")
        for g in ergebnis.verdict.reasons:
            console.print(f"  - {g}")
        sys.exit(1)
    console.print(f"[green]✓[/] {role} {ergebnis.old_version} → {ergebnis.new_version} "
                  f"({ergebnis.target})" + (" [yellow]erzwungen[/]" if ergebnis.forced else ""))


@role_group.group("case", help="Golden Cases anlegen, aus Runs übernehmen, bestätigen.")
def case_group() -> None:
    pass


@case_group.command("new")
@click.argument("role")
@click.option("--title", required=True)
@click.option("--holdout", is_flag=True, help="Als Holdout-Fall unter .sdd/holdout/roles/.")
def case_new_cmd(role: str, title: str, holdout: bool) -> None:
    from .pipeline.evals.cases import CaseError, new_case, role_home

    cfg = _config()
    try:
        fall = new_case(role_home(cfg.root, role), title, holdout=holdout)
    except CaseError as exc:
        _fail(str(exc))
    console.print(f"[green]✓[/] {fall.id} angelegt (Entwurf): "
                  f"{fall.dir.relative_to(cfg.root) if fall.dir.is_relative_to(cfg.root) else fall.dir}")


@case_group.command("capture")
@click.argument("run_id")
@click.argument("element_id")
def case_capture_cmd(run_id: str, element_id: str) -> None:
    from .pipeline.evals.capture import CaptureError, capture

    cfg = _config()
    try:
        fall = capture(cfg, run_id, element_id)
    except CaptureError as exc:
        _fail(str(exc))
    console.print(f"[green]✓[/] {fall.id} ({fall.role}) als Entwurf angelegt: {fall.dir}")
    console.print("  Erwartung prüfen, dann [cyan]sdd role case confirm "
                  f"{fall.role} {fall.id}[/].")


@case_group.command("confirm")
@click.argument("role")
@click.argument("case_id")
def case_confirm_cmd(role: str, case_id: str) -> None:
    from .pipeline.evals.cases import CaseError, confirm_case, find_case, role_home

    cfg = _config()
    try:
        fall = confirm_case(find_case(role_home(cfg.root, role), case_id))
    except CaseError as exc:
        _fail(str(exc))
    console.print(f"[green]✓[/] {fall.id} bestätigt; zählt ab dem nächsten Eval.")
