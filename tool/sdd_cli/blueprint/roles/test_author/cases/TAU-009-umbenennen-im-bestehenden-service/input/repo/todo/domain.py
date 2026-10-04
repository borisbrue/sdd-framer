"""Fachobjekte der Todo-Verwaltung."""
from __future__ import annotations

from dataclasses import dataclass

MAX_TITLE = 200


class ValidationError(ValueError):
    """Eingabe verletzt eine Fachregel."""


class TodoNotFoundError(LookupError):
    """Es gibt kein Todo mit dieser ID."""


@dataclass(frozen=True)
class Todo:
    """Ein Todo; unveränderlich, Änderungen erzeugen ein neues Objekt."""

    id: int
    title: str
    done: bool = False


def clean_title(title: str) -> str:
    """Titel ohne Leerraum an den Rändern; leer oder länger als MAX_TITLE ist ein Fehler."""
    sauber = title.strip()
    if not sauber:
        raise ValidationError("Titel ist leer")
    if len(sauber) > MAX_TITLE:
        raise ValidationError(f"Titel ist länger als {MAX_TITLE} Zeichen")
    return sauber
