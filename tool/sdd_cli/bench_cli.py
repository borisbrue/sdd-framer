"""`sdd bench init|run|report|compare` (SPEC-0056, CON-0223, CON-0224).

`run`, `report` und `compare` schreiben nur unter `bench/results/`. Exit-Codes: 0 Erfolg, 2 ungültige
Eingaben (Matrix, Suite, Profil, Ordner).
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import click
from rich.console import Console

from .config import find_project_root, load_config

console = Console()
BLUEPRINT_BENCH = Path(__file__).resolve().parent / "blueprint" / "bench"


def _config():
    root = find_project_root()
    if root is None:
        console.print("[red]✗[/] Kein SDD-Projekt gefunden. 'sdd init' zuerst.")
        sys.exit(2)
    return load_config(root)


def _fail(message: str) -> None:
    console.print(f"[red]✗[/] {message}")
    sys.exit(2)


@click.group("bench", help="Benchmark: Modellbelegungen nach Qualität und Tokens (SPEC-0056).")
def bench_group() -> None:
    pass


@bench_group.command("init", help="Legt bench/ aus den Vorlagen an (überschreibt nichts).")
def init_cmd() -> None:
    cfg = _config()
    angelegt = []
    for quelle in sorted(p for p in BLUEPRINT_BENCH.rglob("*") if p.is_file()):
        ziel = cfg.root / "bench" / quelle.relative_to(BLUEPRINT_BENCH)
        if not ziel.exists():
            ziel.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(quelle, ziel)
            angelegt.append(ziel)
    from .init import ignore_local_config

    ignore_local_config(cfg.root)
    for datei in angelegt:
        console.print(f"  [green]+[/] {datei.relative_to(cfg.root)}")
    if not angelegt:
        console.print("[green]✓[/] bench/ ist vollständig.")


@bench_group.command("run", help="Führt die Matrix aus und schreibt nach bench/results/<ts>/.")
@click.option("--matrix", "matrix_path", type=click.Path(path_type=Path),
              default=Path("bench/matrix.yaml"), show_default=True)
@click.option("--suite", default=None, help="Nur diese Suite.")
@click.option("--only", default=None, help="Nur diese Belegung.")
@click.option("--repetitions", type=click.IntRange(1, 50), default=None)
@click.option("--concurrency", type=click.IntRange(1, 32), default=1, show_default=True)
@click.option("--resume", type=click.Path(path_type=Path), default=None,
              help="Ergebnisordner fortsetzen.")
@click.option("--dry-run", is_flag=True, help="Nur Zahl der Läufe und Schätzung, kein Aufruf.")
def run_cmd(matrix_path: Path, suite: str | None, only: str | None, repetitions: int | None,
            concurrency: int, resume: Path | None, dry_run: bool) -> None:
    from .bench.config import BenchError, load_matrix
    from .bench.runner import read_records, run_matrix

    cfg = _config()
    pfad = matrix_path if matrix_path.is_absolute() else cfg.root / matrix_path
    if resume is not None and not (cfg.root / resume if not resume.is_absolute()
                                   else resume).is_dir():
        _fail(f"Ergebnisordner {resume} fehlt.")
    try:
        matrix = load_matrix(pfad, cfg)
        ordner, plan = run_matrix(
            cfg, matrix, suite=suite, only=only, repetitions=repetitions,
            concurrency=concurrency, dry_run=dry_run,
            resume=(cfg.root / resume if resume and not resume.is_absolute() else resume),
            notify=console.print)
    except BenchError as exc:
        _fail(str(exc))
    if dry_run:
        bisher = sorted((cfg.root / "bench" / "results").glob("*/results.jsonl"))
        tokens = None
        if bisher:
            alte = read_records(bisher[-1].parent)
            if alte:
                tokens = int(sum(r["T_in"] + r["T_out"] for r in alte) / len(alte)
                             * len(plan.jobs))
        console.print(f"{len(plan.jobs)} Läufe" + (f", geschätzt {tokens} Tokens"
                                                    if tokens else ""))
        for suite_name, namen in plan.filtered.items():
            console.print(f"  gefiltert ({suite_name}): {', '.join(namen)}")
        return
    console.print(f"[green]✓[/] Ergebnisse: {ordner.relative_to(cfg.root)}")


@bench_group.command("report", help="Report mit Kennzahlen, Pareto-Front und Signifikanz.")
@click.argument("ordner", type=click.Path(path_type=Path))
@click.option("--html", "as_html", is_flag=True, help="Zusätzlich report.html.")
@click.option("--by", type=click.Choice(["assignment", "role"]), default="assignment",
              show_default=True)
@click.option("--exclude-reasoning", is_flag=True, help="Effizienz ohne Reasoning-Tokens.")
def report_cmd(ordner: Path, as_html: bool, by: str, exclude_reasoning: bool) -> None:
    from .bench.report import html_report, markdown, valid_records
    from .bench.runner import read_records

    if not (ordner / "results.jsonl").is_file():
        _fail(f"{ordner}/results.jsonl fehlt.")
    records, ungueltig = valid_records(read_records(ordner))
    gefiltert = None
    if (ordner / "filtered.json").is_file():
        gefiltert = json.loads((ordner / "filtered.json").read_text(encoding="utf-8"))
    md = markdown(ordner, records, by=by, exclude_reasoning=exclude_reasoning,
                  filtered=gefiltert)
    (ordner / "report.md").write_text(md, encoding="utf-8")
    if as_html:
        (ordner / "report.html").write_text(html_report(ordner, records, md, by=by),
                                            encoding="utf-8")
    print(md)
    if ungueltig:
        console.print(f"[yellow]⚠[/] {ungueltig} ungültige Records übersprungen.")


@bench_group.command("compare", help="Zwei Ergebnisordner je Belegung vergleichen.")
@click.argument("a", type=click.Path(path_type=Path))
@click.argument("b", type=click.Path(path_type=Path))
@click.option("--json", "as_json", is_flag=True)
def compare_cmd(a: Path, b: Path, as_json: bool) -> None:
    from .bench.report import compare, valid_records
    from .bench.runner import read_records

    for ordner in (a, b):
        if not (ordner / "results.jsonl").is_file():
            _fail(f"{ordner}/results.jsonl fehlt.")
    zeilen, warnungen = compare(valid_records(read_records(a))[0],
                                valid_records(read_records(b))[0])
    if as_json:
        print(json.dumps({"rows": zeilen, "warnings": warnungen}, ensure_ascii=False, indent=2))
        return
    for z in zeilen:
        if "delta_Q" in z:
            hinweis = "" if z["distinct"] else " (nicht unterscheidbar)"
            console.print(f"{z['q_kind']} {z['key']}: Q {z['Q_a']:.3f} → {z['Q_b']:.3f} "
                          f"(Δ {z['delta_Q']:+.3f}{hinweis}), T Δ {z['delta_T']:+.0f}")
        else:
            console.print(f"{z['q_kind']} {z['key']}: nur in "
                          f"{'A' if z['Q_b'] is None else 'B'}")
    for w in warnungen:
        console.print(f"[yellow]⚠[/] {w}")
