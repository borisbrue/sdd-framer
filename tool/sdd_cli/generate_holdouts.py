"""sdd generate-holdouts – automatische Holdout-Generierung per CLI (SPEC-0033)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import SddConfig
from .frontmatter import parse_safe
from .templates import slugify

_VALID_STATUSES = {"approved", "in-progress"}


def load_and_validate_spec(spec_id: str, cfg: SddConfig) -> dict[str, Any]:
    """Lädt die Spec-Datei und validiert Status und Contracts.

    Raises:
        FileNotFoundError: Spec-Datei nicht gefunden.
        ValueError: Status ist draft oder Contracts-Liste ist leer.
    """
    fm: dict[str, Any] = {}
    spec_file: Path | None = None
    for md in cfg.specs_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == spec_id:
            spec_file = md
            fm = doc.frontmatter
            break

    if spec_file is None:
        raise FileNotFoundError(f"Spec {spec_id} nicht gefunden.")

    status = fm.get("status", "")
    if status not in _VALID_STATUSES:
        raise ValueError(
            f"Spec muss approved oder in-progress sein, ist aber '{status}'."
        )

    contracts = fm.get("contracts") or []
    if not contracts:
        raise ValueError(
            "Keine Contracts gefunden. Erstelle zuerst Contracts mit `sdd new contract`."
        )

    return {**fm, "_path": spec_file}


def resolve_contract_files(contract_ids: list[str], cfg: SddConfig) -> list[dict[str, Any]]:
    """Sucht Contract-Dateien auf Disk für die gegebenen IDs.

    Fehlende Contracts werden übersprungen (Warning wird vom Aufrufer ausgegeben).

    Returns:
        Liste von Dicts mit keys: id, path, content (Rohtext), frontmatter.
    """
    result: list[dict[str, Any]] = []
    for cid in contract_ids:
        found = None
        for md in cfg.contracts_dir.rglob("*.md"):
            doc = parse_safe(md)
            if doc and doc.frontmatter.get("id") == cid:
                found = {
                    "id": cid,
                    "path": md,
                    "content": md.read_text(encoding="utf-8"),
                    "frontmatter": doc.frontmatter,
                }
                break
        if found:
            result.append(found)
    return result


def get_existing_hol_ids_for_spec(spec_id: str, cfg: SddConfig) -> set[str]:
    """Scannt .sdd/holdout/ und gibt alle HOL-IDs zurück, die zu spec_id gehören."""
    holdout_dir = cfg.holdout_dir
    if not holdout_dir.exists():
        return set()

    existing: set[str] = set()
    for md in holdout_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("spec") == spec_id:
            hol_id = doc.frontmatter.get("id")
            if hol_id:
                existing.add(hol_id)
    return existing


def write_hol_file(
    hol_id: str,
    spec_id: str,
    contract_id: str,
    scenario: dict[str, Any],
    cfg: SddConfig,
) -> Path:
    """Schreibt eine HOL-Datei mit allen Pflichtfeldern.

    scenario: dict mit keys 'title', 'priority', 'type', 'description',
              optional 'setup' (list), 'test' (dict), optional 'teardown' (list),
              'evaluation_hint'.
    """
    import yaml as _yaml
    from datetime import date

    holdout_dir = cfg.holdout_dir
    holdout_dir.mkdir(parents=True, exist_ok=True)

    title = scenario["title"]
    priority = scenario.get("priority", "normal")
    hol_type = scenario.get("type", "http")
    slug = slugify(title)
    target = holdout_dir / f"{hol_id}-{slug}.md"
    today = date.today().isoformat()

    frontmatter = (
        f"---\n"
        f"id: {hol_id}\n"
        f"title: \"{title}\"\n"
        f"spec: {spec_id}\n"
        f"contract: {contract_id}\n"
        f"status: wip\n"
        f"priority: {priority}\n"
        f"type: {hol_type}\n"
        f"created: {today}\n"
        f"updated: {today}\n"
        f"tags: []\n"
        f"---\n"
    )

    header = (
        f"\n# Holdout: {title}\n\n"
        f"> **Contract:** {contract_id} · **Spec:** {spec_id} · **Priority:** {priority}\n"
        f">\n"
        f"> ⚠️ Dieses Dokument ist dem Code-generierenden Agenten **nicht** zugänglich.\n"
    )

    description = scenario.get("description", "")
    body = f"\n## Beschreibung\n\n{description}\n" if description else ""

    setup = scenario.get("setup")
    if setup:
        setup_yaml = _yaml.dump(setup, allow_unicode=True, default_flow_style=False)
        body += f"\n## Setup\n\n```yaml\n{setup_yaml}```\n"

    test = scenario.get("test")
    if test:
        test_yaml = _yaml.dump({"test": test}, allow_unicode=True, default_flow_style=False)
        body += f"\n## Test\n\n```yaml\n{test_yaml}```\n"

    teardown = scenario.get("teardown")
    if teardown:
        td_yaml = _yaml.dump(teardown, allow_unicode=True, default_flow_style=False)
        body += f"\n## Teardown\n\n```yaml\n{td_yaml}```\n"

    hint = scenario.get("evaluation_hint", "")
    body += f"\n## Evaluation Hint\n\n{hint}\n"

    target.write_text(frontmatter + header + body, encoding="utf-8")
    return target


_SCENARIO_SCHEMA = """\
Jedes Element ist ein JSON-Objekt mit diesen Feldern:
  "title"           – kurzer Szenario-Titel (string)
  "priority"        – "critical" | "normal" | "edge-case"
                      critical = bricht sofort ab; normal = aggregiert; edge-case = nur wenn normal besteht
  "type"            – "http" | "cli"
  "description"     – 1-2 Sätze Plain English, was das System tun soll (string)
  "setup"           – optionale Liste von Setup-Schritten (Array oder null).
                      Jeder Schritt: { "step": "<name>", "action": <action>, "capture": { "<var>": "<json.path>" } }
                      HTTP-Action: { "method": "POST|GET|...", "path": "/api/...", "body": {...} }
                      Builtin-Action: { "builtin": "advance_time|write_file|delete_file", "seconds": N, "path": "...", "content": "..." }
  "test"            – der eigentliche Testaufruf (object, Pflicht):
                      { "action": <action>, "assert": <assert> }
                      HTTP-Assert: { "status": 200, "body": { "<json.path>": <value> } }
                        Assertion-Wert: Skalar (exakter Match), "{captured.var}", { "present": true }, { "contains": "..." }
                      CLI-Assert: { "exit_code": 0, "stdout_contains": ["..."], "stderr_empty": true }
  "teardown"        – optionale Liste von Teardown-Schritten, gleiche Struktur wie setup (Array oder null)
  "evaluation_hint" – strukturierter Hinweis für den KI-Evaluator:
                      "Wenn <assertion> != <erwartet>: <Ursache>. Prüfe <module.py:funktion()>. Fix-Richtung: <was ändern>."
"""


def generate_holdout_scenarios(
    contract_content: str,
    contract_id: str,
    spec_content: str,
    provider: Any,
    num_scenarios: int = 3,
) -> list[dict[str, Any]]:
    """Ruft das LLM auf und leitet Holdout-Szenarien aus Spec + Contract ab.

    Returns:
        Liste von Dicts mit keys: title, priority, type, description,
        setup (optional), test, teardown (optional), evaluation_hint.
    Raises:
        RuntimeError: bei LLM-Fehler nach 1 Retry.
    """
    prompt = (
        f"Du bist ein SDD-Evaluator. Generiere {num_scenarios} ausführbare Holdout-Szenarien "
        f"für den folgenden Contract (ID: {contract_id}).\n\n"
        f"CONTRACT:\n{contract_content}\n\nSPEC-KONTEXT:\n{spec_content}\n\n"
        f"Antworte mit einem JSON-Array. {_SCENARIO_SCHEMA}\n"
        "Regeln:\n"
        "  - Mindestens 1 Szenario muss ein Fehlerfall sein (priority: normal oder edge-case).\n"
        "  - Der Happy Path ist immer priority: critical.\n"
        "  - Alle Pfade und Felder müssen aus dem Contract ableitbar sein – keine Erfindungen.\n"
        "  - Nur JSON, kein Markdown, keine Erklärungen außerhalb des Arrays."
    )

    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            import json
            result = provider.complete(prompt, max_tokens=4096, timeout=90)
            scenarios = json.loads(result.text.strip())
            if not isinstance(scenarios, list):
                raise ValueError("LLM hat kein JSON-Array zurückgegeben.")
            return [
                {
                    "title": s.get("title", f"Szenario {i+1}"),
                    "priority": s.get("priority", "normal"),
                    "type": s.get("type", "http"),
                    "description": s.get("description", ""),
                    "setup": s.get("setup") or None,
                    "test": s.get("test", {}),
                    "teardown": s.get("teardown") or None,
                    "evaluation_hint": s.get("evaluation_hint", ""),
                }
                for i, s in enumerate(scenarios)
            ]
        except Exception as exc:
            last_exc = exc
            if attempt == 0:
                continue

    raise RuntimeError(
        f"LLM-Aufruf für {contract_id} fehlgeschlagen: {last_exc}"
    )
