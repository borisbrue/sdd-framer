"""Seitenweise Ausgabe langer Listen (z. B. `sdd list --page 2`)."""
from __future__ import annotations

from dataclasses import dataclass

MAX_PER_PAGE = 100


@dataclass(frozen=True)
class Page:
    items: list
    page: int
    per_page: int
    total_items: int
    total_pages: int
    has_next: bool


def paginate(items: list, page: int = 1, per_page: int = 20) -> Page:
    return Page(list(items), page, per_page, len(items), 1, False)
