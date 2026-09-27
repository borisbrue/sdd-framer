"""Aufgabe und ihre Regeln (SPEC-0001, SPEC-0003)."""
from __future__ import annotations

import datetime as dt
import re
from collections.abc import Iterable
from dataclasses import dataclass

from .errors import ValidationError

MAX_TITLE_LENGTH = 200
TAG_RE = re.compile(r"[a-z0-9-]{1,20}")


@dataclass(frozen=True)
class Todo:
    """Unveränderliche Momentaufnahme einer Aufgabe."""

    id: int
    title: str
    done: bool = False
    tags: tuple[str, ...] = ()
    due: dt.date | None = None


def normalize_title(title: object) -> str:
    if not isinstance(title, str):
        raise ValidationError("Der Titel muss ein Text sein.")
    bereinigt = title.strip()
    if not bereinigt:
        raise ValidationError("Der Titel darf nicht leer sein.")
    if len(bereinigt) > MAX_TITLE_LENGTH:
        raise ValidationError(f"Der Titel darf höchstens {MAX_TITLE_LENGTH} Zeichen haben.")
    return bereinigt


def normalize_tag(tag: object) -> str:
    if not isinstance(tag, str):
        raise ValidationError("Ein Tag muss ein Text sein.")
    wert = tag.strip().lower()
    if not TAG_RE.fullmatch(wert):
        raise ValidationError(
            f"Ungültiger Tag {tag!r}: erlaubt sind 1 bis 20 Zeichen aus a–z, 0–9 und '-'.")
    return wert


def normalize_tags(tags: Iterable[object]) -> tuple[str, ...]:
    if isinstance(tags, str):
        tags = [tags]
    return tuple(sorted({normalize_tag(t) for t in tags}))


def validate_due(due: object) -> dt.date | None:
    if due is None:
        return None
    if isinstance(due, dt.datetime) or not isinstance(due, dt.date):
        raise ValidationError("Die Fälligkeit muss ein Datum (datetime.date) oder None sein.")
    return due
