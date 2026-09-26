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
    if not 1 <= per_page <= MAX_PER_PAGE:
        raise ValueError(f"per_page muss zwischen 1 und {MAX_PER_PAGE} liegen")
    if page < 1:
        raise ValueError("page beginnt bei 1")
    total = len(items)
    seiten = max(1, -(-total // per_page))
    start = (page - 1) * per_page
    ausschnitt = list(items[start:start + per_page])
    return Page(ausschnitt, page, per_page, total, seiten, page < seiten)
