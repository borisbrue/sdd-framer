"""Extraktion der deklarierten FR-IDs aus einem Spec-Body."""
from __future__ import annotations

import re

_FR_HEADING_RE = re.compile(
    r"^(#{2,3})\s+(?:\d+\.\s+)?Funktionale Anforderungen\b.*$",
    re.IGNORECASE | re.MULTILINE,
)

_FR_ID_RE = re.compile(
    r"^[ \t]*(?:[-*+][ \t]*)?(?:\[[ xX]\][ \t]*)?(?:\*\*)?(FR-\d+)\b", re.MULTILINE
)


def _fr_section(body: str) -> str:
    """Inhalt des FR-Abschnitts, oder "" wenn es keinen gibt."""
    heading = _FR_HEADING_RE.search(body)
    if heading is None:
        return ""
    level = len(heading.group(1))
    rest = body[heading.end():]
    ende = re.search(rf"^#{{1,{level}}}\s", rest, re.MULTILINE)
    return rest[: ende.start()] if ende else rest


def extract_fr_ids(body: str) -> list[str]:
    """Deklarierte FR-IDs aus dem Abschnitt 'Funktionale Anforderungen'."""
    abschnitt = _fr_section(body)
    if not abschnitt:
        return []
    ids = _FR_ID_RE.findall(abschnitt)
    return list(dict.fromkeys(ids))
