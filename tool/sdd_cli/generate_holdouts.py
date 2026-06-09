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
    scenario: dict[str, str],
    cfg: SddConfig,
) -> Path:
    """Schreibt eine HOL-Datei mit allen Pflichtfeldern.

    scenario: dict mit keys 'title', 'input', 'expected', 'evaluation_hint'.
    """
    holdout_dir = cfg.holdout_dir
    holdout_dir.mkdir(parents=True, exist_ok=True)

    title = scenario["title"]
    slug = slugify(title)
    target = holdout_dir / f"{hol_id}-{slug}.md"

    body = (
        f"\n## Input\n\n{scenario['input']}\n\n"
        f"## Expected\n\n{scenario['expected']}\n\n"
        f"## Evaluation Hint\n\n{scenario['evaluation_hint']}\n"
    )

    from datetime import date
    today = date.today().isoformat()
    content = (
        f"---\nid: {hol_id}\nproject: \"\"\ntitle: \"{title}\"\n"
        f"contract: {contract_id}\nspec: {spec_id}\nstatus: ready\n"
        f"created: {today}\nupdated: {today}\ntags: []\n---\n"
        f"{body}"
    )
    target.write_text(content, encoding="utf-8")
    return target


def generate_holdout_scenarios(
    contract_content: str,
    contract_id: str,
    spec_content: str,
    provider: Any,
    num_scenarios: int = 3,
) -> list[dict[str, str]]:
    """Ruft das LLM auf und leitet Holdout-Szenarien aus Spec + Contract ab.

    Returns:
        Liste von Dicts mit keys: title, input, expected, evaluation_hint.
    Raises:
        RuntimeError: bei LLM-Fehler nach 1 Retry.
    """
    prompt = (
        f"Du bist ein SDD-Evaluator. Generiere {num_scenarios} Holdout-Szenarien "
        f"für den folgenden Contract (ID: {contract_id}).\n\n"
        f"CONTRACT:\n{contract_content}\n\nSPEC-KONTEXT:\n{spec_content}\n\n"
        "Antworte mit einem JSON-Array. Jedes Element hat folgende Felder:\n"
        '  "title": kurzer Szenario-Titel\n'
        '  "input": Was eingegeben / ausgelöst wird (konkret)\n'
        '  "expected": Was das System zurückgeben / tun muss (prüfbar)\n'
        '  "evaluation_hint": Aufzählung der Prüfpunkte für den Evaluator\n\n'
        "Mindestens 1 Szenario muss ein Fehlerfall sein. Nur JSON, kein Markdown."
    )

    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            result = provider.complete(prompt, max_tokens=2048, timeout=60)
            import json
            scenarios = json.loads(result.text.strip())
            if not isinstance(scenarios, list):
                raise ValueError("LLM hat kein JSON-Array zurückgegeben.")
            return [
                {
                    "title": s.get("title", f"Szenario {i+1}"),
                    "input": s.get("input", ""),
                    "expected": s.get("expected", ""),
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
