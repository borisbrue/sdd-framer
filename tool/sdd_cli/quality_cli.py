"""CLI `sdd quality …` und `sdd arch …` (SPEC-0054, CON-0197)."""
from __future__ import annotations

import difflib
import json
import sys
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.table import Table

from .config import find_project_root, load_config

console = Console()
err = Console(stderr=True)


def _root() -> Path:
    root = find_project_root()
    if root is None:
        err.print("[red]✗[/] Kein SDD-Projekt gefunden. Führe `sdd init` aus.")
        sys.exit(2)
    return root


def _config_fehler(problems, datei: str) -> None:
    err.print(f"[red]✗[/] {datei} ist ungültig:")
    for p in problems:
        pfad, meldung = (p.path, p.message) if hasattr(p, "path") else p
        err.print(f"  {pfad}: {meldung}")
    sys.exit(2)


# ── sdd quality ───────────────────────────────────────────────────────────────

@click.group("quality", help="Codequalität, Architekturtreue und FR-Erfüllung messen (SPEC-0054).")
def quality_group() -> None:
    pass


def _fmt(score: float | None) -> str:
    return "n/a" if score is None else f"{score:.4f}"


def _ausgabe(report: dict) -> None:
    tabelle = Table(title=f"Qualität {report.get('spec', '')}".strip(), show_header=True)
    tabelle.add_column("Dimension")
    tabelle.add_column("Gewicht", justify="right")
    tabelle.add_column("Score", justify="right")
    tabelle.add_column("Hinweis")
    for k in report["tree"].get("children", []):
        tabelle.add_row(k["name"], str(k["weight"]), _fmt(k["score"]), k.get("reason", ""))
    tabelle.add_row("[bold]total[/]", "", f"[bold]{_fmt(report['score'])}[/]",
                    "unvollständig (renormiert)" if report["incomplete"] else "")
    console.print(tabelle)
    frs = report["requirements"]["frs"]
    offen = [f for f in frs if f["status"] != "erfüllt"]
    if frs:
        console.print(f"FRs erfüllt: {len(frs) - len(offen)}/{len(frs)}")
    for f in offen:
        console.print(f"  {f['id']}: {f['status']}")
    for p in report["probes"]:
        if p["status"] == "n/a":
            console.print(f"  [yellow]Sonde {p['name']}: n/a – {p.get('reason', '')}[/]")
    arch = report["architecture"]
    if arch["violations"]:
        console.print(f"Architekturverstöße: {len(arch['violations'])}")


@quality_group.command("measure", help="Misst den Arbeitsstand und gibt den Quality-Report aus.")
@click.option("--spec", "spec_id", default=None, help="Spec-ID für die FR-Erfüllung.")
@click.option("--diff", "base_ref", default=None, help="Nur Änderungen seit diesem Git-Stand.")
@click.option("--json", "as_json", is_flag=True, help="Report als JSON auf stdout.")
@click.option("--out", "out", default=None, type=click.Path(), help="Report als JSON-Datei.")
@click.option("--reuse-test-run", is_flag=True, help="Letzten Test-Run desselben Git-Stands nutzen.")
@click.option("--judge", is_flag=True, help="Optionalen LLM-Judge ausführen.")
def quality_measure(spec_id, base_ref, as_json, out, reuse_test_run, judge) -> None:
    from .quality.config import QualityConfigError
    from .quality.diff import DiffError
    from .quality.measure import measure

    root = _root()
    try:
        ergebnis = measure(root, spec_id=spec_id, base_ref=base_ref,
                           reuse_test_run=reuse_test_run, judge=judge)
    except FileNotFoundError:
        err.print("[red]✗[/] .sdd/quality.yaml fehlt. Lege sie an mit: sdd quality init --preset <name>")
        sys.exit(2)
    except QualityConfigError as exc:
        _config_fehler(exc.problems, ".sdd/quality.yaml bzw. quality:-Einstellungen")
    except DiffError as exc:
        err.print(f"[red]✗[/] {exc}")
        sys.exit(2)
    report = ergebnis.report
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if out:
        ziel = Path(out) if Path(out).is_absolute() else root / out
        if ziel.exists():
            alt = ziel.read_text(encoding="utf-8")
            err.print("".join(difflib.unified_diff(alt.splitlines(keepends=True),
                                                   (text + "\n").splitlines(keepends=True),
                                                   fromfile=str(out), tofile=str(out)))[:4000])
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(text + "\n", encoding="utf-8")
    if as_json:
        click.echo(text)
    else:
        _ausgabe(report)
    for g in ergebnis.gates:
        if not g["passed"]:
            err.print(f"[red]✗ Gate[/] {g['expression']}: {g.get('reason', '')}")
            if g["expression"].startswith("requirements") or "frs" in g["expression"]:
                for f in report["requirements"]["frs"]:
                    if f["status"] != "erfüllt":
                        err.print(f"    {f['id']}: {f['status']}")
    sys.exit(ergebnis.exit_code)


@quality_group.command("doctor", help="Prüft jede Sonde einmal: vorhanden, Format, Normierung.")
@click.option("--json", "as_json", is_flag=True)
def quality_doctor(as_json) -> None:
    from .quality.config import QualityConfigError
    from .quality.doctor import run_doctor

    root = _root()
    try:
        eintraege = run_doctor(root)
    except FileNotFoundError:
        err.print("[red]✗[/] .sdd/quality.yaml fehlt. Lege sie an mit: sdd quality init --preset <name>")
        sys.exit(2)
    except QualityConfigError as exc:
        _config_fehler(exc.problems, ".sdd/quality.yaml")
    if as_json:
        click.echo(json.dumps([e.to_dict() for e in eintraege], indent=2, ensure_ascii=False))
    else:
        for e in eintraege:
            zeichen = "[green]✓[/]" if e.ready else "[red]✗[/]"
            console.print(f"{zeichen} {e.probe}: {'; '.join(e.messages)}", soft_wrap=True)
    sys.exit(0 if all(e.ready for e in eintraege) else 1)


@quality_group.command("init", help="Kopiert ein Preset (quality.yaml und Hilfsskripte) ins Projekt.")
@click.option("--preset", required=True, help="Name des Presets.")
def quality_init(preset) -> None:
    from .quality.presets import available_presets, install_preset

    root = _root()
    try:
        result = install_preset(root, preset)
    except KeyError:
        err.print(f"[red]✗[/] Unbekanntes Preset {preset!r}. Verfügbar: "
                  f"{', '.join(available_presets()) or '–'}")
        sys.exit(2)
    _schreibbericht(result)


def _schreibbericht(result) -> None:
    for rel in result.written:
        console.print(f"[green]✓[/] {rel} angelegt")
    for rel in result.unchanged:
        console.print(f"[cyan]=[/] {rel} unverändert")
    for rel, diff in result.new_files:
        console.print(f"[yellow]![/] {rel} weicht ab – Vorschlag als {rel}.new")
        click.echo(diff)


# ── sdd arch ──────────────────────────────────────────────────────────────────

@click.group("arch", help="Architekturregeln aus .sdd/architecture.yaml prüfen (SPEC-0054).")
def arch_group() -> None:
    pass


def _arch_auswerten(root: Path):
    from .quality.arch.baseline import Baseline, BaselineError
    from .quality.arch.evaluator import adr_titles, evaluate_architecture
    from .quality.arch.rules import ArchConfigError, load_architecture
    from .quality.config import QualityConfigError, load_quality_config
    from .quality.files import collect_files
    from .quality.parsers import DepsGraph
    from .quality.probe import ProbeRun
    from .quality.settings import QualitySettings

    try:
        arch = load_architecture(root)
    except FileNotFoundError:
        err.print("[red]✗[/] .sdd/architecture.yaml fehlt. Vorschlag erzeugen mit: sdd arch init")
        sys.exit(2)
    except ArchConfigError as exc:
        _config_fehler(exc.problems, ".sdd/architecture.yaml")
    try:
        qcfg = load_quality_config(root)
    except FileNotFoundError:
        err.print("[red]✗[/] .sdd/quality.yaml fehlt; sie braucht eine Sonde mit role: deps.")
        sys.exit(2)
    except QualityConfigError as exc:
        _config_fehler(exc.problems, ".sdd/quality.yaml")
    probe = qcfg.probe_for_role("deps")
    if probe is None:
        err.print("[red]✗[/] .sdd/quality.yaml hat keine Sonde mit role: deps.")
        sys.exit(2)
    try:
        baseline = Baseline.load(root)
    except BaselineError as exc:
        err.print(f"[red]✗[/] {exc}")
        sys.exit(2)
    outcome = ProbeRun(root, collect_files(root, qcfg.paths, qcfg.exclude)).execute(probe)
    graph = outcome.result if outcome.ok and isinstance(outcome.result, DepsGraph) else None
    raw = load_config(root).raw
    settings = QualitySettings.from_raw(raw)
    adr_dir = str(((raw.get("adr") or {}).get("output_dir")) or "docs/adr")
    titel = {k: str(v.get("title", "")) for k, v in adr_titles(root, adr_dir).items()}
    grund = None if graph else f"Sonde {probe.name}: {outcome.reason}"
    return evaluate_architecture(arch, graph, settings, adr_titles=titel, baseline=baseline,
                                 root=root, graph_reason=grund), baseline, grund


@arch_group.command("check", help="Wertet die Architekturregeln aus (Exit 1 bei error-Verstößen).")
@click.option("--json", "as_json", is_flag=True, help="Objekt 'architecture' des Reports ausgeben.")
@click.option("--write-baseline", is_flag=True, help="Aktuelle error-Verstöße in die Baseline übernehmen.")
def arch_check(as_json, write_baseline) -> None:
    root = _root()
    result, baseline, grund = _arch_auswerten(root)
    if grund:
        err.print(f"[red]✗[/] Abhängigkeiten nicht messbar – {grund}")
        sys.exit(2)
    if write_baseline:
        neu = baseline.merged_with(result.violations)
        hinzu = neu.entries[len(baseline.entries):]
        neu.write(root)
        for e in hinzu:
            err.print(f"+ {e['rule']} {e['file']} {e['symbol']} (reason: TODO)")
        console.print(f"[green]✓[/] Baseline geschrieben: {len(neu.entries)} Einträge "
                      f"({len(hinzu)} neu)")
        sys.exit(0)
    if as_json:
        click.echo(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        for v in result.violations:
            art = (f"warn (Baseline, {v.fixed_by})" if v.fixed_by else "warn (Baseline)") \
                if v.baselined else v.severity
            farbe = "yellow" if v.severity == "warn" else "red"
            console.print(f"[{farbe}]{art}[/] {v.rule} {v.file}:{v.line} {v.symbol} – "
                          f"{v.adr} {v.adr_title or ''}".rstrip(), soft_wrap=True)
        for na in result.rules_na:
            console.print(f"[yellow]n/a[/] {na['rule']}: {na['reason']}", soft_wrap=True)
        if result.stale_baseline_entries:
            console.print(f"[cyan]i[/] Baseline kann bereinigt werden "
                          f"({result.stale_baseline_entries} veraltete Einträge)")
        if not result.violations:
            console.print("[green]✓[/] Keine Architekturverstöße.")
    sys.exit(1 if result.errors else 0)


@arch_group.command("init", help="Schlägt .sdd/architecture.yaml mit Schichten vor (ohne Regeln).")
def arch_init() -> None:
    from .quality.arch.init import suggest_architecture
    from .quality.presets import InstallResult, write_or_propose

    root = _root()
    result = InstallResult()
    write_or_propose(root, ".sdd/architecture.yaml",
                     yaml.safe_dump(suggest_architecture(root), sort_keys=False,
                                    allow_unicode=True), result)
    _schreibbericht(result)
