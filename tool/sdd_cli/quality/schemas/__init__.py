"""JSON-Schemas der SPEC-0054-Contracts, als Paketdaten mit ausgeliefert.

Die Dateien sind Kopien der Contract-Artefakte unter `.sdd/contracts/data/`; ein Test
hält beide deckungsgleich.
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


def validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(load_schema(name))


def error_path(error) -> str:
    """Feldpfad eines jsonschema-Fehlers, z. B. ``probes.lint.command``.

    Fehlt ein Pflichtfeld, meldet jsonschema den Fehler am Elternobjekt; der Pfad
    wird dann um den Feldnamen ergänzt, damit er auf das fehlende Feld zeigt.
    """
    teile = [str(t) for t in error.absolute_path]
    if error.validator == "required":
        fehlend = error.message.split("'")[1] if "'" in error.message else ""
        if fehlend:
            teile.append(fehlend)
    return ".".join(teile) or "(Wurzel)"
