"""`sdd stack list|show|apply|verify|diff|extract` (SPEC-0057, CON-0228, CON-0229).

Exit-Codes: 0 Erfolg, 1 Pflichtpunkt von `verify` gescheitert oder Anwenden abgelehnt,
2 unbekannte Vorlage, ungültige Vorlage, fehlender Platzhalterwert.
"""
from __future__ import annotations

import sys
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.markup import escape

from .config import find_project_root

console = Console()
err = Console(stderr=True)

SOURCE_LABELS = {"project": "Projekt", "user": "Nutzer", "blueprint": "Blueprint"}


def _root() -> Path:
    root = find_project_root()
    if root is None:
        err.print("[red]✗[/] Kein SDD-Projekt gefunden. Führe `sdd init` aus.")
        sys.exit(2)
    return root


def _raw(root: Path) -> dict:
    try:
        return yaml.safe_load((root / ".sdd" / "config.yaml").read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def _title(root: Path, raw: dict) -> str:
    return str((raw.get("project") or {}).get("name") or root.name)


def _fail(message: str, code: int = 2) -> None:
    err.print(f"[red]✗[/] {escape(message)}")
    sys.exit(code)


@click.group("stack", help="Stack-Vorlagen: Testbarkeit und Qualitätsmessung einrichten "
                           "(SPEC-0057).")
def stack_group() -> None:
    pass


@stack_group.command("list", help="Vorlagen aus Projekt, Nutzerverzeichnis und Blueprint.")
def list_cmd() -> None:
    from . import stacks

    root = find_project_root() or Path.cwd()
    for eintrag in stacks.list_all(root):
        quelle = SOURCE_LABELS[eintrag.source]
        if eintrag.error:
            console.print(f"[red]✗[/] {eintrag.name} ({quelle}): {escape(eintrag.error)}",
                          soft_wrap=True)
            continue
        if eintrag.stack is None:
            continue
        zeile = (f"{eintrag.name} {eintrag.stack.version} ({quelle}) – "
                 f"{escape(eintrag.stack.data['description'])}")
        if eintrag.shadowed:
            zeile = f"[dim]{zeile} (verdeckt)[/]"
        console.print(zeile, soft_wrap=True)


@stack_group.command("show", help="Zeigt eine Vorlage: Werkzeuge, Platzhalter, Dateien.")
@click.argument("name")
def show_cmd(name: str) -> None:
    from . import stacks

    root = find_project_root() or Path.cwd()
    try:
        stack = stacks.find(root, name)
    except stacks.StackError as exc:
        _fail(str(exc))
    d = stack.data
    console.print(f"[bold]{stack.name}[/] {stack.version} ({SOURCE_LABELS[stack.source]}: "
                  f"{stack.dir})", soft_wrap=True)
    console.print(escape(d["description"]), soft_wrap=True)
    console.print(f"Sprachen: {', '.join(d['languages'])}")
    console.print("Werkzeuge:")
    for r in d.get("requires") or []:
        zusatz = (f" ≥ {r['min']}" if r.get("min") else "") + (" (optional)"
                                                               if r.get("optional") else "")
        console.print(f"  {r['tool']}{zusatz}", soft_wrap=True)
    console.print("Platzhalter:")
    for name_, p in stack.placeholders().items():
        default = f" = {p['default']}" if "default" in p else ""
        console.print(f"  {{{{{name_}}}}}{escape(default)}"
                      f"{' – ' + escape(p['description']) if p.get('description') else ''}",
                      soft_wrap=True)
    if d.get("verify"):
        console.print("Prüfpunkte:")
        for v in d["verify"]:
            console.print(f"  {v['name']}: {escape(v['command'])}", soft_wrap=True)
    console.print("Dateien:")
    for datei in stack.files():
        console.print(f"  {escape(datei.relative_to(stack.files_dir).as_posix())}",
                      soft_wrap=True)
    for abschnitt in stack.agents_sections():
        console.print(f"  AGENTS.md: Abschnitt {abschnitt.stem}")


def _parse_sets(sets: tuple[str, ...]) -> dict[str, str]:
    werte = {}
    for eintrag in sets:
        key, sep, value = eintrag.partition("=")
        if not sep or not key:
            _fail(f"--set erwartet NAME=WERT, bekam {eintrag!r}")
        werte[key] = value
    return werte


def run_apply(root: Path, name: str, *, sets: dict[str, str], only_quality: bool = False,
              yes: bool = False, dry_run: bool = False, interactive: bool | None = None) -> int:
    """Gemeinsamer Ablauf für `sdd stack apply` und `sdd init --stack` (Exit-Code)."""
    from . import stacks
    from .stacks.apply import plan, resolve_values, write
    from .stacks.verify import missing_tools

    interaktiv = sys.stdin.isatty() if interactive is None else interactive
    raw = _raw(root)
    try:
        stack = stacks.find(root, name)
        gespeichert = next((e.get("values") or {} for e in stacks.applied(raw)
                            if e.get("name") == name), {})
        frage = (lambda n, text: click.prompt(f"{n}{' (' + text + ')' if text else ''}")) \
            if interaktiv and not yes else None
        werte = resolve_values(stack, given=sets, stored=gespeichert, title=_title(root, raw),
                               ask=frage)
        p = plan(stack, werte, only_quality=only_quality)
    except stacks.StackError as exc:
        err.print(f"[red]✗[/] {escape(str(exc))}")
        return 2
    vorschau = stack.source != "blueprint" or dry_run
    if vorschau:
        console.print(f"Vorlage {stack.name} {stack.version} aus {SOURCE_LABELS[stack.source]}"
                      f"quelle ({stack.dir}):", soft_wrap=True)
        click.echo(p.preview(root))
    if dry_run:
        return 0
    if stack.source != "blueprint" and not yes and not (
            interaktiv and click.confirm("Anwenden?", default=False)):
        console.print("[yellow]–[/] Nicht angewendet.")
        return 1
    for fehlt in missing_tools(stack):
        console.print(f"[yellow]⚠[/] Werkzeug fehlt: {escape(fehlt)}", soft_wrap=True)
    try:
        ergebnis = write(root, p)
    except stacks.StackError as exc:
        err.print(f"[red]✗[/] {escape(str(exc))}")
        return 2
    from .quality_cli import _schreibbericht

    _schreibbericht(ergebnis)
    console.print(f"[green]✓[/] {stack.name} {stack.version} angewendet; Stand in "
                  f".sdd/config.yaml (stack:). Prüfen mit: sdd stack verify")
    return 0


@stack_group.command("apply", help="Wendet eine Vorlage an (nie überschreibend, sonst .new).")
@click.argument("name")
@click.option("--set", "sets", multiple=True, metavar="NAME=WERT", help="Platzhalterwert.")
@click.option("--only", type=click.Choice(["quality"]), default=None,
              help="Nur .sdd/quality.yaml und .sdd/quality/.")
@click.option("--yes", is_flag=True, help="Ohne Rückfrage anwenden (Projekt-/Nutzervorlagen).")
@click.option("--dry-run", is_flag=True, help="Nur Vorschau, nichts schreiben.")
def apply_cmd(name: str, sets: tuple[str, ...], only: str | None, yes: bool,
              dry_run: bool) -> None:
    sys.exit(run_apply(_root(), name, sets=_parse_sets(sets), only_quality=only == "quality",
                       yes=yes, dry_run=dry_run))


@stack_group.command("verify", help="Prüft Werkzeuge, Sonden, FR-Marker und Architekturregeln.")
def verify_cmd() -> None:
    from . import stacks
    from .stacks.verify import verify

    root = _root()
    try:
        checks = verify(root, _raw(root))
    except stacks.StackError as exc:
        _fail(str(exc))
    for c in checks:
        zeichen = "[green]✓[/]" if c.ok else ("[red]✗[/]" if c.required else "[yellow]⚠[/]")
        console.print(f"{zeichen} {escape(c.name)}: {escape(c.message)}", soft_wrap=True)
    fehler = [c for c in checks if c.failed]
    if fehler:
        console.print(f"[red]{len(fehler)} Pflichtpunkt(e) nicht erfüllt.[/]")
    sys.exit(1 if fehler else 0)


@stack_group.command("diff", help="Vergleicht Projekt, angewendeten Stand und aktuelle Vorlage.")
@click.argument("name", required=False)
def diff_cmd(name: str | None) -> None:
    from . import stacks
    from .stacks.verify import UNCHANGED, diff

    root = _root()
    raw = _raw(root)
    if not stacks.applied(raw):
        console.print("Keine Vorlage angewendet (stack: in config.yaml fehlt).")
        return
    try:
        ergebnis = diff(root, raw, name)
    except stacks.StackError as exc:
        _fail(str(exc))
    for stack_name, zeilen in ergebnis.items():
        console.print(f"[bold]{stack_name}[/]")
        geaendert = {rel: art for rel, art in zeilen.items() if art != UNCHANGED}
        if not geaendert:
            console.print("  alles unverändert")
        for art in dict.fromkeys(geaendert.values()):
            console.print(f"  {art}:")
            for rel in (r for r, a in geaendert.items() if a == art):
                console.print(f"    {escape(rel)}", soft_wrap=True)


@stack_group.command("extract", help="Legt aus dem Projekt eine eigene Vorlage an.")
@click.argument("name")
@click.option("--to", "ziel", type=click.Choice(["user", "project"]), default="user",
              show_default=True)
def extract_cmd(name: str, ziel: str) -> None:
    import re

    from . import stacks
    from .stacks.apply import extract

    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
        _fail(f"Ungültiger Vorlagenname {name!r} (erlaubt: a-z, 0-9, -).")
    root = _root()
    raw = _raw(root)
    basis = root / ".sdd" / "stacks" if ziel == "project" else stacks.user_dir()
    try:
        stack = extract(root, name, basis, title=_title(root, raw), config_raw=raw)
    except stacks.StackError as exc:
        _fail(str(exc))
    n = len(stack.files())
    console.print(f"[green]✓[/] Vorlage {name} angelegt in {stack.dir} ({n} Dateien). "
                  f"Anwenden mit: sdd stack apply {name}", soft_wrap=True)
