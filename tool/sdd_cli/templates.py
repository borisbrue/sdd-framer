"""Rendert Templates aus .sdd/templates/ in neue Dokumente."""
from __future__ import annotations

from datetime import date
from pathlib import Path
import re
import shutil

from .config import SddConfig


# Welches Template ist Standard für welche Art?
TEMPLATE_MAP = {
    "spec":           ("spec",           "default.md"),
    "spec-bug-fix":   ("spec",           "bug-fix.md"),
    "test":           ("test",           "default.md"),
    "adr":            ("adr",            "default.md"),
    "holdout":        ("holdout",        "default.md"),
    "agents-md":      ("agents-md",      "default.md"),
    "github-actions": ("github-actions", "sdd-orchestrate.yml"),
    # Contracts haben mehrere Formate – Auswahl per Flag
}

CONTRACT_TEMPLATES = {
    "openapi":     ("contract", "api-openapi.md",          "api-openapi.skeleton.yaml"),
    "asyncapi":    ("contract", "api-openapi.md",          None),  # Placeholder
    "graphql":     ("contract", "api-openapi.md",          None),
    "grpc":        ("contract", "api-openapi.md",          None),
    "json-schema": ("contract", "data-jsonschema.md",      None),
    "avro":        ("contract", "data-jsonschema.md",      None),
    "protobuf":    ("contract", "data-jsonschema.md",      None),
    "gherkin":     ("contract", "behavior-gherkin.md",     "behavior-gherkin.skeleton.feature"),
    "markdown":    ("contract", "behavior-gherkin.md",     None),
    "slo-yaml":    ("contract", "performance-slo.md",      None),
}


def slugify(text: str) -> str:
    """Konvertiert einen Titel in einen Dateinamen-sicheren Slug."""
    s = text.lower().strip()
    s = re.sub(r"[äÄ]", "ae", s)
    s = re.sub(r"[öÖ]", "oe", s)
    s = re.sub(r"[üÜ]", "ue", s)
    s = re.sub(r"[ß]", "ss", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def render(template_text: str, context: dict[str, str]) -> str:
    """Sehr simpler Renderer: ersetzt Platzhalter in Frontmatter und Body.

    Wir setzen NICHT auf Jinja, um die CLI ohne weitere Abhängigkeiten
    leichtgewichtig zu halten. Ersetzt werden:
      - YAML-Zeilen `id: SPEC-XXXX` → tatsächliche ID
      - YAML-Zeilen `title: "<...>"` → tatsächlicher Titel
      - YAML-Zeilen `created: YYYY-MM-DD` / `updated: ...` → heute
      - {{title}}, {{status}}, {{owner}}, {{version}}, {{spec}}, {{contract}}, {{artifact}}, {{id}}
        im Markdown-Body
    """
    out = template_text

    # Frontmatter-Felder austauschen, falls vorhanden
    replacements = {
        "id":      context.get("id"),
        "title":   context.get("title"),
        "spec":    context.get("spec"),
        "contract":context.get("contract"),
        "owner":   context.get("owner"),
        "artifact":context.get("artifact"),
        "project": context.get("project"),
    }

    if replacements["id"]:
        out = re.sub(r"^id:\s*[A-Z]+-X+(\s*#.*)?$",
                     f'id: {replacements["id"]}',
                     out, count=1, flags=re.MULTILINE)
    if replacements["project"]:
        out = re.sub(r'^project:\s*""(\s*#.*)?$',
                     f'project: {replacements["project"]}',
                     out, count=1, flags=re.MULTILINE)
    if replacements["title"]:
        out = re.sub(
            r'^title:\s*".*"(\s*#.*)?$',
            f'title: "{replacements["title"]}"',
            out, count=1, flags=re.MULTILINE,
        )
    if replacements["spec"]:
        out = re.sub(r"^spec:\s*SPEC-X+(\s*#.*)?$",
                     f'spec: {replacements["spec"]}',
                     out, count=1, flags=re.MULTILINE)
    if replacements["contract"]:
        out = re.sub(r"^contract:\s*CON-X+(\s*#.*)?$",
                     f'contract: {replacements["contract"]}',
                     out, count=1, flags=re.MULTILINE)
    if replacements["owner"]:
        out = re.sub(r'^owner:\s*".*"(\s*#.*)?$',
                     f'owner: "{replacements["owner"]}"',
                     out, count=1, flags=re.MULTILINE)
    if replacements["artifact"]:
        out = re.sub(r'^artifact:\s*"[^"]*"(\s*#.*)?$',
                     f'artifact: "{replacements["artifact"]}"',
                     out, count=1, flags=re.MULTILINE)

    # Datum
    today = date.today().isoformat()
    out = re.sub(r"^(created|updated|date):\s*YYYY-MM-DD\s*$",
                 lambda m: f"{m.group(1)}: {today}",
                 out, flags=re.MULTILINE)

    # Body-Platzhalter
    for key, val in replacements.items():
        if val:
            out = out.replace("{{" + key + "}}", val)
    out = out.replace("{{status}}", context.get("status", "draft"))
    out = out.replace("{{version}}", context.get("version", "0.1.0"))

    return out


def copy_skeleton(config: SddConfig, skeleton_name: str, target: Path) -> None:
    """Kopiert eine Skeleton-Datei (OpenAPI-Yaml etc.) an ihren Zielort."""
    src = config.templates_dir / "contract" / skeleton_name
    if src.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, target)


def load_template(config: SddConfig, kind: str, contract_format: str | None = None) -> tuple[str, str | None]:
    """Liefert (template_text, optional_skeleton_filename)."""
    if kind == "contract":
        if not contract_format or contract_format not in CONTRACT_TEMPLATES:
            raise ValueError(
                f"Bitte Contract-Format angeben (--format). "
                f"Erlaubt: {', '.join(CONTRACT_TEMPLATES.keys())}"
            )
        subdir, name, skeleton = CONTRACT_TEMPLATES[contract_format]
        template_path = config.templates_dir / subdir / name
        return template_path.read_text(encoding="utf-8"), skeleton

    subdir, name = TEMPLATE_MAP[kind]
    template_path = config.templates_dir / subdir / name
    return template_path.read_text(encoding="utf-8"), None
