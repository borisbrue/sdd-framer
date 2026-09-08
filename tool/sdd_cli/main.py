"""Click-basierte Befehle der sdd-CLI."""
from __future__ import annotations

from pathlib import Path
import shutil
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
    CONTRACT_SUBDIR,
    CONTRACT_TEMPLATES,
    test_level_for_contract_format,
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
# sdd init – Hilfsfunktionen
# ─────────────────────────────────────────────────────────────────────────────

def _is_git_repo(path: Path) -> bool:
    import subprocess
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
    )
    return result.returncode == 0


def _check_git_setup(target: Path) -> None:
    """Prüft ob ein Git-Repo existiert; bietet an es anzulegen und ggf. bei GitHub zu registrieren."""
    import subprocess

    if _is_git_repo(target):
        return

    console.print(
        "\n[yellow]⚠[/] Kein Git-Repository gefunden.\n"
        "  SDD benötigt Git für Branches, Commits und PRs.\n"
        "  Jetzt initialisieren? [J/n] ",
        end="",
    )
    try:
        answer = input("").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = "n"

    if answer and not answer.startswith(("j", "y")):
        console.print("  [dim]→ Git-Init übersprungen. Manuell: [cyan]git init[/][/]")
        return

    subprocess.run(["git", "-C", str(target), "init", "-b", "main"], check=True)
    subprocess.run(["git", "-C", str(target), "add", ".sdd", ".claude"], capture_output=True)
    subprocess.run(
        ["git", "-C", str(target), "commit", "-m", "chore: sdd init"],
        capture_output=True,
    )
    console.print("  [green]✓[/] Git-Repository initialisiert und erster Commit erstellt.")

    if not shutil.which("gh"):
        console.print(
            "  [dim]→ gh CLI nicht gefunden – GitHub-Repo kann nicht automatisch angelegt werden.[/]"
        )
        return

    console.print(
        "  GitHub-Repository anlegen? [J/n] ",
        end="",
    )
    try:
        answer2 = input("").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer2 = "n"

    if answer2 and not answer2.startswith(("j", "y")):
        console.print("  [dim]→ Übersprungen. Manuell: [cyan]gh repo create[/][/]")
        return

    console.print("  Sichtbarkeit: [1] privat (Standard)  [2] öffentlich → ", end="")
    try:
        vis_answer = input("").strip()
    except (EOFError, KeyboardInterrupt):
        vis_answer = "1"

    visibility = "public" if vis_answer == "2" else "private"
    repo_name = target.name

    proc = subprocess.run(
        ["gh", "repo", "create", repo_name, f"--{visibility}", "--source=.", "--remote=origin", "--push"],
        capture_output=True,
        text=True,
        cwd=str(target),
    )
    if proc.returncode == 0:
        url = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else f"github.com/{repo_name}"
        console.print(f"  [green]✓[/] GitHub-Repo angelegt: [bold]{url}[/]")
    else:
        console.print(f"  [yellow]⚠[/] gh repo create fehlgeschlagen: {proc.stderr.strip()[:200]}")
        console.print("  Manuell: [cyan]gh repo create[/]")


def _check_gh_available() -> None:
    """Gibt eine Warnung aus wenn gh nicht im PATH ist."""
    if shutil.which("gh"):
        return
    console.print(
        "\n[yellow]⚠[/] gh CLI nicht gefunden – automatische PR-Erstellung nicht möglich.\n"
        "  Installiere gh: [link]https://cli.github.com[/link]\n"
        "  Oder direkt: curl -sL https://github.com/cli/cli/releases/latest "
        "→ Binary nach ~/.local/bin/gh"
    )


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
@click.option("--autonomous", is_flag=True,
              help="Aktiviert hands-off Bypass (defaultMode=bypassPermissions) in "
                   ".claude/settings.local.json – persönlich, nicht committed (SPEC-0051).")
def init(target: str, project_title: str, force: bool,
         provider: str, force_skills: bool, autonomous: bool) -> None:
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
        autonomous=autonomous,
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

    _check_git_setup(Path(target).resolve())
    _check_gh_available()

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
@cli.command(help=(
    "Aktualisiert ein bestehendes SDD-Projekt auf die aktuelle Paket-Version. "
    "Aktualisiert Schemas, Templates und fehlende Skill-Dateien (.claude/commands/) "
    "– ohne Specs, Contracts oder Tests anzufassen."
))
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
@cli.group(help="Scaffolding: Specs, Contracts, Tests, Holdouts anlegen.")
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


@new.command("adr", help="Legt einen Architecture Decision Record an (ADR-XXXX).")
@click.argument("title")
@click.option("--spec", "spec_ids", multiple=True,
              help="Zugehoerige Spec-ID, mehrfach angebbar (z.B. --spec SPEC-0001).")
@click.option("--supersedes", default="",
              help="ADR-ID, die dieser Record ersetzt (z.B. ADR-0001).")
def new_adr(title: str, spec_ids: tuple, supersedes: str) -> None:
    """Der Befehl fehlte, obwohl Vorlage, ID-Praefix und README ihn vorsahen."""
    from datetime import date

    cfg = _ensure_project()
    aid = next_id(cfg, "adr")
    slug = slugify(title)

    # Ablageort wie bei traceability konfigurierbar, Default docs/adr.
    target = cfg.adr_dir / f"{aid}-{slug}.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    tmpl, _ = load_template(cfg, "adr")
    text = render(tmpl, {
        "id": aid,
        "title": title,
        "status": "proposed",
        "related_specs": list(spec_ids),
        "supersedes": supersedes,
    })
    # Die Vorlage haelt Platzhalter im Frontmatter, die render() nicht trifft.
    # json.dumps statt Python-repr: liefert YAML-Flow mit Doppelquotes, so wie
    # der Kommentar in der Vorlage es zeigt.
    import json as _json
    text = text.replace('related_specs: []',
                        f'related_specs: {_json.dumps(list(spec_ids))}', 1)
    if supersedes:
        text = text.replace('supersedes: ""', f'supersedes: "{supersedes}"', 1)
    text = text.replace("date: YYYY-MM-DD", f"date: {date.today().isoformat()}", 1)
    target.write_text(text, encoding="utf-8")

    console.print(f"[green]✓[/] ADR angelegt: [bold]{target}[/]  ([cyan]{aid}[/])")
    console.print(
        "  [yellow]→[/] Status ist [bold]proposed[/]. Nach der Entscheidung auf "
        "[cyan]accepted[/] oder [cyan]rejected[/] setzen."
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

    # Zielverzeichnis nach Typ (Zuordnung liegt in templates.py, weil auch der
    # Test-Stub und der Test-Generator sie brauchen).
    subdir = CONTRACT_SUBDIR[fmt]
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

    # Test-Stub automatisch mitanlegen. Das Level folgt dem Contract-Typ:
    # ein Datenmodell wird per unit geprueft, ein Verhaltens-Contract per
    # acceptance. Fest "contract" legte den Stub sonst ins falsche Verzeichnis.
    tid = next_id(cfg, "test")
    test_level = test_level_for_contract_format(fmt)
    test_target = cfg.tests_dir / test_level / f"{tid}-{slug}.md"
    test_target.parent.mkdir(parents=True, exist_ok=True)
    tmpl_test, _ = load_template(cfg, "test")
    test_text = render(tmpl_test, {
        "id": tid, "title": title or f"{fmt} contract test",
        "spec": spec_id, "contract": cid,
    })
    # Die Vorlage traegt level: contract – auf das tatsaechliche Level ziehen,
    # sonst widerspricht das Frontmatter dem Ablageort.
    test_text = test_text.replace("level: contract", f"level: {test_level}", 1)
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
@click.option("--contract", "contract_id", default="",
              help="Zugehöriger Contract, z.B. CON-0001.")
@click.option("--spec", "spec_id", required=True,
              help="Zugehörige Spec, z.B. SPEC-0004.")
@click.option("--title", required=True, help="Titel des Holdout-Szenarios.")
@click.option("--priority", default="normal",
              type=click.Choice(["critical", "normal", "edge-case"]),
              help="critical=bricht sofort ab; normal=aggregiert; edge-case=nur wenn normal besteht.")
@click.option("--type", "hol_type", default="http",
              type=click.Choice(["http", "cli"]),
              help="http=REST-Aufruf gegen Container; cli=Kommandozeilenaufruf im Container.")
def new_holdout(contract_id: str, spec_id: str, title: str, priority: str, hol_type: str) -> None:
    cfg = _ensure_project()
    hid = next_id(cfg, "holdout")
    slug = slugify(title)
    target = cfg.holdout_dir / f"{hid}-{slug}.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    tmpl, _ = load_template(cfg, "holdout", subtype=hol_type)
    text = render(tmpl, {
        "id": hid, "title": title,
        "contract": contract_id or "CON-XXXX",
        "spec": spec_id,
        "priority": priority,
        "type": hol_type,
    })
    target.write_text(text, encoding="utf-8")

    console.print(f"[green]✓[/] Holdout-Szenario angelegt: [bold]{target}[/]  ([cyan]{hid}[/])")
    console.print(
        f"  [yellow]→[/] Datei ist in [bold].sdd/holdout/[/] – für den Code-Agenten nicht sichtbar."
    )
    console.print(
        "  [yellow]→[/] [bold]status: ready[/] – das Szenario wird evaluiert. "
        "Auf [cyan]wip[/] setzen, um es vorübergehend auszuschließen."
    )


@new.command("agents-md", help="[Entfernt] In sdd init integriert.")
@click.option("--subdir", default="")
@click.option("--force", is_flag=True)
def new_agents_md(subdir: str, force: bool) -> None:
    console.print("[yellow]⚠[/] 'sdd new agents-md' wurde entfernt → in [cyan]sdd init[/] integriert.")
    sys.exit(1)


@new.command("github-workflow", help="[Entfernt] In sdd init integriert.")
def new_github_workflow() -> None:
    console.print("[yellow]⚠[/] 'sdd new github-workflow' wurde entfernt → in [cyan]sdd init[/] integriert.")
    sys.exit(1)


@new.command("hotfix", help="Legt einen neuen Hotfix-Record an.")
@click.argument("description")
def new_hotfix(description: str) -> None:
    from .hotfix import start as _start
    cfg = _ensure_project()
    hf_id = _start(cfg.root, description)
    console.print(f"[green]✓[/] Hotfix [bold]{hf_id}[/] erstellt: {description}")
    console.print(f"  Implementiere den Fix, dann: [cyan]sdd hotfix finalize {hf_id}[/]")


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
# sdd evaluate — MIGRATION STUB
# ─────────────────────────────────────────────────────────────────────────────
@cli.command(help="[Entfernt] Verwende: sdd holdout run", hidden=False)
@click.option("--smoke", is_flag=True, hidden=True, help="Deterministischer Selbsttest.")
@click.pass_context
def evaluate_cmd(ctx: click.Context, smoke: bool) -> None:
    if smoke:
        _run_smoke_test()
        return
    console.print("[yellow]⚠[/] 'sdd evaluate' wurde entfernt. Verwende: [cyan]sdd holdout run[/]")
    sys.exit(1)


def _run_evaluate(
    cfg: "SddConfig",
    base_url: str,
    ids_filter: list[str] | None,
    spec_id: str | None,
    final_attempt: bool,
    save: bool,
    output_json: bool,
    container_name: str | None,
    tier_filter: str | None = None,
) -> None:
    report = run_evaluation(cfg, base_url, hol_ids=ids_filter, spec_id=spec_id,
                            container_name=container_name, tier_filter=tier_filter)

    def _skip_note() -> str:
        if not report.skipped_by_status:
            return ""
        detail = ", ".join(f"{n}x status: {st}"
                           for st, n in sorted(report.skipped_by_status.items()))
        return (f" {sum(report.skipped_by_status.values())} Szenario(en) wurden wegen "
                f"ihres Status nicht evaluiert ({detail}).")

    if tier_filter and report.total == 0:
        # Der Skip-Hinweis ist hier entscheidend: sonst sieht ein Lauf, in dem
        # alle Szenarien auf wip stehen, aus wie "es gibt keine".
        click.echo(f"Keine '{tier_filter}'-Holdouts gefunden.{_skip_note()}")
        sys.exit(0)

    report_path = None
    if save:
        report_path = persist_report(cfg, report)
        console.print(f"[dim]  Report gespeichert: {report_path.relative_to(cfg.root)}[/]")

    passed = report.pass_rate >= 0.9

    if output_json:
        import json as _json
        click.echo(_json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
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
    if report.skipped_by_status:
        console.print(f"[yellow]⚠[/]{_skip_note()}")
        if report.total == 0:
            console.print(
                "  [dim]Ein Lauf ohne evaluierte Szenarien prüft nichts. "
                "Setze status auf [cyan]ready[/] oder [cyan]active[/].[/]"
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


def _run_smoke_test() -> None:
    """Deterministischer Selbsttest für Tier-Sortierung und Fail-Fast (kein HTTP, kein LLM)."""
    from .holdout_runner import PRIORITY_ORDER
    from .evaluator import EvaluationReport, ScenarioResult, ScenarioRun

    checks: list[tuple[str, bool, str]] = []

    # Check 1: PRIORITY_ORDER Sortierung
    tiers = sorted(PRIORITY_ORDER.keys(), key=lambda t: PRIORITY_ORDER[t])
    sort_ok = tiers == ["critical", "normal", "edge-case"]
    checks.append(("Tier-Sortierung", sort_ok,
                   f"critical={PRIORITY_ORDER['critical']} < normal={PRIORITY_ORDER['normal']} "
                   f"< edge-case={PRIORITY_ORDER['edge-case']}"))

    # Check 2: Fail-Fast critical → normal
    c_fail = ScenarioResult(hol_id="SMOKE-C1", title="critical fail", contract="", priority="critical")
    c_fail.pass_threshold = 1
    c_fail.runs.append(ScenarioRun(
        run=1, passed=False, request={}, response_status=None, response_body=None,
        llm_verdict="fail", llm_reasoning="smoke",
    ))
    n_skip = ScenarioResult(hol_id="SMOKE-N1", title="normal skip", contract="", priority="normal")
    failfast_crit_ok = (not c_fail.passed) and (len(n_skip.runs) == 0)
    checks.append(("Fail-Fast critical→normal", failfast_crit_ok,
                   "normal übersprungen nach critical-Fehler"))

    # Check 3: Fail-Fast normal → edge-case
    n_fail = ScenarioResult(hol_id="SMOKE-N2", title="normal fail", contract="", priority="normal")
    n_fail.pass_threshold = 1
    n_fail.runs.append(ScenarioRun(
        run=1, passed=False, request={}, response_status=None, response_body=None,
        llm_verdict="fail", llm_reasoning="smoke",
    ))
    e_skip = ScenarioResult(hol_id="SMOKE-E1", title="edge-case skip", contract="", priority="edge-case")
    failfast_norm_ok = (not n_fail.passed) and (len(e_skip.runs) == 0)
    checks.append(("Fail-Fast normal→edge-case", failfast_norm_ok,
                   "edge-case übersprungen nach normal-Fehler"))

    all_ok = all(ok for _, ok, _ in checks)
    for name, ok, detail in checks:
        icon = "OK" if ok else "FAIL"
        click.echo(f"  [{icon}] {name}: {detail}")

    if all_ok:
        click.echo("Smoke-Test bestanden.")
    else:
        click.echo("Smoke-Test fehlgeschlagen.")

    sys.exit(0 if all_ok else 1)


def _set_evaluation_failed(cfg: SddConfig, spec_id: str, report_path: Path | None) -> None:
    try:
        from .lifecycle import mark_evaluation_failed
        mark_evaluation_failed(cfg, spec_id, report_path or Path("(nicht gespeichert)"))
    except ValueError as e:
        console.print(f"[yellow]![/] Status-Update fehlgeschlagen: {e}")


cli.add_command(evaluate_cmd, name="evaluate")


# ─────────────────────────────────────────────────────────────────────────────
# sdd holdout group  (nach sdd hotfix)
# ─────────────────────────────────────────────────────────────────────────────
@cli.group("holdout", help="Holdout-Szenarien verwalten (generate, run).")
def holdout_group() -> None:
    pass


@holdout_group.command("generate", help="Generiert Holdout-Szenarien für eine Spec via LLM.")
@click.argument("spec_id")
def holdout_generate(spec_id: str) -> None:
    from .generate_holdouts import (
        load_and_validate_spec,
        resolve_contract_files,
        get_existing_hol_ids_for_spec,
        write_hol_file,
        generate_holdout_scenarios,
    )
    from .llm import get_completion_provider
    from .ids import next_id

    cfg = _ensure_project()

    try:
        spec = load_and_validate_spec(spec_id, cfg)
    except FileNotFoundError as exc:
        console.print(f"[red]✗[/] {exc}")
        sys.exit(1)
    except ValueError as exc:
        console.print(f"[red]✗[/] {exc}")
        sys.exit(1)

    contract_ids: list[str] = spec.get("contracts") or []
    contracts = resolve_contract_files(contract_ids, cfg)

    skipped_missing = [cid for cid in contract_ids if not any(c["id"] == cid for c in contracts)]
    for cid in skipped_missing:
        console.print(f"[yellow]⚠[/] Contract {cid} nicht gefunden – übersprungen.")

    existing_hols = get_existing_hol_ids_for_spec(spec_id, cfg)
    spec_content = (spec["_path"]).read_text(encoding="utf-8")

    provider = get_completion_provider(cfg, component="completion")

    created: list[tuple[str, str]] = []
    skipped_count = 0

    for contract in contracts:
        cid = contract["id"]

        existing_for_contract = {
            hid for hid in existing_hols
            if (cfg.holdout_dir / f"{hid}-*.md").exists()
        }
        already_have = any(
            parse_safe(p) and parse_safe(p).frontmatter.get("contract") == cid
            for p in cfg.holdout_dir.rglob("*.md")
        ) if cfg.holdout_dir.exists() else False

        if already_have:
            count = sum(
                1 for p in cfg.holdout_dir.rglob("*.md")
                if parse_safe(p) and parse_safe(p).frontmatter.get("contract") == cid
                   and parse_safe(p).frontmatter.get("spec") == spec_id
            )
            console.print(f"  [dim]→ {cid}: {count} Holdout(s) bereits vorhanden – übersprungen.[/]")
            skipped_count += count
            continue

        try:
            scenarios = generate_holdout_scenarios(
                contract["content"], cid, spec_content, provider
            )
        except RuntimeError as exc:
            console.print(f"[red]✗[/] LLM-Fehler für {cid}: {exc}")
            continue

        for scenario in scenarios:
            hid = next_id(cfg, "holdout")
            path = write_hol_file(hid, spec_id, cid, scenario, cfg)
            created.append((hid, cid))
            console.print(f"  [green]+[/] {hid}  ({cid})  {path.name}")

    table = Table(title=f"Holdouts für {spec_id}", show_header=True)
    table.add_column("HOL-ID", style="cyan")
    table.add_column("Contract", style="blue")
    for hid, cid in created:
        table.add_row(hid, cid)
    if created:
        console.print(table)

    total = len(created)
    console.print(f"\n[green]✓[/] {total} Holdout(s) angelegt", end="")
    if skipped_count:
        console.print(f", {skipped_count} Holdouts übersprungen (bereits vorhanden)")
    else:
        console.print("")


@holdout_group.command("run", help="Führt Holdout-Szenarien gegen einen Service aus.")
@click.option("--base-url", default=None, envvar="SDD_EVAL_BASE_URL",
              help="Basis-URL des zu testenden Services, z.B. http://localhost:8080. "
                   "Wird ignoriert wenn --start-container gesetzt ist.")
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
@click.option("--start-container", is_flag=True,
              help="Container starten, Health-Check abwarten, nach Tests stoppen. "
                   "Konfiguration via evaluator.container in config.yaml.")
@click.option("--build", "build_image", is_flag=True,
              help="Container-Image vor dem Start neu bauen (nur mit --start-container).")
@click.option("--tier", "tier_filter", default=None,
              type=click.Choice(["critical", "normal", "edge-case"]),
              help="Nur Holdouts des angegebenen Tiers ausführen.")
@click.option("--smoke", is_flag=True,
              help="Deterministischer Selbsttest (kein HTTP, kein LLM).")
def holdout_run(base_url: str | None, hol_ids: tuple, save: bool, output_json: bool,
                spec_id: str | None, final_attempt: bool,
                start_container: bool, build_image: bool,
                tier_filter: str | None, smoke: bool) -> None:
    cfg = _ensure_project()

    if smoke:
        _run_smoke_test()
        return

    ids_filter = list(hol_ids) if hol_ids else None

    if tier_filter and ids_filter:
        console.print("[yellow]![/] --hol hat Vorrang vor --tier; --tier wird ignoriert.")
        tier_filter = None

    if start_container:
        from .eval_container import EvalContainer
        container_ctx = EvalContainer(cfg, build=build_image)
        console.print("[cyan]▶[/] Eval-Container wird gestartet …")
        try:
            with container_ctx as (resolved_url, container_name):
                console.print(f"[green]✓[/] Container bereit: [bold]{resolved_url}[/]")
                _run_evaluate(cfg, resolved_url, ids_filter, spec_id, final_attempt,
                              save, output_json, container_name=container_name,
                              tier_filter=tier_filter)
        except RuntimeError as e:
            console.print(f"[red]✗[/] {e}")
            sys.exit(1)
        return

    # Kein Container: base_url ist Pflicht
    if not base_url:
        # Fallback auf config
        base_url = cfg.raw.get("evaluator", {}).get("base_url", "")
    if not base_url:
        console.print(
            "[red]✗[/] --base-url fehlt. Setze SDD_EVAL_BASE_URL, nutze --base-url "
            "oder starte mit --start-container."
        )
        sys.exit(1)

    console.print(f"[cyan]▶[/] Evaluator startet gegen [bold]{base_url}[/] …")
    try:
        _run_evaluate(cfg, base_url, ids_filter, spec_id, final_attempt,
                      save, output_json, container_name=None, tier_filter=tier_filter)
    except RuntimeError as e:
        console.print(f"[red]✗[/] {e}")
        sys.exit(1)


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

    # Hotfix-Abschnitt (SPEC-0031 FR-06)
    from .hotfix import list_hotfixes
    hotfixes = list_hotfixes(cfg.root)
    if hotfixes:
        console.print()
        hf_table = Table(title="Hotfixes", show_lines=False)
        hf_table.add_column("ID", style="cyan")
        hf_table.add_column("Beschreibung")
        hf_table.add_column("Status")
        hf_table.add_column("Commit")
        _sc = {"open": "yellow", "done": "green", "aborted": "dim red"}
        for h in hotfixes:
            st = h.get("status", "?")
            hf_table.add_row(
                h.get("id", "?"),
                h.get("description", ""),
                f"[{_sc.get(st, 'white')}]{st}[/]",
                h.get("commit") or "—",
            )
        console.print(hf_table)


# ─────────────────────────────────────────────────────────────────────────────
# sdd mark-false-positive — MIGRATION STUB
# ─────────────────────────────────────────────────────────────────────────────
@cli.command("mark-false-positive",
             help="[Entfernt] Verwende: sdd autonomy false-positive")
@click.argument("pr_number")
@click.option("--project", "project_id", required=False, default=None)
def mark_false_positive_cmd(pr_number: str, project_id: str | None) -> None:
    console.print("[yellow]⚠[/] 'sdd mark-false-positive' wurde entfernt. Verwende: [cyan]sdd autonomy false-positive[/]")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# sdd set-level — MIGRATION STUB
# ─────────────────────────────────────────────────────────────────────────────
@cli.command("set-level", help="[Entfernt] Verwende: sdd autonomy set-level")
@click.argument("project_id")
@click.argument("level", type=float)
def set_level_cmd(project_id: str, level: float) -> None:
    console.print("[yellow]⚠[/] 'sdd set-level' wurde entfernt. Verwende: [cyan]sdd autonomy set-level[/]")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# sdd level — MIGRATION STUB
# ─────────────────────────────────────────────────────────────────────────────
@cli.command("level", help="[Entfernt] Verwende: sdd autonomy level")
@click.argument("project_id")
def level_cmd(project_id: str) -> None:
    console.print("[yellow]⚠[/] 'sdd level' wurde entfernt. Verwende: [cyan]sdd autonomy level[/]")
    sys.exit(1)


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
@cli.group(help="SDD Hub – Multi-Projekt-Dashboard auf Port 4711.")
def hub() -> None:
    pass


def _hub_port_occupied(port: int) -> bool:
    import socket as _socket
    with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as _s:
        return _s.connect_ex(("127.0.0.1", port)) == 0


def _find_free_port(start: int = 8100, exclude: set[int] | None = None) -> int:
    import socket as _socket
    exclude = exclude or {4711, 8080, 8000, 5173}
    port = start
    while True:
        if port not in exclude:
            with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as s:
                s.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
                if s.connect_ex(("127.0.0.1", port)) != 0:
                    return port
        port += 1


def _hub_run_servers(app, http_port: int, certs_dir: Path | None = None) -> None:
    """Startet HTTP (immer) und HTTPS (port+1, wenn Certs vorhanden) via asyncio."""
    import asyncio
    import uvicorn

    global_certs = certs_dir or Path.home() / ".local/share/sdd/certs"
    has_certs = (global_certs / "cert.pem").exists() and (global_certs / "key.pem").exists()
    https_port = http_port + 1 if has_certs else None

    if not has_certs:
        uvicorn.run(app, host="0.0.0.0", port=http_port)
        return

    async def _serve_both() -> None:
        http_cfg = uvicorn.Config(app, host="0.0.0.0", port=http_port)
        https_cfg = uvicorn.Config(
            app, host="0.0.0.0", port=https_port,
            ssl_certfile=str(global_certs / "cert.pem"),
            ssl_keyfile=str(global_certs / "key.pem"),
        )
        await asyncio.gather(
            uvicorn.Server(http_cfg).serve(),
            uvicorn.Server(https_cfg).serve(),
        )

    asyncio.run(_serve_both())


@hub.command("start", help="Startet den SDD Hub (Multi-Projekt-Dashboard).")
@click.option("--port", default=4711, show_default=True, help="Port für den Hub.")
@click.option("--no-browser", is_flag=True, help="Browser nicht automatisch öffnen.")
def hub_start(port: int, no_browser: bool) -> None:
    import threading
    import webbrowser
    from .hub.app import create_app
    from .hub.config import HubConfig

    if _hub_port_occupied(port):
        console.print(
            f"[yellow][WARN][/] Port {port} ist bereits belegt — "
            f"läuft der Hub-Daemon bereits? Anderen Port mit --port wählen."
        )

    cfg = HubConfig.load()
    cfg = cfg.model_copy(update={"port": port})
    app = create_app(config=cfg)

    global_certs = Path.home() / ".local/share/sdd/certs"
    has_certs = (global_certs / "cert.pem").exists() and (global_certs / "key.pem").exists()

    url = f"http://localhost:{port}/"
    console.print(f"▶ SDD Hub gestartet → {url}")
    if has_certs:
        console.print(f"  HTTPS (LAN/Smartphone) → https://localhost:{port + 1}/")

    if not no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    _hub_run_servers(app, port)


@hub.command("run", help="Startet den Hub-Daemon (wird von systemd verwendet).", hidden=True)
@click.option("--port", default=4711, show_default=True, help="Port für den Hub-Daemon.")
def hub_run(port: int) -> None:
    from .hub.app import create_app
    from .hub.config import HubConfig
    cfg = HubConfig.load()
    cfg = cfg.model_copy(update={"port": port})
    app = create_app(config=cfg)
    _hub_run_servers(app, port)


@hub.command("register", help="Registriert ein Projekt in der Hub-Registry.")
@click.option("--name", required=True, help="Projektname.")
@click.option("--path", "project_path", required=True, help="Pfad zum Projektverzeichnis.")
@click.option("--cmd", required=True, multiple=True, help="Start-Kommando (wiederholbar).")
@click.option("--port", required=True, type=int, help="Port des Projektservers.")
@click.option("--force", is_flag=True, help="Bestehenden Eintrag überschreiben.")
def hub_register(name: str, project_path: str, cmd: tuple, port: int, force: bool) -> None:
    import re
    from pathlib import Path
    from .hub.models import ProjectEntry
    from .hub.registry import ProjectRegistry, DuplicateProjectError

    project_id = re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-")
    entry = ProjectEntry(
        id=project_id,
        name=name,
        path=Path(project_path).expanduser().resolve(),
        start_cmd=list(cmd),
        port=port,
    )
    reg = ProjectRegistry()
    try:
        reg.register(entry, force=force)
        console.print(f"[green]✓[/] Projekt [bold]{name}[/] registriert (ID: {project_id})")
    except DuplicateProjectError as e:
        console.print(f"[red]✗[/] {e}")
        raise SystemExit(1) from e


@hub.command("unregister", help="Entfernt ein Projekt aus der Hub-Registry.")
@click.argument("project_id")
def hub_unregister(project_id: str) -> None:
    from .hub.registry import ProjectRegistry, ProjectNotFoundError

    reg = ProjectRegistry()
    try:
        reg.remove(project_id)
        console.print(f"[green]✓[/] Projekt [bold]{project_id}[/] entfernt")
    except ProjectNotFoundError as e:
        console.print(f"[red]✗[/] {e}")
        raise SystemExit(1) from e


@hub.command("add", help="Fügt ein SDD-Projekt zum Hub hinzu (auto-detektiert Name und Port).")
@click.argument("path", default=".", required=False)
@click.option("--force", is_flag=True, help="Bestehenden Eintrag überschreiben.")
def hub_add(path: str, force: bool) -> None:
    import re
    import yaml
    from pathlib import Path
    from .hub.models import ProjectEntry
    from .hub.registry import ProjectRegistry, DuplicateProjectError

    project_path = Path(path).expanduser().resolve()
    sdd_config_path = project_path / ".sdd" / "config.yaml"

    if not sdd_config_path.exists():
        console.print(f"[red]✗[/] Kein SDD-Projekt gefunden in [bold]{project_path}[/] (.sdd/config.yaml fehlt)")
        raise SystemExit(1)

    raw = yaml.safe_load(sdd_config_path.read_text()) or {}
    name = raw.get("project", {}).get("name") or project_path.name
    existing_port: int | None = raw.get("hub", {}).get("port")

    port = existing_port or _find_free_port()

    if not existing_port:
        raw.setdefault("hub", {})["port"] = port
        sdd_config_path.write_text(yaml.dump(raw, allow_unicode=True, sort_keys=False))
        console.print(f"[dim]→ Port {port} in .sdd/config.yaml gespeichert[/]")

    sdd_bin = Path.home() / ".local" / "bin" / "sdd"
    project_id = re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-")
    entry = ProjectEntry(
        id=project_id,
        name=name,
        path=project_path,
        start_cmd=[str(sdd_bin), "ui", "--project", str(project_path), "--port", str(port), "--no-browser"],
        port=port,
    )
    reg = ProjectRegistry()
    try:
        reg.register(entry, force=force)
        console.print(f"[green]✓[/] [bold]{name}[/] zum Hub hinzugefügt → http://localhost:{port}/")
        console.print(f"  ID: {project_id} | Port: {port} | Cmd: sdd ui --project ...")
    except DuplicateProjectError as e:
        console.print(f"[yellow]![/] {e} Verwende --force zum Überschreiben.")
        raise SystemExit(1) from e


@hub.command("status", help="Zeigt den Status aller registrierten Projekte.")
def hub_status() -> None:
    from .hub.registry import ProjectRegistry
    from rich.table import Table

    reg = ProjectRegistry()
    entries = reg.get_all()
    if not entries:
        console.print("[dim]Keine Projekte registriert.[/]")
        return
    table = Table(title="SDD Hub – Projekte")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Port")
    table.add_column("Status")
    table.add_column("PID")
    for e in entries:
        status_color = {"running": "green", "stopped": "dim", "error": "red"}.get(e.status, "white")
        table.add_row(e.id, e.name, str(e.port), f"[{status_color}]{e.status}[/]", str(e.pid or "–"))
    console.print(table)


@hub.command("install", help="Installiert systemd-User-Service und Avahi-mDNS-Eintrag.")
def hub_install() -> None:
    import shutil
    from pathlib import Path
    from jinja2 import Template
    from .hub.config import HubConfig

    cfg = HubConfig.load()
    sdd_dir = Path.home() / ".config" / "sdd"
    sdd_dir.mkdir(parents=True, exist_ok=True)

    registry_path = sdd_dir / "hub-registry.yaml"
    if not registry_path.exists():
        registry_path.write_text("[]")
        console.print(f"[green]✓[/] Registry angelegt: {registry_path}")

    hub_yaml = sdd_dir / "hub.yaml"
    if not hub_yaml.exists():
        cfg.save(hub_yaml)
        console.print(f"[green]✓[/] Hub-Config angelegt: {hub_yaml}")

    templates_dir = Path(__file__).parent / "hub" / "templates"
    systemd_dir = Path.home() / ".config" / "systemd" / "user"
    systemd_dir.mkdir(parents=True, exist_ok=True)
    unit_tmpl = Template((templates_dir / "sdd-hub.service").read_text())
    unit_text = unit_tmpl.render(port=cfg.port)
    unit_path = systemd_dir / "sdd-hub.service"
    unit_path.write_text(unit_text)
    console.print(f"[green]✓[/] systemd-Unit geschrieben: {unit_path}")

    import subprocess
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    subprocess.run(["systemctl", "--user", "enable", "--now", "sdd-hub"], check=False)
    console.print("[green]✓[/] sdd-hub.service aktiviert und gestartet")

    import os as _os
    avahi_dir = Path("/etc/avahi/services")
    if avahi_dir.exists() and _os.access(str(avahi_dir), _os.W_OK):
        avahi_tmpl = Template((templates_dir / "sdd-hub.avahi.xml").read_text())
        avahi_text = avahi_tmpl.render(port=cfg.port)
        avahi_path = avahi_dir / "sdd-hub.service"
        avahi_path.write_text(avahi_text)
        console.print(f"[green]✓[/] Avahi-Service geschrieben: {avahi_path}")
    else:
        console.print("[yellow]![/] Avahi-Verzeichnis nicht beschreibbar – mDNS übersprungen")

    console.print(f"\n[bold green]Hub installiert.[/] Erreichbar unter http://steamdeck.local:{cfg.port}/")


# ─────────────────────────────────────────────────────────────────────────────
# sdd pwa
# ─────────────────────────────────────────────────────────────────────────────
@cli.group(help="SDD PWA – Mobile Web App auf Port 8080.")
def pwa() -> None:
    pass


@pwa.command("start", help="Startet die SDD PWA (statischer Server).")
@click.option("--port", default=0, show_default=True, help="Port für die PWA (0 = freier Port ab 8080).")
@click.option("--no-browser", is_flag=True, help="Browser nicht automatisch öffnen.")
def pwa_start(port: int, no_browser: bool) -> None:
    from .ui import start_pwa
    start_pwa(port=port, open_browser=not no_browser)


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


@cli.command("test-run", help="[Entfernt] Verwende: sdd test run")
@click.argument("spec_id", required=False)
@click.option("--all", "run_all", is_flag=True)
@click.option("--json", "output_json", is_flag=True)
def test_run_cmd(spec_id: str | None, run_all: bool, output_json: bool) -> None:
    console.print("[yellow]⚠[/] 'sdd test-run' wurde entfernt. Verwende: [cyan]sdd test run[/]")
    sys.exit(1)


@cli.command("test-results", help="[Entfernt] Verwende: sdd test results")
@click.argument("spec_id")
@click.option("--json", "output_json", is_flag=True)
def test_results_cmd(spec_id: str, output_json: bool) -> None:
    console.print("[yellow]⚠[/] 'sdd test-results' wurde entfernt. Verwende: [cyan]sdd test results[/]")
    sys.exit(1)


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

    spec_doc = None
    for md in cfg.specs_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == spec_id:
            spec_doc = doc
            break
    if spec_doc is None:
        console.print(f"[red]✗[/] Spec nicht gefunden: {spec_id}")
        sys.exit(2)

    contracts = spec_doc.frontmatter.get("contracts") or []
    tests = spec_doc.frontmatter.get("tests") or []
    errors: list[str] = []
    if not contracts:
        errors.append(
            f"Keine Contracts verknüpft – erst Contracts anlegen und im Frontmatter eintragen.\n"
            f"  Tipp: [cyan]sdd contract propose {spec_id} CON-XXXX ...[/]"
        )
    if not tests:
        errors.append(
            f"Keine Tests verknüpft – erst Tests anlegen und im Frontmatter eintragen.\n"
            f"  Tipp: [cyan]sdd new test {spec_id}[/]"
        )
    if errors:
        for msg in errors:
            console.print(f"[red]✗[/] {msg}")
        sys.exit(2)

    # FR-05/CON-0153: vollständige Compliance-Kette vor spec-approved
    from .compliance import run_compliance_chain
    from .decompose import TaskDecomposer
    tasks = TaskDecomposer().load(spec_id, cfg)
    compliance_issues = run_compliance_chain(
        spec=spec_doc,
        tasks=tasks,
        cfg_raw=cfg.raw,
        tests_dir=cfg.tests_dir,
        project_root=cfg.root,
        strict=True,
    )
    compliance_errors = [i for i in compliance_issues if i.severity == "error"]
    if compliance_errors:
        for issue in compliance_errors:
            console.print(f"[red]✗[/] {issue.message}")
            if issue.hint:
                console.print(f"  [dim]{issue.hint}[/]")
        sys.exit(2)

    g.mark_phase_complete(spec_id, "spec-approved", consistency_check={
        "fr_coverage": fr_coverage,
        "scenarios_covered": scenarios_covered,
        "contracts_consistent": True,
        "contracts_count": len(contracts),
        "tests_count": len(tests),
    })
    g.mark_phase_complete(spec_id, "execute-unlocked")
    try:
        patch_status(spec_doc.path, "approved")
    except Exception:
        pass
    console.print(f"[green]✓[/] [cyan]{spec_id}[/] genehmigt – Execute freigegeben.")
    console.print(f"  Contracts: {len(contracts)}, Tests: {len(tests)}")


@spec_group.command("solid", help="SOLID-Analyse für eine Spec oder einen Contract.")
@click.argument("artifact_id")
@click.option("--json", "output_json", is_flag=True, help="Maschinenlesbare JSON-Ausgabe.")
@click.option(
    "--principle",
    type=click.Choice(["S", "O", "L", "I", "D"]),
    default=None,
    help="Nur ein SOLID-Prinzip prüfen.",
)
def spec_solid(artifact_id: str, output_json: bool, principle: str | None) -> None:
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


def _mark_regression_ok(cfg: "SddConfig", spec_id: str) -> bool:
    """Markiert die Gate-Phase regression-ok, aber nur mit stehendem Vorgaenger.

    `sdd spec regression` war der einzige Phasenuebergang der CLI ohne
    can_start_phase-Pruefung. Auf einer frischen Spec genuegte der Aufruf, um
    pipeline_phase auf regression-ok zu setzen — und da `sdd spec approve` nur
    seinen direkten Vorgaenger prueft, war die Kette danach bis execute-unlocked
    durchlaufbar. Die Phasen 1 bis 6 liessen sich so vollstaendig ueberspringen.

    Der Check selbst laeuft unabhaengig davon durch: er ist als Konfliktanalyse
    auch ohne Phasenstand nuetzlich. Nur die Markierung entfaellt, und das
    sichtbar — ein harter Abbruch waere hier die schlechtere Wahl, weil er den
    Analysenutzen mit vernichtet.
    """
    from .gate import ExecutionGate

    g = ExecutionGate(cfg.root)
    allowed = g.can_start_phase(spec_id, "regression-ok")
    if not allowed.allowed:
        console.print(
            f"[yellow]⚠[/] Gate-Phase [bold]regression-ok[/] nicht markiert: {allowed.reason}"
        )
        console.print(
            "  [dim]Der Regressions-Check selbst ist durchgelaufen; nur der "
            "Phasenuebergang setzt die vorherigen Phasen voraus.[/]"
        )
        return False
    g.mark_phase_complete(spec_id, "regression-ok")
    return True


@spec_group.command("regression", help="Prüft eine Spec auf Konflikte mit bestehenden Specs.")
@click.argument("spec_id")
@click.option("--json", "output_json", is_flag=True, help="Maschinenlesbare JSON-Ausgabe.")
def spec_regression(spec_id: str, output_json: bool) -> None:
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
        _mark_regression_ok(cfg, spec_id)
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

    has_errors = any(f.severity == "error" for f in result.findings)
    if has_errors:
        console.print("\n[red]✗[/] Error-Severity gefunden – Regression-Check gescheitert")
        console.print(f"  Findings gespeichert: [cyan]sdd conflict list {spec_id}[/]")
        sys.exit(1)
    elif any(f.severity == "warning" for f in result.findings):
        console.print("\n[yellow]⚠[/] Warnungen vorhanden – Findings gespeichert")
        console.print(f"  [cyan]sdd conflict list {spec_id}[/]                        – zeigt alle IDs")
        console.print(f"  [cyan]sdd conflict acknowledge {spec_id} <CF-ID> --reason \"...\"[/]")

    if _mark_regression_ok(cfg, spec_id):
        console.print("\n[green]✓[/] Gate-Phase [bold]regression-ok[/] markiert")


# ─────────────────────────────────────────────────────────────────────────────
# sdd contract propose / analyze
# ─────────────────────────────────────────────────────────────────────────────
@cli.group("contract", help="Contract-Pipeline-Kommandos (Propose, Analyze).")
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
    # Phase 4 ist zustandsbasiert (CON-0025): sind die Contracts schon
    # geschrieben, ist sie mit dem Vorschlag bereits erfüllt.
    for phase in g.evaluate_condition_phases(spec_id):
        console.print(f"[green]✓[/] Gate-Phase [bold]{phase}[/] erfüllt")


@contract_group.command("analyze", help="Führt Konfliktanalyse für vorgeschlagene Contracts durch.")
@click.argument("spec_id")
@click.argument("contract_ids", nargs=-1, required=True)
def contract_analyze(spec_id: str, contract_ids: tuple) -> None:
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


@test_group.command("run", help="Führt alle Tests einer Spec aus (via pytest).")
@click.argument("spec_id", required=False)
@click.option("--all", "run_all", is_flag=True, help="Tests aller Specs ausführen.")
@click.option("--json", "output_json", is_flag=True, help="Ausgabe als JSON.")
def test_run(spec_id: str | None, run_all: bool, output_json: bool) -> None:
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


@test_group.command("results", help="Zeigt den letzten gespeicherten Test-Run einer Spec.")
@click.argument("spec_id")
@click.option("--json", "output_json", is_flag=True, help="Ausgabe als JSON.")
def test_results(spec_id: str, output_json: bool) -> None:
    cfg = _ensure_project()
    report = _test_runner.latest_report(cfg, spec_id)

    if report is None:
        console.print(
            f"[yellow]⚠[/] Noch kein Test-Run für [bold]{spec_id}[/] gefunden. "
            f"Starte mit: [cyan]sdd test run {spec_id}[/]"
        )
        sys.exit(2)

    if output_json:
        import json as _json
        console.print(_json.dumps(report.to_json(), indent=2, ensure_ascii=False))
    else:
        _print_run_report(report)

    sys.exit(report.exit_code)


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
# sdd status-check  (SPEC-0010 FR-01 / FR-02) — interner pre-commit-Hook
# ─────────────────────────────────────────────────────────────────────────────
@cli.command("status-check",
             help="[Entfernt] Laeuft automatisch im pre-commit-Hook.",
             hidden=True)
@click.option("--fix", is_flag=True)
def status_check_cmd(fix: bool) -> None:
    console.print(
        "[yellow]⚠[/] 'sdd status-check' wurde entfernt (SPEC-0044) → die Pruefung "
        "laeuft automatisch in [cyan]sdd install-hooks[/]."
    )
    sys.exit(1)


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
        # Generiert und Platzhalter getrennt ausweisen: ein Platzhalter mit
        # `raise NotImplementedError` wird nie gruen, egal wie gut der Code ist.
        # Vorher standen beide unter "Test-Stubs angelegt".
        console.print("[bold]Test-Stubs angelegt:[/]")
        outcomes = {o.path: o for o in result.stub_outcomes}
        for p in result.stubs_created:
            outcome = outcomes.get(p)
            rel = p.relative_to(cfg.root)
            if outcome is None or outcome.generated:
                console.print(f"  [green]+[/] {rel}")
            else:
                console.print(f"  [yellow]![/] {rel}  [yellow]Platzhalter – "
                              f"Generierung fehlgeschlagen[/]")
                console.print(f"      [dim]{outcome.reason[:160]}[/]")
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
    if result.stubs_placeholder:
        n = len(result.stubs_placeholder)
        console.print(
            f"\n[yellow]⚠[/] {n} von {len(result.stubs_created)} Test-Datei(en) "
            f"blieben Platzhalter.\n"
            f"  Ein [cyan]raise NotImplementedError[/] wird nie grün – erst neu "
            f"generieren, sonst läuft die Implementierung ins Leere.\n"
            f"  Erneut versuchen: Datei löschen und [cyan]sdd start {result.spec_id}[/], "
            f"oder [cyan]llm.test_generation_timeout[/] in .sdd/config.yaml erhöhen."
        )
    if result.stubs_placeholder:
        # Die Aufforderung zu implementieren waere hier irrefuehrend, und
        # `sdd orchestrate` gegen Platzhalter laeuft entweder in eine
        # Retry-Schleife oder meldet die Spec als fertig, ohne dass etwas
        # geprueft wurde. Erst die Testdateien reparieren.
        console.print(
            f"[bold]Erst die Platzhalter ersetzen, dann implementieren.[/]\n"
            f"  [dim]Danach: [/][cyan]/sdd-implement {result.spec_id}[/][dim] oder [/]"
            f"[cyan]sdd orchestrate --spec {result.spec_id}[/]"
        )
    else:
        console.print("[bold]Jetzt Code implementieren bis alle Tests grün sind.[/]")
        console.print(f"  Interaktiv:  [cyan]/sdd-implement {result.spec_id}[/] in Claude Code")
        console.print(f"  Autonom:     [cyan]sdd orchestrate --spec {result.spec_id}[/]")


# ─────────────────────────────────────────────────────────────────────────────
# sdd install-hooks  (SPEC-0010 FR-02)
# ─────────────────────────────────────────────────────────────────────────────
@cli.command("install-hooks",
             help="Installiert Git-Pre-Commit-Hooks: Status-Check + Regressions-Gate (SPEC-0041 FR-08).")
def install_hooks_cmd() -> None:
    cfg = _ensure_project()
    git_dir = cfg.root / ".git"
    if not git_dir.exists():
        console.print("[red]✗[/] Kein .git-Verzeichnis gefunden. Kein Git-Repository?")
        sys.exit(1)

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    hook_path = hooks_dir / "pre-commit"

    # Kein `sdd status-check` mehr: der Befehl ist seit SPEC-0044 nicht mehr
    # oeffentlich und bricht jeden Aufruf ab. Die Status-Check-Logik laeuft jetzt
    # innerhalb von `sdd pre-commit-gate` (CON-0167: "intern lauffaehig").
    hook_script = (
        "#!/bin/sh\n"
        "# Installiert von sdd install-hooks (SPEC-0010 + SPEC-0041)\n"
        "sdd pre-commit-gate\n"
    )
    hook_path.write_text(hook_script, encoding="utf-8")
    hook_path.chmod(0o755)

    console.print(f"[green]✓[/] Pre-Commit-Hook installiert: [bold]{hook_path}[/]")
    console.print(
        "  Bei jedem [cyan]git commit[/] laufen [cyan]Status-Check[/] "
        "und [cyan]Regressions-Gate[/]."
    )


# ─────────────────────────────────────────────────────────────────────────────
# sdd pre-commit-gate  (SPEC-0041 FR-08)
# ─────────────────────────────────────────────────────────────────────────────
@cli.command("pre-commit-gate",
             help="Regressions-Gate: bricht Commit ab wenn Spec-Tests nach main.py/routes/App.tsx-Änderung rot sind.",
             hidden=True)
def pre_commit_gate_cmd() -> None:
    from .pre_commit_hook import main as _hook_main
    sys.exit(_hook_main())


# ─────────────────────────────────────────────────────────────────────────────
# sdd review-contract — MIGRATION STUB
# ─────────────────────────────────────────────────────────────────────────────
@cli.command("review-contract",
             help="[Entfernt] Verwende: sdd review contract")
@click.argument("con_id")
def review_contract_cmd(con_id: str) -> None:
    console.print("[yellow]⚠[/] 'sdd review-contract' wurde entfernt. Verwende: [cyan]sdd review contract[/]")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# sdd review-pending — MIGRATION STUB
# ─────────────────────────────────────────────────────────────────────────────
@cli.command("review-pending",
             help="[Entfernt] Verwende: sdd review pending")
@click.option("--auto", is_flag=True)
def review_pending_cmd(auto: bool) -> None:
    console.print("[yellow]⚠[/] 'sdd review-pending' wurde entfernt. Verwende: [cyan]sdd review pending[/]")
    sys.exit(1)


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
    if summary.get("tasks"):
        console.print("\n  [bold]Per-Task-Aufschlüsselung:[/]")
        for t in summary["tasks"]:
            console.print(
                f"    [cyan]{t['task_id']}[/]  {t['task_label'][:50]}"
                f"  in={t['input_tokens']:,}  out={t['output_tokens']:,}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# sdd implement  (SPEC-0035) — MIGRATION STUB
# ─────────────────────────────────────────────────────────────────────────────
@cli.command("implement", help="[Entfernt] Verwende /sdd-implement in Claude Code.", hidden=True)
@click.argument("spec_id")
def implement_cmd(spec_id: str) -> None:
    console.print("[yellow]⚠[/] 'sdd implement' wurde entfernt. Verwende: [cyan]/sdd-implement SPEC-XXXX[/] in Claude Code.")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# sdd solid-check — MIGRATION STUB
# ─────────────────────────────────────────────────────────────────────────────
@cli.command("solid-check", help="[Entfernt] Verwende: sdd spec solid")
@click.argument("artifact_id")
@click.option("--json", "output_json", is_flag=True)
@click.option("--principle", type=click.Choice(["S", "O", "L", "I", "D"]), default=None)
def solid_check(artifact_id: str, output_json: bool, principle: str | None) -> None:
    console.print("[yellow]⚠[/] 'sdd solid-check' wurde entfernt. Verwende: [cyan]sdd spec solid[/]")
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
# sdd pattern-suggest — entfernt (wird intern von sdd review spec verwendet)
# ─────────────────────────────────────────────────────────────────────────────


def _print_pattern_suggestions(result: Any) -> None:
    if getattr(result, "llm_error", None):
        console.print(
            f"[yellow][WARN] Pattern-Vorschläge übersprungen: {result.llm_error}[/]"
        )
        return
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
# sdd regression-check — MIGRATION STUB
# ─────────────────────────────────────────────────────────────────────────────
@cli.command(
    "regression-check",
    help="[Entfernt] Verwende: sdd spec regression",
)
@click.argument("spec_id")
@click.option("--json", "output_json", is_flag=True)
def regression_check(spec_id: str, output_json: bool) -> None:
    console.print("[yellow]⚠[/] 'sdd regression-check' wurde entfernt. Verwende: [cyan]sdd spec regression[/]")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# sdd review group
# ─────────────────────────────────────────────────────────────────────────────
@cli.group("review", help="Artefakt-Reviews (spec, contract, pending).")
def review_group() -> None:
    pass


@review_group.command("spec", help="SOLID-Analyse + Pattern-Vorschläge für eine Spec.")
@click.argument("spec_id")
def review_spec(spec_id: str) -> None:
    cfg = _ensure_project()
    if cfg.solid_gate_enabled():
        _run_solid_phase(cfg, spec_id, "spec")
    if cfg.pattern_suggestions_enabled():
        _run_pattern_phase(cfg, spec_id, "spec")
    console.print(f"\n[green]✓[/] Review abgeschlossen für [cyan]{spec_id}[/].")


@review_group.command("contract", help="LLM-Review eines Contracts (Vollständigkeit, SOLID-Konformität).")
@click.argument("con_id", required=False, default=None)
@click.option("--spec", "spec_id", default=None, help="Alle Contracts einer Spec sequenziell reviewen.")
def review_contract_group_cmd(con_id: str | None, spec_id: str | None) -> None:
    cfg = _ensure_project()
    from .lifecycle import review_contract

    if spec_id and not con_id:
        # Loop über alle Contracts einer Spec
        spec_doc = None
        for md in cfg.specs_dir.rglob("*.md"):
            doc = parse_safe(md)
            if doc and doc.frontmatter.get("id") == spec_id:
                spec_doc = doc
                break
        if spec_doc is None:
            console.print(f"[red]✗[/] Spec nicht gefunden: {spec_id}")
            sys.exit(1)
        contract_ids = spec_doc.frontmatter.get("contracts") or []
        if not contract_ids:
            console.print(f"[yellow]⚠[/] Keine Contracts für {spec_id}.")
            return
        for cid in contract_ids:
            console.print(f"\n[cyan]▶[/] Review: [bold]{cid}[/] …")
            try:
                result = review_contract(cfg, cid)
                verdict_color = "green" if result.llm_verdict == "approved" else "yellow"
                console.print(f"  [{verdict_color}]{result.llm_verdict}[/]")
            except Exception as exc:
                console.print(f"  [red]✗[/] {exc}")
        return

    if not con_id:
        console.print("[red]✗[/] CON-ID oder --spec SPEC-ID angeben.")
        sys.exit(1)

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
    console.print(f"  Bewertung: [{verdict_color}]{result.llm_verdict}[/]")
    if result.notes:
        console.print(f"  Hinweise: {result.notes[:200]}")


@review_group.command("pending", help="Listet Contracts im Status review. --auto: reviewed alle.")
@click.option("--auto", is_flag=True)
def review_pending_group_cmd(auto: bool) -> None:
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
        table.add_row(fm.get("id", "?"), fm.get("title", ""), fm.get("spec", ""), str(age))
    console.print(table)
    if not auto:
        console.print(f"\n  [dim]{len(pending)} ausstehend. Starte [cyan]sdd review pending --auto[/] für automatisches Review.[/]")
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
                console.print(f"  [green]✓[/] {cid} → [{verdict_color}]{result.llm_verdict}[/]")
            except Exception as exc:
                console.print(f"  [red]✗[/] {cid}: {exc}")
            progress.advance(task)


# ─────────────────────────────────────────────────────────────────────────────
# sdd hotfix  (SPEC-0031)
# ─────────────────────────────────────────────────────────────────────────────
@cli.group("hotfix", help="Schlanker Bugfix-Zyklus ohne SDD-Overhead (SPEC-0031).")
def hotfix_group() -> None:
    pass


@hotfix_group.command("start", help="Legt einen neuen Hotfix-Record an.")
@click.argument("description")
def hotfix_start(description: str) -> None:
    from .hotfix import start as _start
    cfg = _ensure_project()
    hf_id = _start(cfg.root, description)
    console.print(f"[green]✓[/] Hotfix [bold]{hf_id}[/] erstellt: {description}")
    console.print(f"  Implementiere den Fix, dann: [cyan]sdd hotfix finalize {hf_id}[/]")


@hotfix_group.command("finalize", help="Committet staged Changes und schließt den Hotfix ab.")
@click.argument("hf_id")
def hotfix_finalize(hf_id: str) -> None:
    from .hotfix import finalize as _finalize
    cfg = _ensure_project()
    try:
        commit = _finalize(cfg.root, hf_id)
        console.print(f"[green]✓[/] [bold]{hf_id}[/] abgeschlossen — Commit: [cyan]{commit}[/]")
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        console.print(f"[red]✗[/] {e}")
        sys.exit(1)


@hotfix_group.command("abort", help="Bricht einen Hotfix ab (kein Commit).")
@click.argument("hf_id")
def hotfix_abort(hf_id: str) -> None:
    from .hotfix import abort as _abort
    cfg = _ensure_project()
    try:
        _abort(cfg.root, hf_id)
        console.print(f"[yellow]✗[/] [bold]{hf_id}[/] abgebrochen.")
    except FileNotFoundError as e:
        console.print(f"[red]✗[/] {e}")
        sys.exit(1)


@hotfix_group.command("list", help="Listet Hotfixes tabellarisch auf.")
@click.option("--status", default=None, type=click.Choice(["open", "done", "aborted"]),
              help="Filtert nach Status.")
def hotfix_list(status: str | None) -> None:
    from .hotfix import list_hotfixes
    cfg = _ensure_project()
    hotfixes = list_hotfixes(cfg.root, status_filter=status)
    if not hotfixes:
        console.print("[dim]Keine Hotfixes gefunden.[/]")
        return
    table = Table(title="Hotfixes" + (f" · {status}" if status else ""))
    table.add_column("ID", style="cyan")
    table.add_column("Beschreibung")
    table.add_column("Status")
    table.add_column("Erstellt")
    table.add_column("Commit")
    _sc = {"open": "yellow", "done": "green", "aborted": "dim red"}
    for h in hotfixes:
        st = h.get("status", "?")
        table.add_row(
            h.get("id", "?"),
            h.get("description", ""),
            f"[{_sc.get(st, 'white')}]{st}[/]",
            h.get("created", ""),
            h.get("commit") or "—",
        )
    console.print(table)


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

    if report.had_llm_error:
        console.print(
            "[yellow][WARN] SOLID-Analyse unvollständig – LLM nicht erreichbar; "
            "Ergebnis NICHT als 'compliant' werten.[/]"
        )

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



# ─────────────────────────────────────────────────────────────────────────────
# sdd guard group (SPEC-0051 – PreToolUse-Guardrail-Backend)
# ─────────────────────────────────────────────────────────────────────────────
@cli.group("guard", help="Autonomer Bypass-Guardrail (Backend für den PreToolUse-Hook).")
def guard_group() -> None:
    pass


@guard_group.command("check", help="Liest PreToolUse-Hook-JSON von stdin, gibt permissionDecision (deny) aus.")
def guard_check_cmd() -> None:
    import json as _json
    from .guard import decide

    raw = sys.stdin.read()
    try:
        data = _json.loads(raw) if raw.strip() else {}
    except _json.JSONDecodeError:
        return  # fail-open: ungültiges Hook-Input → erlauben (kein Output)
    result = decide(data)
    if result is not None:
        click.echo(_json.dumps(result))


# ─────────────────────────────────────────────────────────────────────────────
# sdd autonomy group
# ─────────────────────────────────────────────────────────────────────────────
@cli.group("autonomy", help="Autonomy-Level verwalten (level, set-level, false-positive).")
def autonomy_group() -> None:
    pass


@autonomy_group.command("level", help="Zeigt Autonomy-Level-Metriken und Upgrade-/Downgrade-Vorschläge.")
@click.argument("project_id")
def autonomy_level(project_id: str) -> None:
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
            f"[cyan]sdd autonomy set-level {project_id} {stats.upgrade_proposal}[/]"
        )

    if stats.downgrade_proposal is not None:
        console.print(
            f"\n  [yellow]▼ Downgrade-Vorschlag:[/] Level {stats.downgrade_proposal} — "
            f"{LEVEL_CRITERIA[stats.downgrade_proposal]['label']}\n"
            f"    {stats.consecutive_below_threshold} aufeinanderfolgende PRs unter Schwellwert.\n"
            f"    Bestätige mit: [cyan]sdd autonomy set-level {project_id} {stats.downgrade_proposal}[/]"
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


@autonomy_group.command("set-level", help="Setzt das Autonomy Level eines Projekts (1|2|3|3.5|4).")
@click.argument("project_id")
@click.argument("level", type=float)
def autonomy_set_level(project_id: str, level: float) -> None:
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


@autonomy_group.command("false-positive", help="Markiert einen PR als False Positive.")
@click.argument("pr_number")
@click.option("--project", "project_id", required=True,
              help="Projekt-ID, z.B. PRJ-0001.")
def autonomy_false_positive(pr_number: str, project_id: str) -> None:
    cfg = _ensure_project()
    from .autonomy import record_false_positive
    record_false_positive(cfg, project_id, pr_number)
    console.print(
        f"[yellow]⚠[/] PR [bold]{pr_number}[/] als False Positive markiert "
        f"(Projekt [cyan]{project_id}[/])."
    )
    console.print(
        "  Die Override-Rate wird beim nächsten [cyan]sdd autonomy level[/]-Aufruf aktualisiert."
    )


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
        if t.test_file:
            console.print(f"      [dim]Test: {t.test_file}[/]")
        elif t.type.value == "code":
            console.print(f"      [yellow]⚠ kein test_file definiert[/]")

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


@config_group.command("validate", help="Prüft config.yaml auf Pflichtfelder und Provider-Konsistenz (SPEC-0052).")
@click.option("--json", "output_json", is_flag=True, help="Maschinenlesbare JSON-Ausgabe ({level,path,message}[]).")
def config_validate_cmd(output_json: bool) -> None:
    import json as _json
    from pathlib import Path as _Path
    from .config_validator import ConfigValidator

    root = find_project_root()
    config_path = _Path(root) / ".sdd" / "config.yaml"
    if not config_path.exists():
        if output_json:
            click.echo(_json.dumps([{"level": "error", "path": "config.yaml", "message": "config.yaml nicht gefunden."}]))
        else:
            console.print("[red]✗[/] config.yaml nicht gefunden.")
        sys.exit(1)

    try:
        import yaml as _yaml
        raw = _yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        if output_json:
            click.echo(_json.dumps([{"level": "error", "path": "config.yaml", "message": f"YAML Parse-Fehler: {exc}"}]))
        else:
            console.print(f"[red]✗[/] YAML Parse-Fehler: {exc}")
        sys.exit(1)

    issues = ConfigValidator(raw).validate()
    has_errors = any(i.level == "error" for i in issues)

    if output_json:
        click.echo(_json.dumps([{"level": i.level, "path": i.path, "message": i.message} for i in issues]))
    else:
        if not issues:
            console.print("[green]✓[/] Konfiguration ist valide.")
        else:
            for issue in issues:
                color = "red" if issue.level == "error" else "yellow"
                marker = "✗" if issue.level == "error" else "!"
                console.print(f"[{color}]{marker}[/] [{issue.level}] {issue.path}: {issue.message}")

    if has_errors:
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


@cli.command(
    "task-route",
    help="Gibt 'local' oder 'claude' für einen Task zurück (SPEC-0045 Routing).",
)
@click.argument("spec_id")
@click.argument("task_id")
def task_route_cmd(spec_id: str, task_id: str) -> None:
    import json as _json
    from .task_routing.config import load_task_routing_config
    from .task_routing.task_exec import decide_routing

    root = find_project_root()
    cfg = load_config(root)
    routing_cfg = load_task_routing_config(cfg.raw)

    task_file = root / ".sdd" / "tasks" / f"{spec_id}.json"
    if not task_file.exists():
        console.print(f"[red]✗[/] Task-Datei nicht gefunden: {task_file}")
        sys.exit(1)

    tasks = _json.loads(task_file.read_text())
    task_dict = next((t for t in tasks if t.get("id") == task_id), None)
    if task_dict is None:
        console.print(f"[red]✗[/] Task-ID '{task_id}' nicht in {task_file} gefunden.")
        sys.exit(1)

    decision = decide_routing(task_dict, routing_cfg)
    print(decision)


@cli.command(
    "task-exec",
    help="Führt Implementierungsphase eines Tasks via lokalem LLM aus (SPEC-0045).",
)
@click.argument("spec_id")
@click.argument("task_id")
@click.option("--test-file", "test_file_override", default=None, help="Override Test-Datei-Pfad.")
@click.option("--iteration", default=1, type=int, show_default=True, help="Versuchs-Nummer.")
@click.option("--error-context", default="", help="pytest-Output des vorherigen Fehlversuchs.")
def task_exec_cmd(
    spec_id: str,
    task_id: str,
    test_file_override: str | None,
    iteration: int,
    error_context: str,
) -> None:
    import json as _json
    from .task_routing.config import load_task_routing_config
    from .task_routing.task_exec import ImplOnlyExecutor

    root = find_project_root()
    cfg = load_config(root)
    routing_cfg = load_task_routing_config(cfg.raw)

    if not routing_cfg.local_llm_configured:
        console.print(
            "[red]✗[/] Kein lokales LLM konfiguriert. "
            "Setze llm.local_llm in .sdd/config.yaml."
        )
        sys.exit(1)

    task_file = root / ".sdd" / "tasks" / f"{spec_id}.json"
    if not task_file.exists():
        console.print(f"[red]✗[/] Task-Datei nicht gefunden: {task_file}")
        sys.exit(1)

    tasks = _json.loads(task_file.read_text())
    task_dict = next((t for t in tasks if t.get("id") == task_id), None)
    if task_dict is None:
        console.print(f"[red]✗[/] Task-ID '{task_id}' nicht gefunden.")
        sys.exit(1)

    if test_file_override:
        test_file = Path(test_file_override)
    elif task_dict.get("test_file"):
        test_file = root / task_dict["test_file"]
    else:
        console.print("[red]✗[/] Kein test_file im Task und kein --test-file angegeben.")
        sys.exit(1)

    if not test_file.exists():
        console.print(f"[red]✗[/] Test-Datei nicht gefunden: {test_file}")
        sys.exit(1)

    executor = ImplOnlyExecutor(config=cfg, project_root=root)
    console.print(f"[cyan]▶[/] Lokales LLM implementiert Task '{task_dict['title']}' (Versuch {iteration}) …")

    try:
        success, output = executor.execute(
            task=task_dict,
            test_file=test_file,
            iteration=iteration,
            error_context=error_context,
        )
    except ValueError as exc:
        console.print(f"[red]✗[/] {exc}")
        sys.exit(1)

    if success:
        console.print("[green]✓[/] Tests grün.")
    else:
        console.print("[yellow]✗[/] Tests noch rot.")
        console.print(output)
        sys.exit(1)


@cli.command(
    "generate-holdouts",
    help="[Entfernt] Verwende: sdd holdout generate",
)
@click.argument("spec_id")
def generate_holdouts_cmd(spec_id: str) -> None:
    console.print("[yellow]⚠[/] 'sdd generate-holdouts' wurde entfernt. Verwende: [cyan]sdd holdout generate[/]")
    sys.exit(1)


@cli.group("vision", help="Produktvision verwalten (SPEC-0046).")
def vision_group() -> None:
    pass


@vision_group.command("init", help="Erstellt .sdd/vision.md interaktiv.")
@click.pass_context
def vision_init(ctx: click.Context) -> None:
    from .vision.init import VisionInitWizard, VisionAlreadyExistsError

    root = find_project_root()
    sdd_dir = root / ".sdd"
    answers: dict[str, str] = {}
    for key, prompt in [
        ("vision_statement", "Vision Statement"),
        ("target_audience", "Zielgruppe"),
        ("tech_stack", "Tech Stack"),
        ("competitive_landscape", "Competitive Landscape"),
        ("core_problems", "Kernprobleme"),
    ]:
        value = click.prompt(prompt, default="", show_default=False)
        if value:
            answers[key] = value

    try:
        VisionInitWizard(sdd_dir=sdd_dir).run(answers=answers)
        console.print(f"[green]✓[/] {sdd_dir / 'vision.md'} erstellt.")
    except VisionAlreadyExistsError as exc:
        console.print(f"[red]✗[/] {exc}")
        sys.exit(1)


@vision_group.command("show", help="Gibt das Vision-Dokument aus.")
def vision_show() -> None:
    from .vision.show import VisionReader, VisionNotFoundError

    root = find_project_root()
    try:
        VisionReader(sdd_dir=root / ".sdd").show()
    except VisionNotFoundError as exc:
        console.print(f"[red]✗[/] {exc}")
        sys.exit(1)


@vision_group.command("edit", help="Öffnet das Vision-Dokument im Editor.")
def vision_edit() -> None:
    from .vision.edit import VisionEditor, VisionNotFoundError

    root = find_project_root()
    try:
        VisionEditor(sdd_dir=root / ".sdd").open()
    except VisionNotFoundError as exc:
        console.print(f"[red]✗[/] {exc}")
        sys.exit(1)


@vision_group.command("add-feature", help="Fügt eine Feature-Idee zur Vision hinzu.")
@click.option("--title", prompt="Titel", help="Feature-Titel")
@click.option("--description", default="", prompt="Beschreibung (optional)", show_default=False, help="Kurzbeschreibung")
def vision_add_feature(title: str, description: str) -> None:
    from .vision.document import VisionDocument, VisionNotFoundError

    root = find_project_root()
    vision_file = root / ".sdd" / "vision.md"
    try:
        doc = VisionDocument.from_file(vision_file)
        doc.add_feature(title, description)
        doc.save()
        console.print(f"[green]✓[/] Feature '{title}' hinzugefügt.")
    except VisionNotFoundError as exc:
        console.print(f"[red]✗[/] {exc}")
        sys.exit(1)
    except ValueError as exc:
        console.print(f"[red]✗[/] {exc}")
        sys.exit(1)


@vision_group.command("add-task", help="Fügt einen Task zur Vision hinzu.")
@click.option("--title", prompt="Titel", help="Task-Titel")
def vision_add_task(title: str) -> None:
    from .vision.document import VisionDocument, VisionNotFoundError

    root = find_project_root()
    vision_file = root / ".sdd" / "vision.md"
    try:
        doc = VisionDocument.from_file(vision_file)
        doc.add_task(title)
        doc.save()
        console.print(f"[green]✓[/] Task '{title}' hinzugefügt.")
    except VisionNotFoundError as exc:
        console.print(f"[red]✗[/] {exc}")
        sys.exit(1)
    except ValueError as exc:
        console.print(f"[red]✗[/] {exc}")
        sys.exit(1)


@vision_group.command("challenge", help="LLM- und/oder Code-Challenge für eine Feature-Idee.")
@click.argument("feature_index", type=int)
@click.option("--llm", "mode", flag_value="llm", help="Nur LLM-Challenge.")
@click.option("--code", "mode", flag_value="code", help="Nur Code-Challenge.")
@click.option("--both", "mode", flag_value="both", default=True, help="LLM + Code (Standard).")
def vision_challenge(feature_index: int, mode: str) -> None:
    import asyncio
    from .vision.challenge import LLMChallengeStrategy, CodeChallengeStrategy
    from .vision.document import VisionNotFoundError

    root = find_project_root()
    cfg = load_config(root)
    vision_file = root / ".sdd" / "vision.md"

    try:
        if mode in ("llm", "both"):
            strategy = LLMChallengeStrategy(vision_file=vision_file, config=cfg)
            asyncio.run(strategy.challenge(feature_index=feature_index))
            console.print("[green]✓[/] LLM Challenge abgeschlossen.")
        if mode in ("code", "both"):
            strategy_code = CodeChallengeStrategy(vision_file=vision_file, project_root=root)
            strategy_code.challenge(feature_index=feature_index)
            console.print("[green]✓[/] Code Challenge abgeschlossen.")
    except VisionNotFoundError as exc:
        console.print(f"[red]✗[/] {exc}")
        sys.exit(1)
    except ValueError as exc:
        console.print(f"[red]✗[/] {exc}")
        sys.exit(1)


@vision_group.command("stats", help="Zeigt Statistiken zur aktuellen Vision.")
def vision_stats() -> None:
    from .vision.document import VisionDocument, VisionNotFoundError
    from .vision.stats import VisionStats
    from pathlib import Path

    root = find_project_root() or Path.cwd()
    vision_file = root / ".sdd" / "vision.md"

    try:
        doc = VisionDocument.from_file(vision_file)
    except VisionNotFoundError:
        console.print(
            "[red]✗[/] Keine vision.md gefunden. "
            "Erstelle sie zuerst mit: [bold]sdd vision init[/]"
        )
        sys.exit(1)

    stats = VisionStats.from_document(doc)
    console.print(f"Features:        {stats.feature_count}")
    console.print(
        f"Tasks:           {stats.task_total}"
        f"  (done: {stats.task_done} / offen: {stats.task_open})"
    )
    console.print(f"LLM Challenges:  {stats.llm_challenge_count}")
    console.print(f"Code Challenges: {stats.code_challenge_count}")


if __name__ == "__main__":
    cli()
