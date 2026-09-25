"""JSON-Schemas der SPEC-0053-Contracts, als Paketdaten mit ausgeliefert.

Die Dateien sind Kopien der Contract-Artefakte unter `.sdd/contracts/data/` (CON-0199 bis
CON-0202); ein Test hält beide deckungsgleich.
"""
from __future__ import annotations

import json
from functools import cache
from pathlib import Path

from jsonschema import Draft202012Validator

_DIR = Path(__file__).parent


@cache
def load_schema(name: str) -> dict:
    return json.loads((_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))


def validator(name: str, definition: str | None = None) -> Draft202012Validator:
    """Validator für ein Schema oder eine seiner `$defs`."""
    schema = load_schema(name)
    if definition is None:
        return Draft202012Validator(schema)
    return Draft202012Validator({"$ref": f"#/$defs/{definition}", "$defs": schema["$defs"]})


def errors(name: str, instance: object, definition: str | None = None) -> list[str]:
    """Fehlermeldungen, sortiert nach Pfad; leer, wenn die Instanz gültig ist."""
    fehler = sorted(validator(name, definition).iter_errors(instance),
                    key=lambda e: list(map(str, e.absolute_path)))
    return [f"{'.'.join(map(str, e.absolute_path)) or '(Wurzel)'}: {e.message}" for e in fehler]
