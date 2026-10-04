"""Öffentliche Schnittstellen einer Datei ohne Rümpfe (SPEC-0065 FR-02, FR-03).

Registry je Dateiendung (Strategy): Jedes Modul im Paket `extractors` meldet sich mit
`register(endung, funktion)` an; die Funktion bekommt den Dateitext und liefert Zeilen. Was als
öffentlich gilt, entscheidet der Extraktor der Sprache. Dateien ohne Extraktor erscheinen nur mit
ihrem Pfad.
"""
from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable
from pathlib import PurePosixPath

Extractor = Callable[[str], list[str]]

EXTRACTORS: dict[str, Extractor] = {}

KEIN_EXTRAKTOR = "(kein Extraktor für diesen Dateityp – nur der Pfad)"
NICHT_LESBAR = "(Datei nicht lesbar – Schnittstellen nicht ermittelt)"


class ExtractionError(ValueError):
    """Ein Extraktor kann den Dateitext nicht lesen (etwa Syntaxfehler)."""


def register(suffix: str, extractor: Extractor) -> None:
    EXTRACTORS[suffix.lower()] = extractor


def api_of(rel: str, text: str) -> str:
    """Schnittstellen von `rel` als Text; ohne Extraktor oder bei Lesefehler nur ein Hinweis."""
    extractor = EXTRACTORS.get(PurePosixPath(rel).suffix.lower())
    if extractor is None:
        return KEIN_EXTRAKTOR
    try:
        zeilen = extractor(text)
    except ExtractionError:
        return NICHT_LESBAR
    return "\n".join(zeilen) if zeilen else "(keine öffentlichen Definitionen)"


def _load_extractors() -> None:
    from . import extractors

    for modul in pkgutil.iter_modules(extractors.__path__):
        importlib.import_module(f"{extractors.__name__}.{modul.name}")


_load_extractors()
