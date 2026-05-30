"""Click-basierte Befehle der sdd-CLI."""
from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from .config import load_config, find_project_root
from .frontmatter import parse, parse_safe
from .ids import next_id
from .init import init_project
from .upgrade import upgrade_project
from .templates import (
    load_template,
    render,
    slugify,
    copy_skeleton,
    CONTRACT_TEMPLATES,
)
from .validate import validate
from .traceability import write_matrix
from .evaluator import run_evaluation, persist_report
from .orchestrator import run_pipeline, persist_pipeline_report
from .projects import list_projects, load_project, set_autonomy_level, VALID_AUTONOMY_LEVELS
from .autonomy import compute_level_stats, level_label, LEVEL_CRITERIA
from .maintenance import run_maintenance_sweep
from .ui import start_server
from . import test_runner as _test_runner

console = Console()


@click.group(help="Spec-Driven Development CLI")
@click.version_option(__version__)
def cli() -> None:
    pass


# ─────────────────────────────────────────────────────────────────────────────
# sdd init
# ─────────────────────────────────────────────────────────────────────────────
@cli.command(help="Initialisiert die SDD-Struktur im aktuellen oder angegebenen Verzeichnis.")
@click.option("--path", "target", default=".", help="Zielverzeichnis (Default: aktuelles).")
@click.option("--title", "--name", "project_title", default="", help="Projekttitel (Default: Ordnername).")
@click.option("--force", is_flag=True, help="Überschreibt vorhandene Dateien.")
@click.option("--provider", default="claude", show_default=True,
              help="Skill-Provider für AI-Assistenten-Integration. "
                   "Verfügbar: claude, copilot, openai.")
@click.option("--force-skills", is_flag=True,
              help="Überschreibt vorhandene Skill-Dateien im Ziel-Projekt (SPEC-0018 FR-03).")
def init(target: str, project_title: str, force: bool,
         provider: str, force_skills: bool) -> None:
    from .init import get_skill_provider, SKILL_PROVIDERS
    try:
        prov = get_skill_provider(provider)
    except ValueError as exc:
        console.print(f"[red]✗[/] {exc}")
        sys.exit(1)

    title = project_title or Path(target).resolve().name

    result = init_project(
        Path(target), title,
        force=force,
        skill_provider=provider,
        force_skills=force_skills,
    )

    n_core = len(result["created"])
    n_skills = len(result["skill_created"])
    n_skipped = len(result["skill_skipped"])

    console.print(f"[green]✓[/] SDD-Projekt initialisiert in [bold]{Path(target).resolve()}[/].")
    console.print(f"  {n_core} Kern-Pfade erstellt/kopiert.")

    if n_skills:
        console.print(
            f"  [green]+[/] {n_skills} Skill-Datei(en) → "
            f"[bold]{prov.target_dir}/[/]  [{prov.description}]"
        )
    if n_skipped:
        console.print(
            f"  [yellow]~[/] {n_skipped} Skill-Datei(en) übersprungen "
            f"(bereits vorhanden – nutze [cyan]--force-skills[/] zum Überschreiben)"
        )
    if not n_skills and not n_skipped:
        console.print(
            f"  [dim]Keine Skill-Dateien für Provider '{provider}' gefunden "
            f"(Vorlagen fehlen in .sdd/templates/agents-md/{prov.source_subdir}/)[/]"
        )

    config_path = Path(target).resolve() / ".sdd" / "config.yaml"
    from .config_wizard import ConfigWizard
    from .config_manager import ConfigManager
    cfg_data = ConfigManager(config_path).load()
    if ConfigWizard.needs_setup(cfg_data):
        console.print(
            "\n[yellow]⚙[/] Die Projektkonfiguration ist noch nicht vollständig. "
            "Soll der Konfigurations-Wizard jetzt gestartet werden? [J/n] ",
            end="",
        )
        try:
            answer = input("").strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = "n"
        if not answer or answer.startswith("j") or answer.startswith("y"):
            wizard = ConfigWizard(config_path)
            try:
                wizard.run()
                console.print("[green]✓[/] Konfiguration gespeichert.")
            except Exception as exc:
                console.print(f"[yellow]⚠[/] Wizard abgebrochen: {exc}")
                console.print("  Jederzeit nachholen: [cyan]sdd config wizard[/]")
        else:
            console.print("  Jederzeit nachholen: [cyan]sdd config wizard[/]")

    console.print("\nNächste Schritte:")
    console.print("  1. [cyan]sdd new spec \"Mein erstes Feature\"[/]")
    console.print("  2. [cyan]sdd new contract --spec SPEC-0001 --format openapi[/]")
    console.print("  3. [cyan]sdd new test --spec SPEC-0001 --contract CON-0001 --level contract[/]")
    console.print("  4. [cyan]sdd validate[/]")
    if n_skills:
        console.print(f"  5. [cyan]/sdd[/]  (in Claude Code – Projektübersicht)")


# ─────────────────────────────────────────────────────────────────────────────
# sdd upgrade
# ─────────────────────────────────────────────────────────────────────────────
@cli.command(help="Aktualisiert ein bestehendes SDD-Projekt auf die aktuelle Paket-Version.")
@click.option("--path", "target", default=".", help="Projektverzeichnis (Default: aktuelles).")
@click.option("--verbose", "-v", is_flag=True, help="Zeigt jede geänderte Datei.")
def upgrade(target: str, verbose: bool) -> None:
    target_path = Path(target).resolve()
    config_file = target_path / ".sdd" / "config.yaml"
    if not config_file.exists():
        console.print(f"[red]✗[/] Kein SDD-Projekt gefunden in [bold]{target_path}[/] (.sdd/config.yaml fehlt).")
        console.print("  Initialisiere zuerst mit: [cyan]sdd init[/]")
        sys.exit(1)

    console.print(f"[bold]SDD Upgrade[/] → [bold]{target_path}[/]")
    result = upgrade_project(target_path, verbose=verbose)

    n_created = len(result["created"])
    n_updated = len(result["updated"])
    n_skipped = len(result["skipped"])

    if n_created > 0:
        console.print(f"  [green]+[/] {n_created} neue Dateien/Verzeichnisse erstellt")
    if n_updated > 0:
        console.print(f"  [cyan]↺[/] {n_updated} Dateien aktualisiert (Schemas)")
    if n_skipped > 0 and verbose:
        console.print(f"  [dim]○ {n_skipped} Dateien unverändert[/]")

    if n_created == 0 and n_updated == 0:
        console.print("[green]✓[/] Projekt ist bereits auf dem neuesten Stand.")
    else:
        console.print(f"\n[green]✓[/] Upgrade abgeschlossen.")
        console.print("\nHinweis: Spec/Contract/Test-Dateien wurden [bold]nicht[/] verändert.")
        console.print("Prüfe die aktualisierte config.yaml auf neue Sektionen:")
        console.print(f"  [cyan]{config_file}[/]")


# ─────────────────────────────────────────────────────────────────────────────
# sdd new …
# ─────────────────────────────────────────────────────────────────────────────
@cli.group(help="Neue Specs, Contracts, Tests oder ADRs anlegen.")
def new() -> None:
    pass


def _ensure_project() -> "object":
    try:
        return load_config()
    except FileNotFoundError as e:
        console.print(f"[red]✗[/] {e}")
        sys.exit(1)


@new.command("spec", help="Legt eine neue Spec an (feature oder bug-fix).")
@click.argument("title")
@click.option("--owner", default="", help="Owner-Eintrag im Frontmatter.")
@click.option("--type", "spec_type", default="feature",
              type=click.Choice(["feature", "bug-fix"]),
              show_default=True,
              help="Spec-Typ: 'feature' für neue Funktionalität, 'bug-fix' für Fehlerbehebung.")
def new_spec(title: str, owner: str, spec_type: str) -> None:
    cfg = _ensure_project()
    sid = next_id(cfg, "spec")
    slug = slugify(title)
    target = cfg.specs_dir / f"{sid}-{slug}.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    tmpl_key = "spec-bug-fix" if spec_type == "bug-fix" else "spec"
    tmpl, _ = load_template(cfg, tmpl_key)
    text = render(tmpl, {"id": sid, "title": title, "owner": owner})
    target.write_text(text, encoding="utf-8")

    label = "[red]Bug-Fix[/]" if spec_type == "bug-fix" else "[blue]Feature[/]"
    console.print(f"[green]✓[/] {label}-Spec angelegt: [bold]{target}[/]  ([cyan]{sid}[/])")
    if spec_type == "bug-fix":
        console.print(
            "  [yellow]→[/] Beschreibe nur das [bold]Symptom[/] – "
            "keine Root-Cause-Annahmen. Der Agent untersucht die Codebasis selbst."
        )


@new.command("contract", help="Legt einen neuen Contract an, verknüpft mit einer Spec.")
@click.option("--spec", "spec_id", required=True, help="Zugehörige Spec-ID, z.B. SPEC-0001.")
@click.option("--format", "fmt", required=True,
              type=click.Choice(list(CONTRACT_TEMPLATES.keys())),
              help="Contract-Format.")
@click.option("--title", default="", help="Titel des Contracts.")
def new_contract(spec_id: str, fmt: str, title: str) -> None:
    cfg = _ensure_project()
    cid = next_id(cfg, "contract")
    slug = slugify(title or fmt)

    # Zielverzeichnis nach Typ
    subdir_map = {
        "openapi": "api", "asyncapi": "api", "graphql": "api", "grpc": "api",
        "json-schema": "data", "avro": "data", "protobuf": "data",
        "gherkin": "behavior", "markdown": "behavior",
        "slo-yaml": "performance",
    }
    subdir = subdir_map[fmt]
    target = cfg.contracts_dir / subdir / f"{cid}-{slug}.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    # Artifact-Pfad bestimmen
    ext_map = {
        "openapi": "openapi.yaml", "asyncapi": "asyncapi.yaml",
        "graphql": "graphql", "grpc": "proto",
        "json-schema": "schema.json", "avro": "avsc", "protobuf": "proto",
        "gherkin": "feature", "markdown": "md",
        "slo-yaml": "slo.yaml",
    }
    artifact_rel = f".sdd/contracts/{subdir}/{slug}.{ext_map[fmt]}"

    tmpl, skeleton = load_template(cfg, "contract", contract_format=fmt)
    text = render(tmpl, {
        "id": cid, "title": title or f"{fmt} contract",
        "spec": spec_id, "artifact": artifact_rel,
    })
    target.write_text(text, encoding="utf-8")

    if skeleton:
        copy_skeleton(cfg, skeleton, cfg.root / artifact_rel)

    console.print(f"[green]✓[/] Contract angelegt: [bold]{target}[/]  ([cyan]{cid}[/])")
    if skeleton:
        console.print(f"  Artifact-Skeleton: [dim]{artifact_rel}[/]")

    # Test-Stub automatisch mitanlegen
    tid = next_id(cfg, "test")
    test_level = "contract"
    test_target = cfg.tests_dir / test_level / f"{tid}-{slug}.md"
    test_target.parent.mkdir(parents=True, exist_ok=True)
    tmpl_test, _ = load_template(cfg, "test")
    test_text = render(tmpl_test, {
        "id": tid, "title": title or f"{fmt} contract test",
        "spec": spec_id, "contract": cid,
    })
    test_target.write_text(test_text, encoding="utf-8")

    # tests: [] im Contract-File auf die neue ID patchen
    contract_text = target.read_text(encoding="utf-8")
    # FR-03 (SPEC-0010): neuer Contract erhält direkt Status review
    contract_text = contract_text.replace("\nstatus: draft\n", "\nstatus: review\n", 1)
    target.write_text(contract_text.replace('tests: []', f'tests: ["{tid}"]', 1), encoding="utf-8")

    console.print(f"[green]✓[/] Test-Stub angelegt:  [bold]{test_target}[/]  ([cyan]{tid}[/])")
    console.print(
        f"\n  [yellow]→[/] Fülle [bold]{test_target.name}[/] aus – oder lass dein LLM helfen:\n"
        f"  [dim]\"Fülle {tid} für {cid} aus. Spec: {spec_id}. "
        f"Format: {fmt}. Beschreibe Vorbedingungen, Ablauf und Erwartetes Ergebnis.\"[/]"
    )
    _hint_link_in_spec(spec_id, "contracts", cid)
    _hint_link_in_spec(spec_id, "tests", tid)


@new.command("test", help="Legt einen neuen Test an, verknüpft mit Spec und Contract.")
@click.option("--spec", "spec_id", required=True)
@click.option("--contract", "contract_id", required=True)
@click.option("--level", required=True,
              type=click.Choice(["unit", "integration", "contract", "acceptance",
                                 "performance", "property"]))
@click.option("--title", default="")
def new_test(spec_id: str, contract_id: str, level: str, title: str) -> None:
    cfg = _ensure_project()
    tid = next_id(cfg, "test")
    slug = slugify(title or level)
    target = cfg.tests_dir / level / f"{tid}-{slug}.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    tmpl, _ = load_template(cfg, "test")
    text = render(tmpl, {
        "id": tid, "title": title or f"{level} test",
        "spec": spec_id, "contract": contract_id,
    })
    # level im Frontmatter setzen
    text = text.replace("level: contract", f"level: {level}", 1)
    target.write_text(text, encoding="utf-8")

    console.print(f"[green]✓[/] Test angelegt: [bold]{target}[/]  ([cyan]{tid}[/])")
    _hint_link_in_spec(spec_id, "tests", tid)


@new.command("holdout", help="Legt ein neues Holdout-Szenario an (HOL-XXXX, isoliert vom Code-Agenten).")
@click.option("--contract", "contract_id", required=True,
              help="Zugehöriger Contract, z.B. CON-0001.")
@click.option("--spec", "spec_id", required=True,
              help="Zugehörige Spec, z.B. SPEC-0004.")
@click.option("--title", required=True, help="Titel des Holdout-Szenarios.")
def new_holdout(contract_id: str, spec_id: str, title: str) -> None:
    cfg = _ensure_project()
    hid = next_id(cfg, "holdout")
    slug = slugify(title)
    target = cfg.holdout_dir / f"{hid}-{slug}.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    tmpl, _ = load_template(cfg, "holdout")
    text = render(tmpl, {
        "id": hid, "title": title,
        "contract": contract_id, "spec": spec_id,
    })
    target.write_text(text, encoding="utf-8")

    console.print(f"[green]✓[/] Holdout-Szenario angelegt: [bold]{target}[/]  ([cyan]{hid}[/])")
    console.print(
        f"  [yellow]→[/] Datei ist in [bold].sdd/holdout/[/] – für den Code-Agenten nicht sichtbar."
    )


@new.command("agents-md", help="Generiert ein AGENTS.md-Skeleton im Projekt-Root oder einem Unterverzeichnis.")
@click.option("--subdir", default="", help="Unterverzeichnis für Subkomponenten-AGENTS.md, z.B. 'services/auth'.")
@click.option("--force", is_flag=True, help="Überschreibt eine vorhandene AGENTS.md.")
def new_agents_md(subdir: str, force: bool) -> None:
    cfg = _ensure_project()
    base = (cfg.root / subdir) if subdir else cfg.root
    target = base / "AGENTS.md"
    if target.exists() and not force:
        console.print(f"[yellow]⚠[/] AGENTS.md existiert bereits: [bold]{target}[/]")
        console.print("  Verwende [cyan]--force[/] um zu überschreiben.")
        return

    base.mkdir(parents=True, exist_ok=True)
    tmpl, _ = load_template(cfg, "agents-md")
    target.write_text(tmpl, encoding="utf-8")
    console.print(f"[green]✓[/] AGENTS.md angelegt: [bold]{target}[/]")
    if subdir:
        console.print(f"  Subkomponente: [cyan]{subdir}[/] – beschreibe hier nur diesen Teil des Systems.")
    console.print("  Fülle alle Sektionen aus – das Dokument gibt dem Code-Agenten seinen Kontext.")


@new.command("github-workflow", help="Generiert einen GitHub-Actions-Workflow für sdd orchestrate.")
def new_github_workflow() -> None:
    cfg = _ensure_project()
    tmpl, _ = load_template(cfg, "github-actions")
    target = cfg.root / ".github" / "workflows" / "sdd-orchestrate.yml"
    if target.exists():
        console.print(f"[yellow]⚠[/] Workflow existiert bereits: [bold]{target}[/]")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(tmpl, encoding="utf-8")
    console.print(f"[green]✓[/] GitHub-Actions-Workflow angelegt: [bold]{target}[/]")
    console.print("  Trage [cyan]ANTHROPIC_API_KEY[/] als GitHub-Secret ein.")


@new.command("adr", help="Legt eine neue Architecture Decision Record an.")
@click.argument("title")
def new_adr(title: str) -> None:
    cfg = _ensure_project()
    aid = next_id(cfg, "adr")
    slug = slugify(title)
    target = cfg.adr_dir / f"{aid}-{slug}.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    tmpl, _ = load_template(cfg, "adr")
    text = render(tmpl, {"id": aid, "title": title})
    target.write_text(text, encoding="utf-8")

    console.print(f"[green]✓[/] ADR angelegt: [bold]{target}[/]  ([cyan]{aid}[/])")


def _hint_link_in_spec(spec_id: str, key: str, new_id: str) -> None:
    """Hinweis, dass die neue ID noch in die Spec eingetragen werden muss."""
    console.print(
        f"  [yellow]→[/] Trage [cyan]{new_id}[/] in der Spec [bold]{spec_id}[/] "
        f"unter [italic]{key}:[/] ein, sonst schlägt [cyan]sdd validate[/] fehl."
    )


# ─────────────────────────────────────────────────────────────────────────────
# sdd validate
# ─────────────────────────────────────────────────────────────────────────────
@cli.command(help="Validiert Frontmatter, Verknüpfungen und Konsistenz.")
@click.option("--strict", is_flag=True, help="Warnungen als Fehler behandeln.")
@click.option("--instruct", is_flag=True,
              help="Gibt maschinenlesbare Korrektur-Anweisungen als JSON aus (für Agenten).")
def validate_cmd(strict: bool, instruct: bool) -> None:
    cfg = _ensure_project()
    report = validate(cfg)

    if instruct:
        import json as _json
        issues = [i.to_dict(cfg.root) for i in report.issues]
        sys.stdout.write(_json.dumps({"issues": issues, "ok": report.ok}, indent=2,
                                     ensure_ascii=False) + "\n")
        sys.stdout.flush()
        fail = bool(report.errors) or (strict and bool(report.warnings))
        sys.exit(1 if fail else 0)

    if report.errors:
        console.print(f"[red]✗ {len(report.errors)} Fehler gefunden:[/]")
        for issue in report.errors:
            console.print(issue.format(cfg.root))
    if report.warnings:
        console.print(f"[yellow]⚠ {len(report.warnings)} Warnungen:[/]")
        for issue in report.warnings:
            console.print(issue.format(cfg.root))

    if not report.errors and not report.warnings:
        console.print("[green]✓ Alles in Ordnung.[/]")

    fail = bool(report.errors) or (strict and bool(report.warnings))
    sys.exit(1 if fail else 0)


# click reserviert den Namen `validate` als Methode, daher Mapping:
cli.add_command(validate_cmd, name="validate")


# ─────────────────────────────────────────────────────────────────────────────
# sdd trace
# ─────────────────────────────────────────────────────────────────────────────
@cli.command(help="Generiert die Traceability-Matrix Spec ↔ Contract ↔ Test.")
def trace() -> None:
    cfg = _ensure_project()
    path = write_matrix(cfg)
    console.print(f"[green]✓[/] Traceability-Matrix aktualisiert: [bold]{path.relative_to(cfg.root)}[/]")


# ─────────────────────────────────────────────────────────────────────────────
# sdd evaluate
# ─────────────────────────────────────────────────────────────────────────────
@cli.command(help="Führt Holdout-Szenarien gegen einen laufenden Service aus (Evaluator).")
@click.option("--base-url", required=True, envvar="SDD_EVAL_BASE_URL",
              help="Basis-URL des zu testenden Services, z.B. http://localhost:8080.")
@click.option("--hol", "hol_ids", multiple=True,
              help="Einschränkung auf bestimmte HOL-IDs (wiederholbar). Default: alle aktiven.")
@click.option("--save/--no-save", default=True,
              help="Report in .sdd/evaluations/ persistieren (Default: ja).")
@click.option("--json", "output_json", is_flag=True,
              help="Report als JSON ausgeben statt als Rich-Tabelle.")
@click.option("--spec", "spec_id", default=None,
              help="SPEC-ID – bei finalem Fehlschlag wird Status auf evaluation-failed gesetzt.")
@click.option("--final-attempt", is_flag=True,
              help="Letzter Retry-Versuch – setzt SPEC auf evaluation-failed wenn Tests nicht grün.")
def evaluate_cmd(base_url: str, hol_ids: tuple, save: bool, output_json: bool,
                 spec_id: str | None, final_attempt: bool) -> None:
    cfg = _ensure_project()

    ids_filter = list(hol_ids) if hol_ids else None
    console.print(f"[cyan]▶[/] Evaluator startet gegen [bold]{base_url}[/] …")

    try:
        report = run_evaluation(cfg, base_url, hol_ids=ids_filter, spec_id=spec_id)
    except RuntimeError as e:
        console.print(f"[red]✗[/] {e}")
        sys.exit(1)

    report_path = None
    if save:
        report_path = persist_report(cfg, report)
        console.print(f"[dim]  Report gespeichert: {report_path.relative_to(cfg.root)}[/]")

    passed = report.pass_rate >= 0.9

    if output_json:
        import json as _json
        console.print(_json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        if not passed and final_attempt and spec_id:
            _set_evaluation_failed(cfg, spec_id, report_path)
        sys.exit(0 if passed else 1)

    # Rich-Ausgabe
    from rich.table import Table
    table = Table(title=f"Evaluator-Report · {report.timestamp[:19]}")
    table.add_column("HOL-ID", style="cyan")
    table.add_column("Titel")
    table.add_column("Contract")
    table.add_column("Runs", justify="right")
    table.add_column("Ergebnis")

    for s in report.scenarios:
        result_text = f"[green]✓ PASS ({s.pass_count}/{len(s.runs)})[/]" if s.passed \
            else f"[red]✗ FAIL ({s.pass_count}/{len(s.runs)})[/]"
        table.add_row(s.hol_id, s.title, s.contract,
                      str(len(s.runs)), result_text)

    console.print(table)
    rate_color = "green" if passed else "red"
    console.print(
        f"\n[{rate_color}]Pass-Rate: {report.passed}/{report.total} "
        f"({report.pass_rate:.0%})[/]"
        + (" · [green]Auto-Merge-Schwelle erreicht ✓[/]" if passed
           else " · [red]Unter 90 % – kein Auto-Merge[/]")
    )

    if not passed and final_attempt and spec_id:
        _set_evaluation_failed(cfg, spec_id, report_path)
        console.print(
            f"\n[red bold]✗ Evaluation nach 3 Versuchen fehlgeschlagen.[/]\n"
            f"  SPEC [cyan]{spec_id}[/] → [red]evaluation-failed[/]\n"
            f"  Report: [dim]{report_path}[/]\n"
            f"  Nächster Schritt: Spec überarbeiten oder Holdout-Kriterien anpassen."
        )

    sys.exit(0 if passed else 1)


def _set_evaluation_failed(cfg: SddConfig, spec_id: str, report_path: Path | None) -> None:
    try:
        from .lifecycle import mark_evaluation_failed
        mark_evaluation_failed(cfg, spec_id, report_path or Path("(nicht gespeichert)"))
    except ValueError as e:
        console.print(f"[yellow]![/] Status-Update fehlgeschlagen: {e}")


cli.add_command(evaluate_cmd, name="evaluate")


# ─────────────────────────────────────────────────────────────────────────────
# sdd orchestrate
# ─────────────────────────────────────────────────────────────────────────────
@cli.command(help="Führt die Dark-Factory-Pipeline aus: Spec → Code → PR → Eval → Retry.")
@click.option("--spec", "spec_id", required=True, help="Spec-ID, z.B. SPEC-0004.")
@click.option("--base-url", default=None, envvar="SDD_EVAL_BASE_URL",
              help="Basis-URL des Services für den Evaluator-Schritt.")
@click.option("--build-cmd", default=None,
              help="Build + Test-Kommando. Überschreibt orchestrator.build_command in config.yaml.")
@click.option("--max-retries", default=3, show_default=True,
              help="Max. Versuche bei Fehlschlag.")
@click.option("--no-pr", is_flag=True, help="PR-Erstellung überspringen.")
@click.option("--dry-run", is_flag=True,
              help="Zeigt generierten Code, schreibt/committed/pushed nicht.")
@click.option("--save/--no-save", default=True,
              help="Report in .sdd/pipeline/ persistieren.")
@click.option("--project", "project_id", default="",
              help="Projekt-ID für Autonomy-Level-Tracking und evaluations.db.")
@click.option("--resume", is_flag=True,
              help="Setzt Retry-Zähler zurück (nach manuellem Review). Startet neuen Zyklus.")
def orchestrate_cmd(spec_id: str, base_url: str | None, build_cmd: str | None,
                    max_retries: int, no_pr: bool, dry_run: bool, save: bool,
                    project_id: str, resume: bool) -> None:
    cfg = _ensure_project()

    if resume and project_id:
        from .autonomy import record_resume_event
        record_resume_event(cfg, pr_number=spec_id, triggered_by="cli")
        console.print(f"[yellow]↺[/] Resume-Event für [bold]{spec_id}[/] geloggt.")

    mode = "[yellow]dry-run[/]" if dry_run else "[cyan]live[/]"
    console.print(f"[cyan]▶[/] Orchestrator startet für [bold]{spec_id}[/] ({mode}) …")

    try:
        report = run_pipeline(
            cfg, spec_id,
            base_url=base_url,
            build_cmd=build_cmd,
            max_retries=max_retries,
            no_pr=no_pr,
            dry_run=dry_run,
            project_id=project_id,
        )
    except (ValueError, RuntimeError) as e:
        console.print(f"[red]✗[/] {e}")
        sys.exit(1)

    if save and not dry_run:
        path = persist_pipeline_report(cfg, report)
        console.print(f"[dim]  Report gespeichert: {path.relative_to(cfg.root)}[/]")

    status_color = {
        "merged": "bold green", "labeled": "green",
        "failed": "red", "dry_run": "yellow",
    }.get(report.final_status, "white")

    for a in report.attempts:
        pr = f" · PR: {a.pr_url}" if a.pr_url else ""
        eval_str = f" · Eval: {a.eval_pass_rate:.0%}" if a.eval_pass_rate is not None else ""
        build_str = " · Build: ✓" if a.build_passed else (" · Build: ✗" if a.build_passed is False else "")
        console.print(f"  Attempt {a.attempt}: {a.explanation}{build_str}{eval_str}{pr}")
        if a.error:
            console.print(f"    [dim red]{a.error[:120]}[/]")

    console.print(f"\n[{status_color}]Status: {report.final_status.upper()}[/]")
    sys.exit(0 if report.final_status in ("merged", "labeled", "dry_run") else 1)


cli.add_command(orchestrate_cmd, name="orchestrate")


# ─────────────────────────────────────────────────────────────────────────────
# sdd status
# ─────────────────────────────────────────────────────────────────────────────
@cli.command(help="Zeigt eine Übersicht aller Specs mit Status und Coverage.")
def status() -> None:
    cfg = _ensure_project()

    specs = sorted(
        [parse_safe(p) for p in cfg.specs_dir.rglob("*.md")
         if parse_safe(p) and parse_safe(p).frontmatter.get("id")],
        key=lambda d: d.frontmatter["id"],
    )

    table = Table(title="SDD-Projekt-Status", show_lines=False)
    table.add_column("Spec-ID", style="cyan")
    table.add_column("Titel")
    table.add_column("Status")
    table.add_column("Contracts", justify="right")
    table.add_column("Tests", justify="right")

    status_color = {
        "draft": "white",
        "review": "yellow",
        "approved": "green",
        "in-progress": "cyan",
        "implemented": "bold green",
        "deprecated": "dim red",
    }
    for s in specs:
        fm = s.frontmatter
        st = fm.get("status", "?")
        color = status_color.get(st, "white")
        table.add_row(
            fm.get("id", "?"),
            fm.get("title", ""),
            f"[{color}]{st}[/]",
            str(len(fm.get("contracts") or [])),
            str(len(fm.get("tests") or [])),
        )
    console.print(table)


# ─────────────────────────────────────────────────────────────────────────────
# sdd mark-false-positive
# ─────────────────────────────────────────────────────────────────────────────
@cli.command("mark-false-positive",
             help="Markiert einen PR als False Positive (manuell gereverted/gefixt).")
@click.argument("pr_number")
@click.option("--project", "project_id", required=True,
              help="Projekt-ID, z.B. PRJ-0001.")
def mark_false_positive_cmd(pr_number: str, project_id: str) -> None:
    cfg = _ensure_project()
    from .autonomy import record_false_positive
    record_false_positive(cfg, project_id, pr_number)
    console.print(
        f"[yellow]⚠[/] PR [bold]{pr_number}[/] als False Positive markiert "
        f"(Projekt [cyan]{project_id}[/])."
    )
    console.print(
        "  Die Override-Rate wird beim nächsten [cyan]sdd level[/]-Aufruf aktualisiert."
    )


# ─────────────────────────────────────────────────────────────────────────────
# sdd set-level
# ─────────────────────────────────────────────────────────────────────────────
@cli.command("set-level", help="Setzt das Autonomy Level eines Projekts (1|2|3|3.5|4).")
@click.argument("project_id")
@click.argument("level", type=float)
def set_level_cmd(project_id: str, level: float) -> None:
    cfg = _ensure_project()
    try:
        project = set_autonomy_level(cfg, project_id, level)
    except ValueError as e:
        console.print(f"[red]✗[/] {e}")
        sys.exit(1)

    label = level_label(level)
    console.print(
        f"[green]✓[/] [bold]{project_id}[/] → [cyan]{label}[/]"
    )
    crit = LEVEL_CRITERIA.get(level, {})
    if crit.get("auto_merge"):
        console.print("  Auto-Merge: [green]aktivierbar[/] (wenn Pass-Rate + Min. PRs erreicht)")
    else:
        console.print("  Auto-Merge: [dim]nicht erlaubt auf diesem Level[/]")


# ─────────────────────────────────────────────────────────────────────────────
# sdd level
# ─────────────────────────────────────────────────────────────────────────────
@cli.command("level", help="Zeigt Autonomy-Level-Metriken und Upgrade-/Downgrade-Vorschläge.")
@click.argument("project_id")
def level_cmd(project_id: str) -> None:
    cfg = _ensure_project()
    project = load_project(cfg, project_id)
    if project is None:
        console.print(f"[red]✗[/] Projekt nicht gefunden: {project_id}")
        sys.exit(1)

    stats = compute_level_stats(cfg, project_id, project.autonomy_level)

    console.print(f"\n[bold]{project.name}[/] ([cyan]{project_id}[/])")
    console.print(f"  Autonomy Level: [bold cyan]{level_label(stats.current_level)}[/]")
    console.print(f"  Gesamt PRs:     {stats.total_prs}")

    if stats.total_prs > 0:
        rate_color = "green" if stats.pass_rate >= 0.9 else ("yellow" if stats.pass_rate >= 0.7 else "red")
        console.print(f"  Pass-Rate:      [{rate_color}]{stats.pass_rate:.0%}[/]")
        console.print(f"  Override-Rate:  {stats.override_rate:.0%}")

    if stats.auto_merge_blocked:
        console.print("  Auto-Merge:     [red]BLOCKIERT[/] (Pass-Rate unter Schwellwert)")
    elif stats.current_level >= 3.5:
        console.print("  Auto-Merge:     [green]freigegeben[/]")

    if stats.upgrade_proposal is not None:
        console.print(
            f"\n  [green]▲ Upgrade-Vorschlag:[/] Level {stats.upgrade_proposal} — "
            f"{LEVEL_CRITERIA[stats.upgrade_proposal]['label']}\n"
            f"    Alle Schwellwerte erfüllt. Bestätige mit: "
            f"[cyan]sdd set-level {project_id} {stats.upgrade_proposal}[/]"
        )

    if stats.downgrade_proposal is not None:
        console.print(
            f"\n  [yellow]▼ Downgrade-Vorschlag:[/] Level {stats.downgrade_proposal} — "
            f"{LEVEL_CRITERIA[stats.downgrade_proposal]['label']}\n"
            f"    {stats.consecutive_below_threshold} aufeinanderfolgende PRs unter Schwellwert.\n"
            f"    Bestätige mit: [cyan]sdd set-level {project_id} {stats.downgrade_proposal}[/]"
        )

    # Level-Kriterien-Übersicht
    table = Table(title="Level-Kriterien", show_lines=False, box=None)
    table.add_column("Level", style="cyan", width=6)
    table.add_column("Bezeichnung")
    table.add_column("Min. Pass-Rate", justify="right")
    table.add_column("Min. PRs", justify="right")
    table.add_column("Auto-Merge")

    for lvl, crit in sorted(LEVEL_CRITERIA.items()):
        active = "► " if lvl == stats.current_level else "  "
        table.add_row(
            f"{active}{lvl}",
            crit["label"],
            f"{crit['min_pass_rate']:.0%}" if crit["min_pass_rate"] > 0 else "—",
            str(crit["min_prs"]) if crit["min_prs"] > 0 else "—",
            "[green]ja[/]" if crit["auto_merge"] else "[dim]nein[/]",
        )
    console.print()
    console.print(table)


# ─────────────────────────────────────────────────────────────────────────────
# sdd maintenance
# ─────────────────────────────────────────────────────────────────────────────
@cli.command(help="Drift-Sweep: veraltete Specs, fehlende Contracts und Tests aufspüren.")
@click.option("--json", "output_json", is_flag=True,
              help="Ausgabe als JSON (maschinenlesbar).")
@click.option("--auto-pr", is_flag=True,
              help="Startet sdd orchestrate für jede veraltete Spec (öffnet Cleanup-PR).")
@click.option("--spec", "spec_id", default=None,
              help="Einschränkung auf eine einzelne Spec-ID.")
def maintenance_cmd(output_json: bool, auto_pr: bool, spec_id: str | None) -> None:
    cfg = _ensure_project()
    sweep = run_maintenance_sweep(cfg)

    if spec_id:
        sweep.issues = [i for i in sweep.issues if i.spec_id == spec_id]

    if output_json:
        import json as _json
        console.print(_json.dumps(sweep.to_dict(cfg.root), indent=2, ensure_ascii=False))
        sys.exit(0 if not sweep.issues else 1)

    stale_count = len(sweep.stale)
    drift_count = len(sweep.drift)

    console.print(
        f"\n[bold]Maintenance-Sweep[/] · "
        f"Stale-Grenze: [cyan]{sweep.stale_after_weeks} Wochen[/]"
    )

    if not sweep.issues:
        console.print("[green]✓ Keine Drift-Probleme gefunden.[/]")
        sys.exit(0)

    if stale_count:
        console.print(f"\n[yellow]⏰ {stale_count} veraltete Spec(s):[/]")
        for issue in sweep.stale:
            console.print(issue.format(cfg.root))
            console.print(f"    [dim]→ {issue.action}[/]")

    if drift_count:
        console.print(f"\n[red]⚠ {drift_count} Drift-Problem(e):[/]")
        for issue in sweep.drift:
            console.print(issue.format(cfg.root))
            console.print(f"    [dim]→ {issue.action}[/]")

    if auto_pr and sweep.stale:
        console.print("\n[cyan]▶[/] Starte Orchestrator für veraltete Specs …")
        for issue in sweep.stale:
            console.print(f"  [dim]{issue.spec_id}[/] …")
            try:
                report = run_pipeline(cfg, issue.spec_id)
                color = "green" if report.final_status in ("merged", "labeled") else "red"
                console.print(
                    f"  [{color}]{issue.spec_id}: {report.final_status.upper()}[/]"
                )
            except Exception as exc:
                console.print(f"  [red]✗ {issue.spec_id}: {exc}[/]")

    sys.exit(0 if not sweep.issues else 1)


# ─────────────────────────────────────────────────────────────────────────────
# sdd ui
# ─────────────────────────────────────────────────────────────────────────────
@cli.command(help="Startet den SDD Web UI Server. Mit --watch: Vite Dev Server + HMR.")
@click.option("--project", "project_root", default=".",
              help="SDD-Projektverzeichnis (Default: aktuelles).")
@click.option("--port", default=0, show_default=True,
              help="Port für den Server (nur ohne --watch). 0 = freier Port automatisch.")
@click.option("--watch", is_flag=True,
              help="Watch-Modus: Vite Dev Server (Port 5173) + FastAPI (Port 8000) mit Auto-Reload.")
@click.option("--no-browser", is_flag=True,
              help="Browser nicht automatisch öffnen.")
@click.option("--external-url", "external_url", default="",
              help="Externe URL für QR-Code (z.B. http://192.168.1.10:8000). Leer = auto.")
def ui_cmd(project_root: str, port: int, watch: bool, no_browser: bool, external_url: str) -> None:
    start_server(
        project_root=project_root,
        port=port,
        watch=watch,
        open_browser=not no_browser,
        external_url=external_url,
    )


cli.add_command(ui_cmd, name="ui")


# ─────────────────────────────────────────────────────────────────────────────
# sdd hub
# ─────────────────────────────────────────────────────────────────────────────
@cli.group(help="SDD Hub – Multi-Projekt-Dashboard auf Port 8000.")
def hub() -> None:
    pass


@hub.command("start", help="Startet den SDD Hub (Multi-Projekt-Dashboard).")
@click.option("--port", default=8000, show_default=True, help="Port für den Hub.")
@click.option("--no-browser", is_flag=True, help="Browser nicht automatisch öffnen.")
def hub_start(port: int, no_browser: bool) -> None:
    from .ui import start_hub
    start_hub(port=port, open_browser=not no_browser)


# ─────────────────────────────────────────────────────────────────────────────
# sdd test-run / sdd test-results
# ─────────────────────────────────────────────────────────────────────────────
def _print_run_report(report: "_test_runner.RunReport") -> None:
    table = Table(title=f"Test-Run · {report.spec_id} · {report.started_at[:19]}")
    table.add_column("TST-ID", style="cyan")
    table.add_column("Artefakt")
    table.add_column("Status")
    table.add_column("Dauer", justify="right")

    status_style = {
        "passed": "[green]✓ passed[/]",
        "failed": "[red]✗ failed[/]",
        "error": "[red]✗ error[/]",
        "missing": "[yellow]– missing[/]",
        "skipped": "[dim]◌ skipped[/]",
    }
    for t in report.tests:
        table.add_row(
            t.test_id,
            t.artifact or "—",
            status_style.get(t.status, t.status),
            f"{t.duration_s:.2f}s" if t.duration_s else "—",
        )
    console.print(table)

    if report.contract_coverage:
        console.print("\n[bold]Contract-Coverage:[/]")
        for con_id, covered in report.contract_coverage.items():
            mark = "[green]✓[/]" if covered else "[red]✗[/]"
            console.print(f"  {mark} {con_id}")

    failures = [t for t in report.tests if t.status in ("failed", "error") and t.message]
    if failures:
        console.print("\n[bold red]Fehlermeldungen:[/]")
        for t in failures:
            console.print(f"\n[cyan]{t.test_id}[/]")
            console.print(t.message)

    color = "green" if report.exit_code == 0 else "red"
    console.print(
        f"\n[{color}]Gesamt: {report.passed} passed · {report.failed} failed · "
        f"{report.skipped} skipped · {report.duration_s:.2f}s[/]"
    )


@cli.command("test-run", help="Führt alle Tests einer Spec aus (via pytest).")
@click.argument("spec_id", required=False)
@click.option("--all", "run_all", is_flag=True, help="Tests aller Specs ausführen.")
@click.option("--json", "output_json", is_flag=True, help="Ausgabe als JSON.")
def test_run_cmd(spec_id: str | None, run_all: bool, output_json: bool) -> None:
    cfg = _ensure_project()

    if not spec_id and not run_all:
        console.print("[red]✗[/] Entweder SPEC-ID angeben oder --all verwenden.")
        sys.exit(2)

    try:
        if run_all:
            reports = _test_runner.run_all(cfg)
        else:
            reports = [_test_runner.run(cfg, spec_id)]
    except ValueError as e:
        console.print(f"[red]✗[/] {e}")
        sys.exit(2)
    except RuntimeError as e:
        console.print(f"[red]✗[/] {e}")
        sys.exit(2)

    if output_json:
        import json as _json
        data = [r.to_json() for r in reports]
        console.print(_json.dumps(data if run_all else data[0], indent=2, ensure_ascii=False))
    else:
        for r in reports:
            _print_run_report(r)

    overall_exit = max(r.exit_code for r in reports)
    sys.exit(overall_exit)


@cli.command("test-results", help="Zeigt den letzten gespeicherten Test-Run einer Spec.")
@click.argument("spec_id")
@click.option("--json", "output_json", is_flag=True, help="Ausgabe als JSON.")
def test_results_cmd(spec_id: str, output_json: bool) -> None:
    cfg = _ensure_project()
    report = _test_runner.latest_report(cfg, spec_id)

    if report is None:
        console.print(
            f"[yellow]⚠[/] Noch kein Test-Run für [bold]{spec_id}[/] gefunden. "
            f"Starte mit: [cyan]sdd test-run {spec_id}[/]"
        )
        sys.exit(2)

    if output_json:
        import json as _json
        console.print(_json.dumps(report.to_json(), indent=2, ensure_ascii=False))
    else:
        _print_run_report(report)

    sys.exit(report.exit_code)


# ─────────────────────────────────────────────────────────────────────────────
# sdd spec review / approve
# ─────────────────────────────────────────────────────────────────────────────
@cli.group("spec", help="Spec-Pipeline-Kommandos (Gate, Review, Approve).")
def spec_group() -> None:
    pass


@spec_group.command("review", help="Markiert eine Spec als reviewed (Phase: spec-review).")
@click.argument("spec_id")
def spec_review(spec_id: str) -> None:
    cfg = _ensure_project()
    from .gate import ExecutionGate
    g = ExecutionGate(cfg.root)
    allowed = g.can_start_phase(spec_id, "spec-review")
    if not allowed.allowed:
        console.print(f"[red]✗[/] {allowed.reason}")
        sys.exit(2)
    g.mark_phase_started(spec_id, "spec-review")

    # Sub-Phase 2b: SOLID-Analyse (SPEC-0015)
    if cfg.solid_gate_enabled():
        _run_solid_phase(cfg, spec_id, "spec")

    # Sub-Phase 2c: Pattern-Vorschläge (SPEC-0015)
    if cfg.pattern_suggestions_enabled():
        _run_pattern_phase(cfg, spec_id, "spec")

    g.mark_phase_complete(spec_id, "spec-review")
    console.print(f"\n[green]✓[/] Phase [bold]spec-review[/] abgeschlossen für [cyan]{spec_id}[/].")


@spec_group.command("approve", help="Genehmigt eine Spec (spec-approved + execute-unlocked).")
@click.argument("spec_id")
@click.option("--fr-coverage", default="", help="FR-Coverage-Angabe, z.B. '11/11'.")
@click.option("--scenarios-covered", default="", help="Szenarien-Coverage, z.B. '25/25'.")
def spec_approve(spec_id: str, fr_coverage: str, scenarios_covered: str) -> None:
    cfg = _ensure_project()
    from .gate import ExecutionGate
    from .frontmatter import patch_status
    g = ExecutionGate(cfg.root)
    allowed = g.can_start_phase(spec_id, "spec-approved")
    if not allowed.allowed:
        console.print(f"[red]✗[/] {allowed.reason}")
        sys.exit(2)
    g.mark_phase_complete(spec_id, "spec-approved", consistency_check={
        "fr_coverage": fr_coverage,
        "scenarios_covered": scenarios_covered,
        "contracts_consistent": True,
    })
    g.mark_phase_complete(spec_id, "execute-unlocked")
    for md in cfg.specs_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == spec_id:
            try:
                patch_status(md, "approved")
            except Exception:
                pass
            break
    console.print(f"[green]✓[/] [cyan]{spec_id}[/] genehmigt – Execute freigegeben.")


# ─────────────────────────────────────────────────────────────────────────────
# sdd contract propose / review
# ─────────────────────────────────────────────────────────────────────────────
@cli.group("contract", help="Contract-Pipeline-Kommandos (Propose, Review).")
def contract_group() -> None:
    pass


@contract_group.command("propose", help="Schlägt Contracts vor und startet Phase contracts-proposed.")
@click.argument("spec_id")
@click.argument("contract_ids", nargs=-1, required=True)
def contract_propose(spec_id: str, contract_ids: tuple) -> None:
    cfg = _ensure_project()
    from .gate import ExecutionGate
    g = ExecutionGate(cfg.root)
    allowed = g.can_start_phase(spec_id, "contracts-proposed")
    if not allowed.allowed:
        console.print(f"[red]✗[/] {allowed.reason}")
        sys.exit(2)
    g.mark_phase_started(spec_id, "contracts-proposed")
    g.mark_phase_complete(spec_id, "contracts-proposed", proposed=list(contract_ids))
    console.print(
        f"[green]✓[/] Contracts vorgeschlagen für [cyan]{spec_id}[/]: "
        + ", ".join(f"[bold]{c}[/]" for c in contract_ids)
    )


@contract_group.command("review", help="Führt Konfliktanalyse für vorgeschlagene Contracts durch.")
@click.argument("spec_id")
@click.argument("contract_ids", nargs=-1, required=True)
def contract_review(spec_id: str, contract_ids: tuple) -> None:
    cfg = _ensure_project()
    from .gate import ExecutionGate
    from .conflict_detector import ConflictDetector
    g = ExecutionGate(cfg.root)
    allowed = g.can_start_phase(spec_id, "contracts-review")
    if not allowed.allowed:
        console.print(f"[red]✗[/] {allowed.reason}")
        sys.exit(2)
    g.mark_phase_started(spec_id, "contracts-review")

    console.print(f"[cyan]▶[/] Analysiere Konflikte für {len(contract_ids)} Contract(s) …")
    d = ConflictDetector(cfg.root)
    report = d.analyze(spec_id, list(contract_ids))

    summary = report.impact_summary
    total = summary["total_conflicts"]
    high = summary["high"]

    if total == 0:
        console.print("[green]✓[/] Keine Konflikte gefunden.")
    else:
        color = "red" if high > 0 else "yellow"
        console.print(
            f"[{color}]{total} Konflikte gefunden "
            f"(high={high}, medium={summary['medium']}, low={summary['low']})[/]"
        )
        for cf in report.conflicts:
            sev_color = {"high": "red", "medium": "yellow", "low": "white"}.get(cf["severity"], "white")
            console.print(
                f"  [{sev_color}]{cf['id']}[/] [{cf['severity'].upper()}] "
                f"{cf['type']}: {cf['new_contract']} ↔ {cf['conflicting_contract']}"
            )
            if cf.get("detail"):
                console.print(f"    {cf['detail']}")

    g.mark_phase_complete(
        spec_id, "contracts-review",
        conflicts_found=total,
        conflicts_high=high,
    )

    # Sub-Phase 5b+5c: SOLID-Analyse und Pattern-Vorschläge für jeden Contract (SPEC-0015)
    for con_id in contract_ids:
        if cfg.solid_gate_enabled():
            _run_solid_phase(cfg, con_id, "contract")
        if cfg.pattern_suggestions_enabled():
            _run_pattern_phase(cfg, con_id, "contract")

    if high > 0:
        console.print(
            f"\n[red]✗[/] {high} HIGH-Konflikte offen. "
            "Auflösen mit: [cyan]sdd conflict resolve[/] oder [cyan]sdd conflict acknowledge[/]"
        )
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# sdd test generate
# ─────────────────────────────────────────────────────────────────────────────
@cli.group("test", help="Test-Pipeline-Kommandos (Generate).")
def test_group() -> None:
    pass


@test_group.command("generate", help="Generiert Contract-Tests aus Contract-Definitionen.")
@click.argument("spec_id")
@click.argument("contract_ids", nargs=-1, required=True)
def test_generate(spec_id: str, contract_ids: tuple) -> None:
    cfg = _ensure_project()
    from .gate import ExecutionGate
    from .test_generator import TestGenerator
    g = ExecutionGate(cfg.root)
    allowed = g.can_start_phase(spec_id, "tests-generated")
    if not allowed.allowed:
        console.print(f"[red]✗[/] {allowed.reason}")
        sys.exit(2)
    g.mark_phase_started(spec_id, "tests-generated")

    gen = TestGenerator(cfg.root)
    result = gen.generate(spec_id, list(contract_ids))

    for f in result.generated_files:
        console.print(
            f"[green]✓[/] {f['contract_id']}: "
            f"[bold]{f['path']}[/] ({f['test_count']} Tests)"
        )

    if result.syntax_errors:
        for err in result.syntax_errors:
            console.print(f"[red]✗[/] {err}")

    if result.success:
        g.mark_phase_complete(
            spec_id, "tests-generated",
            files_generated=[f["path"] for f in result.generated_files],
        )
        console.print(f"[green]✓[/] Phase [bold]tests-generated[/] abgeschlossen.")
    else:
        g.mark_phase_complete(spec_id, "tests-generated", result="failed",
                              syntax_errors=result.syntax_errors)
        console.print("[red]✗[/] Syntaxfehler – Phase tests-generated fehlgeschlagen.")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# sdd conflict list / resolve / acknowledge
# ─────────────────────────────────────────────────────────────────────────────
@cli.group("conflict", help="Konflikte verwalten (list, resolve, acknowledge).")
def conflict_group() -> None:
    pass


@conflict_group.command("list", help="Listet Konflikte für eine Spec.")
@click.argument("spec_id")
@click.option("--status", default=None,
              type=click.Choice(["open", "resolved", "acknowledged"]),
              help="Filter nach Status.")
@click.option("--json", "output_json", is_flag=True)
def conflict_list(spec_id: str, status: str | None, output_json: bool) -> None:
    cfg = _ensure_project()
    from .conflict_detector import ConflictDetector
    import json as _json
    d = ConflictDetector(cfg.root)
    conflicts = d.list_conflicts(spec_id, status_filter=status)
    if output_json:
        console.print(_json.dumps(conflicts, indent=2, ensure_ascii=False))
        return
    if not conflicts:
        console.print("[green]✓[/] Keine Konflikte gefunden.")
        return
    table = Table(title=f"Konflikte – {spec_id}")
    table.add_column("CF-ID", style="cyan")
    table.add_column("Typ")
    table.add_column("Schwere")
    table.add_column("Neu ↔ Bestehend")
    table.add_column("Status")
    sev_style = {"high": "red", "medium": "yellow", "low": "white"}
    status_style = {"open": "yellow", "resolved": "green", "acknowledged": "dim"}
    for cf in conflicts:
        sev = cf.get("severity", "?")
        st = cf.get("status", "?")
        table.add_row(
            cf.get("id", "?"),
            cf.get("type", "?"),
            f"[{sev_style.get(sev, 'white')}]{sev}[/]",
            f"{cf.get('new_contract', '?')} ↔ {cf.get('conflicting_contract', '?')}",
            f"[{status_style.get(st, 'white')}]{st}[/]",
        )
    console.print(table)


@conflict_group.command("resolve", help="Markiert einen Konflikt als aufgelöst.")
@click.argument("spec_id")
@click.argument("cf_id")
@click.option("--action", required=True, help="Beschreibung der Auflösung.")
def conflict_resolve(spec_id: str, cf_id: str, action: str) -> None:
    cfg = _ensure_project()
    from .conflict_detector import ConflictDetector
    d = ConflictDetector(cfg.root)
    try:
        d.resolve(spec_id, cf_id, action)
    except FileNotFoundError as e:
        console.print(f"[red]✗[/] {e}")
        sys.exit(1)
    console.print(f"[green]✓[/] [bold]{cf_id}[/] aufgelöst: {action}")


@conflict_group.command("acknowledge", help="Bestätigt einen Konflikt mit Begründung.")
@click.argument("spec_id")
@click.argument("cf_id")
@click.option("--reason", required=True, help="Pflichtbegründung.")
def conflict_acknowledge(spec_id: str, cf_id: str, reason: str) -> None:
    cfg = _ensure_project()
    from .conflict_detector import ConflictDetector
    d = ConflictDetector(cfg.root)
    try:
        d.acknowledge(spec_id, cf_id, reason)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]✗[/] {e}")
        sys.exit(1)
    console.print(f"[green]✓[/] [bold]{cf_id}[/] bestätigt.")


# ─────────────────────────────────────────────────────────────────────────────
# sdd obsidian export / import / watch
# ─────────────────────────────────────────────────────────────────────────────
@cli.group("obsidian", help="Obsidian Vault Synchronisation (Export, Import, Watch).")
def obsidian_group() -> None:
    pass


@obsidian_group.command("export", help="Exportiert alle SDD-Artefakte in den Obsidian-Vault.")
@click.option("--vault", "vault_path", default=None,
              help="Vault-Pfad (überschreibt obsidian.vault_path in config.yaml).")
@click.option("--dry-run", is_flag=True,
              help="Zeigt geplante Aktionen, schreibt keine Dateien.")
def obsidian_export(vault_path: str | None, dry_run: bool) -> None:
    cfg = _ensure_project()
    from .obsidian import export as _export, obsidian_config

    try:
        result = _export(cfg, vault_override=vault_path, dry_run=dry_run)
    except ValueError as e:
        console.print(f"[red]✗[/] {e}")
        sys.exit(2)
    except FileNotFoundError as e:
        console.print(f"[red]✗[/] {e}")
        sys.exit(2)

    mode = "[yellow]dry-run[/]" if dry_run else "[green]live[/]"
    console.print(f"[cyan]▶[/] Obsidian Export ({mode})")
    for p in result.written:
        console.print(f"  [green]✓[/] {p}")
    for p in result.skipped:
        console.print(f"  [dim]– {p} (übersprungen – Vault aktueller)[/]")
    console.print(
        f"\n[green]✓[/] {len(result.written)} Datei(en) {'würden geschrieben' if dry_run else 'geschrieben'}, "
        f"{len(result.skipped)} übersprungen."
    )


@obsidian_group.command("import", help="Importiert geänderte Vault-Dateien ins Projekt zurück.")
@click.option("--vault", "vault_path", default=None,
              help="Vault-Pfad (überschreibt obsidian.vault_path in config.yaml).")
def obsidian_import(vault_path: str | None) -> None:
    cfg = _ensure_project()
    from .obsidian import import_vault

    try:
        result = import_vault(cfg, vault_override=vault_path)
    except ValueError as e:
        console.print(f"[red]✗[/] {e}")
        sys.exit(2)
    except FileNotFoundError as e:
        console.print(f"[red]✗[/] {e}")
        sys.exit(2)

    for p in result.imported:
        console.print(f"  [green]✓[/] importiert: {p}")
    for w in result.warnings:
        console.print(f"  [yellow]⚠[/] {w}")
    for c in result.conflicts:
        console.print(f"  [red]✗[/] Conflict: {c} – nicht überschrieben")

    if result.conflicts:
        console.print(
            f"\n[red]✗[/] {len(result.conflicts)} Conflict(s) erkannt. "
            "Siehe [bold].sdd/obsidian-conflicts.yaml[/]."
        )
        sys.exit(1)

    console.print(
        f"\n[green]✓[/] {len(result.imported)} Datei(en) importiert, "
        f"{len(result.skipped)} übersprungen."
    )


@obsidian_group.command("watch", help="Beobachtet den Vault auf Änderungen und importiert automatisch.")
@click.option("--vault", "vault_path", default=None,
              help="Vault-Pfad (überschreibt obsidian.vault_path in config.yaml).")
@click.option("--interval", default=None, type=int,
              help="Polling-Intervall in Sekunden (überschreibt watch_interval_secs).")
def obsidian_watch(vault_path: str | None, interval: int | None) -> None:
    cfg = _ensure_project()
    from .obsidian import watch as _watch, obsidian_config

    try:
        ocfg = obsidian_config(cfg, vault_path)
        effective = interval or ocfg.watch_interval_secs
        console.print(
            f"[cyan]▶[/] Obsidian Watch läuft (Intervall: {effective}s). "
            "Beenden mit [bold]Ctrl+C[/]."
        )
        _watch(cfg, vault_override=vault_path, interval=interval)
    except ValueError as e:
        console.print(f"[red]✗[/] {e}")
        sys.exit(2)
    except FileNotFoundError as e:
        console.print(f"[red]✗[/] {e}")
        sys.exit(2)

    console.print("\n[dim]Watch beendet.[/]")


# ─────────────────────────────────────────────────────────────────────────────
# sdd status-check  (SPEC-0010 FR-01 / FR-02)
# ─────────────────────────────────────────────────────────────────────────────
@cli.command("status-check",
             help="Prüft Content-Hashes und meldet veraltete Status. "
                  "Mit --fix werden Status-Felder automatisch aktualisiert.")
@click.option("--fix", is_flag=True,
              help="Status-Felder im Frontmatter automatisch patchen.")
def status_check_cmd(fix: bool) -> None:
    cfg = _ensure_project()
    from .lifecycle import (
        check_transitions, apply_transitions, rebuild_hashes,
        load_hashes, save_hashes,
    )

    hashes = load_hashes(cfg)
    if not hashes:
        console.print("[dim]Erstlauf: baue Content-Hash-Index neu auf …[/]")
        hashes = rebuild_hashes(cfg)
        save_hashes(cfg, hashes)
        console.print(
            f"[green]✓[/] {len(hashes)} Artefakt-Hash(es) initialisiert "
            f"in [bold].sdd/content-hashes.json[/]."
        )
        _print_in_progress_section(cfg)
        sys.exit(0)

    changes = check_transitions(cfg)
    exit_code = 0

    if not changes:
        console.print("[green]✓ Alle Status sind aktuell. Kein Übergang nötig.[/]")
    else:
        table = Table(title="Veraltete Status")
        table.add_column("Artefakt", style="cyan")
        table.add_column("Datei")
        table.add_column("Alt")
        table.add_column("Neu")
        for ch in changes:
            table.add_row(
                ch.artifact_id,
                str(ch.path.relative_to(cfg.root)),
                f"[yellow]{ch.old_status}[/]",
                f"[green]{ch.new_status}[/]",
            )
        console.print(table)

        if fix:
            apply_transitions(cfg, changes)
            console.print(
                f"[green]✓[/] {len(changes)} Status-Übergang(¨e) angewendet "
                f"und in [bold].sdd/audit.log[/] festgehalten."
            )
        else:
            console.print(
                "\n  [dim]Starte [cyan]sdd status-check --fix[/] um die Übergänge anzuwenden.[/]"
            )
            exit_code = 1

    _print_in_progress_section(cfg)
    sys.exit(exit_code)


def _print_in_progress_section(cfg: "object") -> None:
    """Zeigt in-progress Specs mit started_at und 24h-Warnung (SPEC-0019 FR-08/FR-09)."""
    from datetime import datetime, timezone, timedelta
    from .lifecycle import get_in_progress_specs

    in_progress = get_in_progress_specs(cfg)
    if not in_progress:
        return

    console.print()
    console.rule("[cyan]IN PROGRESS[/]")
    now = datetime.now(timezone.utc)

    for doc in in_progress:
        fm = doc.frontmatter
        spec_id = fm.get("id", "?")
        title = fm.get("title", "")[:50]
        started_at_str = fm.get("started_at", "")
        tst_count = len(fm.get("tests") or [])

        age_str = ""
        warn_24h = False
        if started_at_str:
            try:
                started = datetime.fromisoformat(started_at_str.replace("Z", "+00:00"))
                age = now - started
                hours = int(age.total_seconds() // 3600)
                age_str = f"{hours}h"
                warn_24h = age > timedelta(hours=24)
            except ValueError:
                pass

        console.print(
            f"  [cyan]{spec_id}[/]  {title}  "
            f"seit [dim]{age_str or '?'}[/]  "
            f"Tests: [dim]{tst_count} verknüpft[/]"
        )

        if warn_24h:
            tests_root = cfg.root / "tests"
            slug = spec_id.lower().replace("-", "_")
            has_file = any(tests_root.rglob(f"*{slug}*.py")) if tests_root.exists() else False
            if not has_file:
                console.print(
                    f"  [yellow]![/] {spec_id} ist seit >24h in-progress "
                    "aber keine Testdatei gefunden – führe [cyan]sdd start[/] erneut aus."
                )


# ─────────────────────────────────────────────────────────────────────────────
# sdd start  (SPEC-0019)
# ─────────────────────────────────────────────────────────────────────────────

@cli.command("start", help="Startet die TDD-Implementierungsphase: approved → in-progress + Test-Stubs (SPEC-0019).")
@click.argument("spec_id")
@click.option("--auto", is_flag=True,
              help="Nach start sofort sdd orchestrate ausführen (autonomer Dark-Factory-Pfad).")
@click.option("--base-url", default=None, envvar="SDD_EVAL_BASE_URL",
              help="Basis-URL für den Evaluator-Schritt (nur mit --auto).")
@click.option("--build-cmd", default=None,
              help="Build-Kommando (nur mit --auto). Überschreibt orchestrator.build_command.")
@click.option("--no-pr", is_flag=True, help="PR-Erstellung überspringen (nur mit --auto).")
@click.option("--no-container", is_flag=True,
              help="Container nicht starten (z.B. in CI ohne Docker-Daemon).")
def start_cmd(spec_id: str, auto: bool, base_url: str | None,
              build_cmd: str | None, no_pr: bool, no_container: bool) -> None:
    cfg = _ensure_project()
    from .lifecycle import start_spec

    try:
        result = start_spec(cfg, spec_id)
    except ValueError as exc:
        msg = str(exc)
        if msg.startswith("[INFO]"):
            console.print(f"[cyan]{msg.removeprefix('[INFO] ')}[/]")
        else:
            console.print(f"[red]✗[/] {exc}")
        sys.exit(1)

    console.print(f"[green]✓[/] [cyan]{result.spec_id}[/] → [bold]in-progress[/]")
    console.print()

    if not result.tst_ids:
        console.print(
            "[yellow]![/] Keine Tests im Frontmatter verknüpft – "
            "erstelle erst Tests mit [cyan]sdd new test[/], dann erneut [cyan]sdd start[/]."
        )
        sys.exit(0)

    # ── Container starten ────────────────────────────────────────────────────
    if not no_container:
        from .dev_container import DevContainerManager
        mgr = DevContainerManager(cfg)
        if not mgr.runtime_available():
            console.print(
                f"[yellow]![/] Container-Runtime nicht verfügbar – "
                f"Container wird nicht gestartet.\n"
                f"  Starte die Runtime und führe [cyan]sdd dev start {spec_id}[/] manuell aus.\n"
                f"  Oder nutze [cyan]sdd start {spec_id} --no-container[/]."
            )
        else:
            console.print()
            if not mgr.image_exists():
                console.print(f"[dim]▶ Baue Container-Image (einmalig) …[/]")
                mgr.build()
            console.print(f"[dim]▶ Starte Container für {spec_id} …[/]")
            mgr.start(spec_id)
            console.print(
                f"[green]✓[/] Container bereit – Tests ausführen mit:\n"
                f"  [cyan]sdd dev exec {spec_id} pytest tests/ -x --tb=short[/]"
            )

    if result.stubs_created:
        console.print("[bold]Test-Stubs angelegt:[/]")
        for p in result.stubs_created:
            console.print(f"  [green]+[/] {p.relative_to(cfg.root)}")
    if result.stubs_skipped:
        console.print("[bold]Übersprungen (bereits vorhanden):[/]")
        for p in result.stubs_skipped:
            console.print(f"  [yellow]~[/] {p.relative_to(cfg.root)}")

    if auto:
        console.print()
        console.print(f"[dim]▶ --auto: starte orchestrate für [cyan]{result.spec_id}[/] …[/]")
        from .orchestrator import run_pipeline, persist_pipeline_report
        try:
            report = run_pipeline(
                cfg, result.spec_id,
                base_url=base_url,
                build_cmd=build_cmd,
                no_pr=no_pr,
                on_step=lambda msg: console.print(f"  {msg}"),
            )
        except (ValueError, RuntimeError) as exc:
            console.print(f"[red]✗[/] Orchestrator fehlgeschlagen: {exc}")
            sys.exit(1)
        persist_pipeline_report(cfg, report)
        color = {"merged": "bold green", "labeled": "green",
                 "failed": "red", "dry_run": "yellow"}.get(report.final_status, "white")
        console.print(f"\n[{color}]Orchestrator: {report.final_status.upper()}[/]")
        sys.exit(0 if report.final_status in ("merged", "labeled") else 1)

    console.print()
    console.print("[bold]Jetzt Code implementieren bis alle Tests grün sind.[/]")
    console.print(f"  Interaktiv:  [cyan]/sdd-implement {result.spec_id}[/] in Claude Code")
    console.print(f"  Autonom:     [cyan]sdd orchestrate --spec {result.spec_id}[/]")


# ─────────────────────────────────────────────────────────────────────────────
# sdd install-hooks  (SPEC-0010 FR-02)
# ─────────────────────────────────────────────────────────────────────────────
@cli.command("install-hooks",
             help="Installiert einen Git-Pre-Commit-Hook der sdd status-check --fix ausführt.")
def install_hooks_cmd() -> None:
    cfg = _ensure_project()
    git_dir = cfg.root / ".git"
    if not git_dir.exists():
        console.print("[red]✗[/] Kein .git-Verzeichnis gefunden. Kein Git-Repository?")
        sys.exit(1)

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    hook_path = hooks_dir / "pre-commit"

    hook_script = (
        "#!/bin/sh\n"
        "# Installiert von sdd install-hooks (SPEC-0010)\n"
        "sdd status-check --fix\n"
    )
    hook_path.write_text(hook_script, encoding="utf-8")
    hook_path.chmod(0o755)

    console.print(f"[green]✓[/] Pre-Commit-Hook installiert: [bold]{hook_path}[/]")
    console.print(
        "  Bei jedem [cyan]git commit[/] wird [cyan]sdd status-check --fix[/] ausgeführt."
    )


# ─────────────────────────────────────────────────────────────────────────────
# sdd review-contract  (SPEC-0010 FR-05 / FR-06 / FR-07)
# ─────────────────────────────────────────────────────────────────────────────
@cli.command("review-contract",
             help="LLM-Review eines Contracts: prüft Vollständigkeit und erzeugt Testvorschlag.")
@click.argument("con_id")
def review_contract_cmd(con_id: str) -> None:
    cfg = _ensure_project()
    from .lifecycle import review_contract

    console.print(f"[cyan]▶[/] LLM-Review für [bold]{con_id}[/] …")
    try:
        result = review_contract(cfg, con_id)
    except ValueError as e:
        console.print(f"[red]✗[/] {e}")
        sys.exit(1)
    except RuntimeError as e:
        console.print(f"[red]✗[/] LLM nicht erreichbar: {e}")
        sys.exit(1)

    verdict_color = "green" if result.llm_verdict == "approved" else "yellow"
    console.print(
        f"  Bewertung: [{verdict_color}]{result.llm_verdict}[/]"
    )
    console.print(
        f"  [green]✓[/] TST-Datei angelegt: [bold]{result.tst_path.relative_to(cfg.root)}[/] "
        f"([cyan]{result.tst_id}[/])"
    )
    if result.notes:
        console.print(f"  Hinweise: {result.notes[:200]}")
    if result.llm_verdict == "needs_revision":
        console.print(
            f"  [yellow]⚠[/] LLM Review Notes an [bold]{con_id}[/] angehängt."
        )


# ─────────────────────────────────────────────────────────────────────────────
# sdd review-pending  (SPEC-0010 FR-08 / FR-09)
# ─────────────────────────────────────────────────────────────────────────────
@cli.command("review-pending",
             help="Listet alle Contracts im Status review ohne Test. "
                  "Mit --auto: führt sdd review-contract für jeden aus.")
@click.option("--auto", is_flag=True,
              help="Führt LLM-Review für jeden Eintrag sequenziell aus.")
def review_pending_cmd(auto: bool) -> None:
    cfg = _ensure_project()
    from .lifecycle import pending_contracts, review_contract
    from datetime import date

    pending = pending_contracts(cfg)

    if not pending:
        console.print("[green]✓ Keine ausstehenden Contract-Reviews.[/]")
        sys.exit(0)

    table = Table(title="Pending Contract-Reviews")
    table.add_column("Contract-ID", style="cyan")
    table.add_column("Titel")
    table.add_column("Spec")
    table.add_column("Alter (Tage)", justify="right")

    today = date.today()
    for doc in pending:
        fm = doc.frontmatter
        created_raw = fm.get("created", "")
        try:
            created = date.fromisoformat(str(created_raw))
            age = (today - created).days
        except (ValueError, TypeError):
            age = "?"
        table.add_row(
            fm.get("id", "?"),
            fm.get("title", ""),
            fm.get("spec", ""),
            str(age),
        )
    console.print(table)

    if not auto:
        console.print(
            f"\n  [dim]{len(pending)} ausstehend. "
            "Starte [cyan]sdd review-pending --auto[/] für automatisches Review.[/]"
        )
        sys.exit(1)

    from rich.progress import Progress
    with Progress(console=console) as progress:
        task = progress.add_task("LLM-Reviews …", total=len(pending))
        for doc in pending:
            cid = doc.frontmatter.get("id", "?")
            progress.update(task, description=f"Reviewe {cid} …")
            try:
                result = review_contract(cfg, cid)
                verdict_color = "green" if result.llm_verdict == "approved" else "yellow"
                console.print(
                    f"  [green]✓[/] {cid} → [{verdict_color}]{result.llm_verdict}[/] "
                    f"· {result.tst_id}"
                )
            except Exception as exc:
                console.print(f"  [red]✗[/] {cid}: {exc}")
            progress.advance(task)


# ─────────────────────────────────────────────────────────────────────────────
# sdd estimate  (SPEC-0011)
# ─────────────────────────────────────────────────────────────────────────────
@cli.command("estimate",
             help="Schätzt Token-Kosten für eine Spec (oder alle) via Nearest-Neighbor-Heuristik.")
@click.argument("spec_id", required=False)
@click.option("--all", "estimate_all", is_flag=True,
              help="Alle Specs mit passendem --status schätzen.")
@click.option("--status", "filter_status", default=None,
              type=click.Choice(["draft", "review", "approved", "implemented", "deprecated"]),
              help="Nur Specs mit diesem Status schätzen (nur mit --all).")
@click.option("--model", "model_override", default=None,
              help="Überschreibt das Preismodell, z.B. claude-sonnet-4-6.")
@click.option("--json", "output_json", is_flag=True,
              help="Ausgabe als maschinenlesbares JSON.")
def estimate_cmd(
    spec_id: str | None,
    estimate_all: bool,
    filter_status: str | None,
    model_override: str | None,
    output_json: bool,
) -> None:
    from .estimation import estimate, EstimateResult
    import json as _json

    cfg = _ensure_project()

    if not spec_id and not estimate_all:
        console.print("[red]✗[/] Entweder SPEC-ID angeben oder --all verwenden.")
        sys.exit(2)

    if estimate_all:
        specs = sorted(
            [parse_safe(p) for p in cfg.specs_dir.rglob("*.md")
             if parse_safe(p) and parse_safe(p).frontmatter.get("id")],
            key=lambda d: d.frontmatter["id"],
        )
        if filter_status:
            specs = [s for s in specs if s.frontmatter.get("status") == filter_status]

        results: list[EstimateResult] = []
        for s in specs:
            sid = s.frontmatter["id"]
            try:
                results.append(estimate(cfg, sid, model_override))
            except Exception as exc:
                console.print(f"[yellow]⚠[/] {sid}: {exc}")

        if output_json:
            console.print(_json.dumps(
                {"estimates": [r.to_dict() for r in results]},
                indent=2, ensure_ascii=False,
            ))
            sys.exit(0)

        _print_estimate_table(results, cfg)
        sys.exit(0)

    # Einzelne Spec
    try:
        result = estimate(cfg, spec_id, model_override)
    except ValueError as e:
        console.print(f"[red]✗[/] {e}")
        sys.exit(1)

    if output_json:
        console.print(_json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        sys.exit(0)

    _print_estimate_single(result)


def _print_estimate_single(result: "object") -> None:
    from rich.panel import Panel

    conf_color = {"LOW": "red", "MEDIUM": "yellow", "HIGH": "green"}.get(
        result.confidence, "white"
    )
    fallback_note = " [dim](Fallback auf 'default'-Preis)[/]" if result.model_fallback else ""

    console.print(f"\n[bold]Token-Kostenschätzung für [cyan]{result.spec_id}[/][/]\n")
    console.print(f"  Modell:        [bold]{result.model}[/]{fallback_note}")
    console.print(f"  Input-Tokens:  {result.input_tokens:,}")
    console.print(f"  Output-Tokens: {result.output_tokens:,}")
    if result.cache_read_tokens:
        console.print(f"  Cache-Read:    {result.cache_read_tokens:,}")
    console.print(f"  Geschätzte Kosten: [bold]{result.estimated_usd:.4f} USD[/]")
    console.print(
        f"  Konfidenz:     [{conf_color}]{result.confidence}[/] "
        f"({result.n_data_points} hist. Datenpunkt(e))"
    )

    if result.confidence == "LOW":
        console.print(
            "[yellow]⚠ Wenig Daten – Schätzung unzuverlässig "
            "(< 3 historische Datenpunkte).[/]"
        )

    if result.neighbors:
        console.print("\n  [bold]Nächste Vergleichs-Specs:[/]")
        for n in result.neighbors:
            console.print(
                f"    [cyan]{n.spec_id}[/]  "
                f"Input: {n.input_tokens:,}  Output: {n.output_tokens:,}  "
                f"Ähnlichkeit: {n.similarity:.0%}"
            )

    if result.budget_exceeded:
        console.print(Panel(
            f"[bold red]Schätzung überschreitet Budget "
            f"({result.estimated_usd:.4f} USD > {result.budget_limit_usd:.2f} USD)[/]",
            title="WARNING",
            border_style="red",
        ))


def _print_estimate_table(results: list, cfg: "object") -> None:
    from rich.panel import Panel

    table = Table(title="Token-Kostenschätzung – Alle Specs")
    table.add_column("Spec-ID", style="cyan")
    table.add_column("Input-T", justify="right")
    table.add_column("Output-T", justify="right")
    table.add_column("Kosten (USD)", justify="right")
    table.add_column("Konfidenz")

    conf_color = {"LOW": "red", "MEDIUM": "yellow", "HIGH": "green"}
    total_usd = 0.0
    budget_exceeded_total = False

    for r in results:
        total_usd += r.estimated_usd
        cc = conf_color.get(r.confidence, "white")
        table.add_row(
            r.spec_id,
            f"{r.input_tokens:,}",
            f"{r.output_tokens:,}",
            f"{r.estimated_usd:.4f}",
            f"[{cc}]{r.confidence}[/]",
        )

    table.add_section()
    table.add_row(
        "[bold]GESAMT[/]", "", "",
        f"[bold]{total_usd:.4f}[/]", "[dim](Schätzung)[/]",
    )
    console.print(table)

    if results:
        budget_limit = results[0].budget_limit_usd
        if budget_limit and total_usd > budget_limit:
            console.print(Panel(
                f"[bold red]Gesamtschätzung überschreitet Budget "
                f"({total_usd:.4f} USD > {budget_limit:.2f} USD)[/]",
                title="WARNING",
                border_style="red",
            ))


# ─────────────────────────────────────────────────────────────────────────────
# sdd token-history  (SPEC-0011 FR-07 / FR-08)
# ─────────────────────────────────────────────────────────────────────────────
@cli.command("token-history",
             help="Zeigt gespeicherte Token-Verbräuche. Optional gefiltert nach SPEC-ID.")
@click.argument("spec_id", required=False)
@click.option("--export", "export_csv", default=None,
              help="Exportiert alle Datenpunkte als CSV (Pfad zur Ausgabedatei).")
def token_history_cmd(spec_id: str | None, export_csv: str | None) -> None:
    from .estimation import token_history, export_token_history_csv

    cfg = _ensure_project()

    if export_csv:
        path = Path(export_csv)
        n = export_token_history_csv(cfg, path)
        console.print(f"[green]✓[/] {n} Zeile(n) exportiert nach [bold]{path}[/]")
        sys.exit(0)

    rows = token_history(cfg, spec_id)

    if not rows:
        msg = f"[yellow]⚠[/] Keine Token-Daten für [bold]{spec_id}[/] gefunden." \
            if spec_id else "[yellow]⚠[/] Keine Token-Daten vorhanden."
        console.print(msg)
        console.print("  Starte LLM-gestützte Befehle (z.B. [cyan]sdd review-contract[/]), "
                      "um Daten zu sammeln.")
        sys.exit(0)

    title = f"Token-History – {spec_id}" if spec_id else "Token-History – Alle Specs"
    table = Table(title=title)
    table.add_column("ID", justify="right", style="dim")
    table.add_column("Zeitstempel")
    table.add_column("Spec")
    table.add_column("Komponente")
    table.add_column("Modell")
    table.add_column("Input-T", justify="right")
    table.add_column("Output-T", justify="right")
    table.add_column("Cache-R", justify="right")
    table.add_column("Dauer (ms)", justify="right")

    for r in rows:
        table.add_row(
            str(r.id),
            r.timestamp[:19],
            r.spec_id or "—",
            r.component,
            r.model or "—",
            f"{r.input_tokens:,}",
            f"{r.output_tokens:,}",
            f"{r.cache_read_tokens:,}" if r.cache_read_tokens else "—",
            f"{r.duration_ms:,}" if r.duration_ms else "—",
        )
    console.print(table)


# ─────────────────────────────────────────────────────────────────────────────
# sdd calibrate  (SPEC-0011 FR-09)
# ─────────────────────────────────────────────────────────────────────────────
@cli.command("calibrate",
             help="Markiert Token-Verbrauch einer Spec als kalibrierten Abschluss-Datenpunkt.")
@click.argument("spec_id")
def calibrate_cmd(spec_id: str) -> None:
    from .estimation import calibrate

    cfg = _ensure_project()
    try:
        summary = calibrate(cfg, spec_id)
    except FileNotFoundError as e:
        console.print(f"[red]✗[/] {e}")
        sys.exit(1)

    console.print(f"[green]✓[/] [cyan]{spec_id}[/] kalibriert:")
    console.print(f"  Input-Tokens:  {summary['input_tokens']:,}")
    console.print(f"  Output-Tokens: {summary['output_tokens']:,}")
    console.print(f"  Einträge:      {summary['n_entries']}")


# ─────────────────────────────────────────────────────────────────────────────
# sdd solid-check  (SPEC-0015 FR-03)
# ─────────────────────────────────────────────────────────────────────────────
@cli.command("solid-check",
             help="SOLID-Analyse für eine Spec oder einen Contract (SPEC-0015).")
@click.argument("artifact_id")
@click.option("--json", "output_json", is_flag=True, help="Maschinenlesbare JSON-Ausgabe.")
@click.option(
    "--principle",
    type=click.Choice(["S", "O", "L", "I", "D"]),
    default=None,
    help="Nur ein SOLID-Prinzip prüfen.",
)
def solid_check(artifact_id: str, output_json: bool, principle: str | None) -> None:
    import json as _json
    from .solid import create_analyzer, find_artifact, PRINCIPLE_LABELS

    cfg = _ensure_project()
    artifact = find_artifact(cfg, artifact_id)
    if artifact is None:
        msg = f"Artefakt nicht gefunden: {artifact_id}"
        if output_json:
            print(_json.dumps({"error": msg}, ensure_ascii=False))
        else:
            console.print(f"[red]✗[/] {msg}")
        sys.exit(2)

    artifact_text, artifact_type = artifact
    analyzer = create_analyzer(cfg, principle_filter=principle)
    report = analyzer.analyze(artifact_text, artifact_id, artifact_type)

    if output_json:
        print(_json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        _print_solid_report(report, cfg.solid_gate_mode())

    if cfg.solid_gate_mode() == "block" and report.has_violations():
        if not output_json:
            console.print(
                "\n[red]✗ SOLID-Violation blockiert Phasenübergang[/] "
                "(solid_gate.mode: block)"
            )
        sys.exit(1)


def _print_solid_report(report: Any, mode: str) -> None:
    from .solid import PRINCIPLE_LABELS

    score_color = {"compliant": "green", "warn": "yellow", "violation": "red"}.get(
        report.overall_solid_score, "white"
    )
    console.print(
        f"\n[bold]{report.artifact_id}[/] · SOLID-Analyse "
        f"([{score_color}]{report.overall_solid_score}[/])"
    )
    console.print("─" * 70)

    by_principle: dict[str, list] = {p: [] for p in "SOLID"}
    for f in report.findings:
        if f.principle in by_principle:
            by_principle[f.principle].append(f)

    for p, label in PRINCIPLE_LABELS.items():
        findings = by_principle.get(p, [])
        violations = [f for f in findings if f.severity == "violation"]
        warns = [f for f in findings if f.severity == "warn"]
        if violations:
            console.print(f"  [red]✗[/] {p} – {label} [VIOLATION]")
            for f in violations:
                console.print(f"    → {f.description}")
                console.print(f"      Stelle: {f.location}")
                console.print(f"      Vorschlag: {f.suggestion}")
        elif warns:
            prefix = "[WARN]" if mode == "warn" else "[WARN]"
            console.print(f"  [yellow]![/] {p} – {label} {prefix}")
            for f in warns:
                console.print(f"    → {f.description}")
        else:
            console.print(f"  [green]✓[/] {p} – {label}")

    if report.summary:
        console.print(f"\n  [dim]{report.summary}[/]")


# ─────────────────────────────────────────────────────────────────────────────
# sdd pattern-suggest  (SPEC-0015 FR-04)
# ─────────────────────────────────────────────────────────────────────────────
@cli.command("pattern-suggest",
             help="Pattern-Vorschläge für eine Spec oder einen Contract (SPEC-0015).")
@click.argument("artifact_id")
def pattern_suggest_cmd(artifact_id: str) -> None:
    from .solid import find_artifact
    from .pattern import create_suggester

    cfg = _ensure_project()
    artifact = find_artifact(cfg, artifact_id)
    if artifact is None:
        console.print(f"[red]✗[/] Artefakt nicht gefunden: {artifact_id}")
        sys.exit(2)

    artifact_text, artifact_type = artifact
    suggester = create_suggester(cfg)
    if suggester is None:
        console.print("[yellow]![/] pattern_suggestions.enabled ist false – keine Vorschläge.")
        return

    console.print(f"[cyan]▶[/] Analysiere Pattern-Vorschläge für {artifact_id} …")
    result = suggester.suggest(artifact_text, artifact_id, artifact_type)

    _print_pattern_suggestions(result)
    console.print(
        f"\n  → Pattern annehmen: [cyan]sdd pattern accept {artifact_id} <PatternName> "
        "--reason \"<Begründung>\"[/]"
    )


def _print_pattern_suggestions(result: Any) -> None:
    if not result.pattern_suggestions:
        console.print("[dim]Keine Pattern-Vorschläge generiert.[/]")
        return

    console.print(f"\n[bold]Pattern-Vorschläge[/] für {result.artifact_id}:\n")
    priority_color = {"recommended": "green", "optional": "cyan", "consider": "dim"}
    for i, s in enumerate(result.pattern_suggestions, 1):
        color = priority_color.get(s.priority, "white")
        console.print(
            f"  [{i}] [bold]{s.pattern_name}[/] ({s.category}) "
            f"– [{color}]{s.priority.upper()}[/]"
        )
        console.print(f"      Warum: {s.rationale}")
        console.print(f"      Alternative abgelehnt: {s.alternative}")
        console.print(f"      Quelle: [link={s.refactoring_guru_url}]{s.refactoring_guru_url}[/link]")
        console.print()


# ─────────────────────────────────────────────────────────────────────────────
# sdd pattern accept / reject / list  (SPEC-0015 FR-05/06/07)
# ─────────────────────────────────────────────────────────────────────────────
@cli.group("pattern", help="Pattern-Register verwalten (accept, reject, list).")
def pattern_group() -> None:
    pass


@pattern_group.command("accept",
                       help="Nimmt ein Pattern an und dokumentiert die Entscheidung im Register.")
@click.argument("spec_id")
@click.argument("pattern_name")
@click.option("--reason", default=None, help="Begründung der Annahme (Pflicht).")
@click.option("--url", default=None, help="Refactoring Guru URL (optional).")
def pattern_accept(spec_id: str, pattern_name: str, reason: str | None, url: str | None) -> None:
    from .pattern import PatternRegistry

    if not reason:
        console.print("[red]✗[/] --reason ist erforderlich")
        sys.exit(1)

    cfg = _ensure_project()
    registry = PatternRegistry(cfg.root)
    registry.accept(spec_id, pattern_name, reason, url)
    console.print(
        f"[green]✓[/] Pattern [bold]{pattern_name}[/] für [cyan]{spec_id}[/] "
        "als [green]accepted[/] dokumentiert."
    )


@pattern_group.command("reject",
                       help="Lehnt ein Pattern ab und dokumentiert die Begründung im Register.")
@click.argument("spec_id")
@click.argument("pattern_name")
@click.option("--reason", default=None, help="Ablehnungsgrund (Pflicht).")
@click.option("--url", default=None, help="Refactoring Guru URL (optional).")
def pattern_reject(spec_id: str, pattern_name: str, reason: str | None, url: str | None) -> None:
    from .pattern import PatternRegistry

    if not reason:
        console.print("[red]✗[/] --reason ist erforderlich")
        sys.exit(1)

    cfg = _ensure_project()
    registry = PatternRegistry(cfg.root)
    registry.reject(spec_id, pattern_name, reason, url)
    console.print(
        f"[yellow]✗[/] Pattern [bold]{pattern_name}[/] für [cyan]{spec_id}[/] "
        "als [red]rejected[/] dokumentiert."
    )


@pattern_group.command("list",
                       help="Zeigt das Pattern-Register tabellarisch an.")
@click.argument("spec_id", required=False, default=None)
def pattern_list(spec_id: str | None) -> None:
    from .pattern import PatternRegistry

    cfg = _ensure_project()
    registry = PatternRegistry(cfg.root)
    entries = registry.list_patterns(spec_id)

    if not entries:
        console.print("[dim]Keine Pattern-Entscheidungen" +
                      (f" für {spec_id}" if spec_id else "") + ".[/]")
        return

    table = Table(title="Pattern-Register" + (f" · {spec_id}" if spec_id else ""))
    table.add_column("SPEC", style="cyan")
    table.add_column("Pattern", style="bold")
    table.add_column("Status")
    table.add_column("Begründung")
    table.add_column("Datum")

    status_style = {"accepted": "green", "rejected": "red", "under-review": "yellow"}
    for e in entries:
        status = e.get("status", "under-review")
        reason = e.get("acceptance_reason") or e.get("rejection_reason") or "—"
        if len(reason) > 60:
            reason = reason[:57] + "…"
        decided = (e.get("decided_at") or "")[:10] or "—"
        table.add_row(
            e.get("spec_id", "—"),
            e.get("pattern_name", "—"),
            f"[{status_style.get(status, 'white')}]{status}[/]",
            reason,
            decided,
        )
    console.print(table)


# ─────────────────────────────────────────────────────────────────────────────
# sdd regression-check  (SPEC-0030)
# ─────────────────────────────────────────────────────────────────────────────
@cli.command(
    "regression-check",
    help="Prüft eine Spec auf Konflikte mit bestehenden Specs (SPEC-0030).",
)
@click.argument("spec_id")
@click.option("--json", "output_json", is_flag=True, help="Maschinenlesbare JSON-Ausgabe.")
def regression_check(spec_id: str, output_json: bool) -> None:
    import json as _json
    from .regression_check import RegressionCheckChain

    cfg = _ensure_project()

    provider = None
    try:
        from .llm.factory import get_completion_provider
        provider = get_completion_provider(cfg, "analyzer")
    except Exception:
        pass

    chain = RegressionCheckChain(cfg.root)
    result = chain.run(spec_id, provider=provider)

    if output_json:
        print(_json.dumps(
            {
                "spec_id": result.spec_id,
                "findings": [f.to_dict() for f in result.findings],
                "llm_skipped": result.llm_skipped,
                "llm_skip_reason": result.llm_skip_reason,
            },
            indent=2,
            ensure_ascii=False,
        ))
        if any(f.severity == "error" for f in result.findings):
            sys.exit(1)
        return

    rule_findings = [f for f in result.findings if f.source == "rule"]
    llm_findings = [f for f in result.findings if f.source == "llm"]
    _sev_color = {"error": "red", "warning": "yellow", "info": "cyan"}

    console.print(f"\n[bold]Regression-Check: {spec_id}[/]")
    console.print("─" * 70)

    console.print("\n[bold dim][rule] Stufe 1 – Regelbasiert[/]")
    if rule_findings:
        for f in rule_findings:
            c = _sev_color.get(f.severity, "white")
            console.print(f"  [{c}]{f.severity.upper()}[/] {f.spec_id} · {f.own_section} ↔ {f.section}")
            console.print(f"    → {f.description}")
    else:
        console.print("  [green]✓[/] Kein regelbasierter Regressionskonflikt gefunden")

    console.print("\n[bold dim][llm] Stufe 2 – LLM-Semantik[/]")
    if result.llm_skipped:
        console.print(f"  [yellow]⚠[/] LLM-Check übersprungen ({result.llm_skip_reason})")
    elif llm_findings:
        for f in llm_findings:
            c = _sev_color.get(f.severity, "white")
            console.print(f"  [{c}]{f.severity.upper()}[/] {f.spec_id} · {f.own_section} ↔ {f.section}")
            console.print(f"    → {f.description}")
    else:
        console.print("  [green]✓[/] Kein inhaltlicher Regressionskonflikt gefunden")

    if any(f.severity == "error" for f in result.findings):
        console.print("\n[red]✗[/] Error-Severity gefunden – Regression-Check gescheitert")
        sys.exit(1)
    elif any(f.severity == "warning" for f in result.findings):
        console.print("\n[yellow]⚠[/] Warnungen vorhanden – bitte prüfen")


# ─────────────────────────────────────────────────────────────────────────────
# SOLID-Integration: spec review / contract review Erweiterung (SPEC-0015 §6.1)
# ─────────────────────────────────────────────────────────────────────────────

def _run_solid_phase(cfg: Any, artifact_id: str, artifact_type: str) -> None:
    """Sub-Phase 2b/5b: SOLID-Analyse. Gibt Findings aus, blockiert ggf. bei block-Modus."""
    from .solid import create_analyzer, find_artifact as _find

    artifact = _find(cfg, artifact_id)
    if artifact is None:
        console.print(f"[yellow]![/] SOLID-Analyse: Artefakt {artifact_id} nicht gefunden.")
        return

    artifact_text, _ = artifact
    analyzer = create_analyzer(cfg)
    report = analyzer.analyze(artifact_text, artifact_id, artifact_type)

    console.print("\n── SOLID-Analyse ──────────────────────────────────────────")
    _print_solid_report(report, cfg.solid_gate_mode())

    if cfg.solid_gate_mode() == "block" and report.has_violations():
        console.print(
            "\n[red]✗ SOLID-Violation blockiert Phasenübergang[/] "
            "(solid_gate.mode: block)"
        )
        sys.exit(2)


def _run_pattern_phase(cfg: Any, artifact_id: str, artifact_type: str) -> None:
    """Sub-Phase 2c/5c: Pattern-Vorschläge ausgeben (kein Block)."""
    from .solid import find_artifact as _find
    from .pattern import create_suggester

    suggester = create_suggester(cfg)
    if suggester is None:
        return

    artifact = _find(cfg, artifact_id)
    if artifact is None:
        return

    artifact_text, _ = artifact
    console.print("\n── Pattern-Vorschläge ─────────────────────────────────────")
    result = suggester.suggest(artifact_text, artifact_id, artifact_type)
    _print_pattern_suggestions(result)
    if result.pattern_suggestions:
        console.print(
            f"  → Entscheiden mit: [cyan]sdd pattern accept {artifact_id} <PatternName>[/]"
        )


# ── sdd dev – Isolierte Docker-Entwicklungsumgebung (SPEC-0021) ───────────────

@cli.group("dev", help="Isolierte Docker-Entwicklungsumgebung pro Spec (SPEC-0021).")
def dev_group() -> None:
    pass


@dev_group.command("start", help="Startet Docker-Container + Git-Branch für eine Spec.")
@click.argument("spec_id")
def dev_start(spec_id: str) -> None:
    cfg = _ensure_project()
    from .dev_container import DevContainerManager
    DevContainerManager(cfg).start(spec_id)


@dev_group.command("exec", help="Führt einen Befehl im Dev-Container aus.")
@click.argument("spec_id")
@click.argument("cmd", nargs=-1, required=True)
def dev_exec(spec_id: str, cmd: tuple) -> None:
    cfg = _ensure_project()
    from .dev_container import DevContainerManager
    DevContainerManager(cfg).exec_cmd(spec_id, list(cmd))


@dev_group.command("close", help="Stoppt und entfernt den Dev-Container.")
@click.argument("spec_id")
@click.option("--delete-branch", is_flag=True, help="Löscht auch den Git-Branch dev/SPEC-XXXX.")
def dev_close(spec_id: str, delete_branch: bool) -> None:
    cfg = _ensure_project()
    from .dev_container import DevContainerManager
    DevContainerManager(cfg).close(spec_id, delete_branch=delete_branch)


@dev_group.command("pr", help="Erstellt einen lokalen PR nach Validierung.")
@click.argument("spec_id")
def dev_pr(spec_id: str) -> None:
    cfg = _ensure_project()
    from .dev_container import DevContainerManager
    DevContainerManager(cfg).pr(spec_id)


@dev_group.command("build", help="Baut das Docker-Image aus dem konfigurierten Dockerfile.")
def dev_build() -> None:
    cfg = _ensure_project()
    from .dev_container import DevContainerManager
    DevContainerManager(cfg).build()


@dev_group.command("push", help="Schiebt das Image in die konfigurierte Registry.")
def dev_push() -> None:
    cfg = _ensure_project()
    from .dev_container import DevContainerManager
    DevContainerManager(cfg).push()


@dev_group.command("up", help="Startet den Compose-Stack für eine Spec.")
@click.argument("spec_id")
def dev_up(spec_id: str) -> None:
    cfg = _ensure_project()
    from .dev_container import DevContainerManager
    DevContainerManager(cfg).up(spec_id)


@dev_group.command("down", help="Stoppt den Compose-Stack für eine Spec.")
@click.argument("spec_id")
def dev_down(spec_id: str) -> None:
    cfg = _ensure_project()
    from .dev_container import DevContainerManager
    DevContainerManager(cfg).down(spec_id)


# ── SPEC-0026: LLM Task Distribution Engine ──────────────────────────────────

@cli.command("decompose", help="Zerlegt eine Spec in klassifizierte Tasks (SPEC-0026).")
@click.argument("spec_id")
@click.option("--yes", "-y", is_flag=True, help="Automatisch bestätigen ohne Interaktion.")
def decompose(spec_id: str, yes: bool) -> None:
    cfg = _ensure_project()
    from .decompose import TaskDecomposer
    decomposer = TaskDecomposer()
    console.print(f"[cyan]▶ Zerlege {spec_id} in Tasks …[/]")
    try:
        tasks = decomposer.decompose(spec_id, cfg)
    except ValueError as exc:
        console.print(f"[red]✗ {exc}[/]")
        raise SystemExit(1)

    console.print(f"\n[bold]Tasks ({len(tasks)}):[/]")
    for i, t in enumerate(tasks, 1):
        console.print(
            f"  {i:2}. [{t.complexity.value}/{t.context_size.value}] "
            f"[{t.type.value}] {t.title}"
        )
        if t.description:
            console.print(f"      {t.description[:80]}")

    if not yes:
        click.confirm("\nTask-Liste bestätigen?", abort=True)

    path = decomposer.save(tasks, cfg)
    console.print(f"[green]✓ {len(tasks)} Tasks gespeichert → {path}[/]")


@cli.command("distribute", help="Verteilt Tasks einer Spec an LLMs und erstellt PR (SPEC-0026).")
@click.argument("spec_id")
@click.option("--dry-run", is_flag=True, help="Kein echter Git-Commit, kein PR.")
def distribute(spec_id: str, dry_run: bool) -> None:
    cfg = _ensure_project()
    from .decompose import TaskDecomposer
    from .llm_pool import LlmPoolRegistry, LlmEntry, LlmType, CostTier
    from .dist_orchestrator import DistributionOrchestrator

    tasks = TaskDecomposer().load(spec_id, cfg)
    if not tasks:
        console.print(f"[red]✗ Keine Tasks für {spec_id}. Führe erst 'sdd decompose {spec_id}' aus.[/]")
        raise SystemExit(1)

    llm_pool_cfg = getattr(cfg, "llm_pool", []) or []
    registry = LlmPoolRegistry()
    for entry in llm_pool_cfg:
        registry.register(LlmEntry(
            id=entry.get("id", ""),
            type=LlmType(entry.get("type", "remote")),
            model=entry.get("model", ""),
            cost_tier=CostTier(entry.get("cost_tier", "standard")),
            max_context_tokens=int(entry.get("max_context_tokens", 100000)),
        ))

    if not registry.entries:
        from .llm_pool import LlmEntry, LlmType, CostTier
        registry.register(LlmEntry(
            id="claude-code-cli",
            type=LlmType.LOCAL,
            model="claude-code",
            cost_tier=CostTier.POWERFUL,
            max_context_tokens=200000,
        ))

    orch = DistributionOrchestrator(cfg, registry, dry_run=dry_run)
    console.print(f"[cyan]▶ Starte Distribution für {spec_id} ({len(tasks)} Tasks) …[/]")
    report = orch.run(spec_id, tasks)

    console.print(f"\n[bold]Report:[/]")
    console.print(f"  Branch:    {report.branch}")
    console.print(f"  Committed: {len(report.committed)}")
    console.print(f"  Blocked:   {len(report.blocked)}")
    if report.pr_url:
        console.print(f"  PR:        {report.pr_url}")
    if report.merged:
        console.print(f"[green]✓ PR gemergt – {spec_id} implementiert.[/]")
    elif report.error:
        console.print(f"[red]✗ {report.error}[/]")


@cli.command("task-status", help="Zeigt Status aller Tasks einer Spec (SPEC-0026).")
@click.argument("spec_id")
def task_status(spec_id: str) -> None:
    cfg = _ensure_project()
    from .decompose import TaskDecomposer
    tasks = TaskDecomposer().load(spec_id, cfg)
    if not tasks:
        console.print(f"[yellow]Keine Tasks für {spec_id}.[/]")
        return
    console.print(f"[bold]Tasks für {spec_id} ({len(tasks)}):[/]")
    for t in tasks:
        color = {
            "committed": "green", "blocked": "red",
            "running": "cyan", "review": "yellow",
        }.get(t.status.value, "white")
        console.print(
            f"  [{color}]{t.status.value:10}[/] {t.title}"
            + (f" (retry {t.retry_count})" if t.retry_count else "")
        )


# ─────────────────────────────────────────────────────────────────────────────
# sdd finalize  (SPEC-0026 unified finalization)
# ─────────────────────────────────────────────────────────────────────────────
@cli.command("finalize", help="Container-Test + PR für eine Spec (einheitlich für alle Pfade).")
@click.argument("spec_id")
@click.option("--dry-run", is_flag=True, help="Kein echter Commit, kein Container, kein PR.")
@click.option("--no-commit", is_flag=True, help="Kein git commit – Caller hat bereits committed.")
@click.option("--branch", default=None, help="Branch-Name (Default: feat/SPEC-XXXX).")
@click.option("--commit-msg", default="", help="Commit-Nachricht (Default: automatisch).")
@click.option("--skip-container", is_flag=True,
              help="Container-Check und Testlauf überspringen; Commit und PR laufen normal.")
def finalize_cmd(spec_id: str, dry_run: bool, no_commit: bool,
                 branch: str | None, commit_msg: str, skip_container: bool) -> None:
    cfg = _ensure_project()
    from .finalize import SpecFinalizer

    console.print(f"[cyan]▶ Finalisiere {spec_id} …[/]")
    finalizer = SpecFinalizer(cfg, dry_run=dry_run)
    try:
        report = finalizer.run(
            spec_id,
            commit_msg=commit_msg,
            no_commit=no_commit,
            branch=branch,
            skip_container=skip_container,
        )
    except RuntimeError as exc:
        console.print(f"[red]✗[/] {exc}")
        sys.exit(1)

    console.print(f"  Branch:  [cyan]{report.branch}[/]")
    if report.commit_hash:
        console.print(f"  Commit:  [dim]{report.commit_hash[:12]}[/]")

    if report.tests_passed:
        if "übersprungen" in report.test_output:
            console.print(f"[yellow]⚠[/] {report.test_output}")
        else:
            console.print("[green]✓[/] Tests im Container: grün")
        if report.pr_url:
            console.print(f"[green]✓[/] PR erstellt: {report.pr_url}")
        elif report.pr_path:
            console.print(f"[green]✓[/] PR-Dokument: [bold]{report.pr_path.relative_to(cfg.root)}[/]")
    else:
        console.print("[red]✗[/] Tests fehlgeschlagen:")
        console.print(f"[dim]{report.test_output[-600:]}[/]")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# sdd config  (SPEC-0027 guided configuration)
# ─────────────────────────────────────────────────────────────────────────────
@cli.group("config", help="SDD-Konfiguration anzeigen, setzen und validieren.")
def config_group() -> None:
    pass


@config_group.command("wizard", help="Interaktiver Konfigurations-Wizard.")
@click.option("--section", default=None,
              help="Nur diese Section konfigurieren (project|llm|docker|evaluator|orchestrator).")
@click.option("--non-interactive", "non_interactive", is_flag=True,
              help="Kein interaktiver Prompt – Werte aus Flags/Env-Vars.")
def config_wizard_cmd(section: str | None, non_interactive: bool) -> None:
    cfg = _ensure_project()
    from .config_wizard import ConfigWizard
    wizard = ConfigWizard(cfg.root / ".sdd" / "config.yaml")
    try:
        wizard.run(section=section, non_interactive=non_interactive)
        console.print("[green]✓[/] Konfiguration gespeichert.")
    except Exception as exc:
        console.print(f"[red]✗[/] {exc}")
        sys.exit(1)


@config_group.command("set", help="Setzt einen einzelnen Konfigurationswert (Dot-Notation).")
@click.argument("assignment", metavar="KEY=VALUE")
@click.option("--non-interactive", "non_interactive", is_flag=True)
def config_set_cmd(assignment: str, non_interactive: bool) -> None:
    if "=" not in assignment:
        console.print("[red]✗[/] Format: KEY=VALUE")
        sys.exit(1)
    key, _, value = assignment.partition("=")
    cfg = _ensure_project()
    from .config_manager import ConfigManager, ConfigValidationError, _coerce
    mgr = ConfigManager(cfg.root / ".sdd" / "config.yaml")
    try:
        mgr.set(key.strip(), _coerce(value.strip()))
        console.print(f"[green]✓[/] {key} = {value}")
    except ConfigValidationError as exc:
        console.print(f"[red]✗[/] Validierungsfehler: {exc}")
        sys.exit(1)


@config_group.command("get", help="Liest einen einzelnen Konfigurationswert.")
@click.argument("key")
def config_get_cmd(key: str) -> None:
    cfg = _ensure_project()
    from .config_manager import ConfigManager
    mgr = ConfigManager(cfg.root / ".sdd" / "config.yaml")
    value = mgr.get(key)
    if value is None:
        sys.exit(1)
    console.print(value)


@config_group.command("show", help="Zeigt die aktuelle Konfiguration.")
@click.option("--section", default=None,
              help="Nur diese Section anzeigen.")
def config_show_cmd(section: str | None) -> None:
    cfg = _ensure_project()
    from .config_manager import ConfigManager
    mgr = ConfigManager(cfg.root / ".sdd" / "config.yaml")
    console.print(mgr.show(section=section))


@config_group.command("validate", help="Prüft die gesamte Konfiguration auf Vollständigkeit.")
def config_validate_cmd() -> None:
    cfg = _ensure_project()
    from .config_manager import ConfigManager
    mgr = ConfigManager(cfg.root / ".sdd" / "config.yaml")
    errors = mgr.validate()
    if not errors:
        console.print("[green]✓[/] Konfiguration ist valide.")
    else:
        for e in errors:
            console.print(f"[red]✗[/] {e}")
        sys.exit(1)


@config_group.command("test-llm", help="Testet die Erreichbarkeit eines LLM-Providers.")
@click.option("--id", "llm_id", default=None, help="Provider-ID (leer = alle testen).")
def config_test_llm_cmd(llm_id: str | None) -> None:
    cfg = _ensure_project()
    from .config_manager import ConfigManager
    from .llm_probe import probe_llm, LlmProbeError
    mgr = ConfigManager(cfg.root / ".sdd" / "config.yaml")
    data = mgr.load()
    providers = data.get("llm_pool", {}).get("providers") or []
    if llm_id:
        providers = [p for p in providers if p.get("id") == llm_id]
        if not providers:
            console.print(f"[red]✗[/] Provider '{llm_id}' nicht gefunden.")
            sys.exit(1)
    if not providers:
        console.print("[yellow]⚠[/] Keine LLM-Provider konfiguriert.")
        sys.exit(1)
    has_error = False
    for prov in providers:
        pid = prov.get("id", "?")
        try:
            latency = probe_llm(prov)
            console.print(f"[green]✓[/] {pid}: OK ({latency:.0f} ms)")
        except LlmProbeError as exc:
            console.print(f"[red]✗[/] {pid}: {exc}")
            has_error = True
    if has_error:
        sys.exit(1)


if __name__ == "__main__":
    cli()
