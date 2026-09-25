"""Verknüpfung architecture.yaml ↔ ADRs für `sdd validate` (SPEC-0054 FR-06, CON-0197 INV-07/08)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .evaluator import adr_titles
from .rules import ARCH_FILE, ArchConfigError, load_raw, parse_architecture

INACTIVE_ADR = ("superseded", "deprecated")
_INVARIANT_RE = re.compile(r"^[ \t]*[-*][ \t]+\*\*(?P<name>[^*]+?)\*\*", re.MULTILINE)
_TASTE_RE = re.compile(r"^##\s+Taste Invariants\s*$(?P<body>.*?)(?=^##\s|\Z)",
                       re.MULTILINE | re.DOTALL)


@dataclass(frozen=True)
class LinkFinding:
    level: str
    path: str
    message: str


def _invarianten_ohne_regel(root: Path) -> list[LinkFinding]:
    agents = root / "AGENTS.md"
    if not agents.is_file():
        return []
    m = _TASTE_RE.search(agents.read_text(encoding="utf-8"))
    if not m:
        return []
    funde = []
    for zeile in m.group("body").splitlines():
        treffer = _INVARIANT_RE.match(zeile)
        if treffer and not re.search(r"\[ARCH-\d{2,}\]", zeile):
            name = treffer.group("name").strip().rstrip(":")
            funde.append(LinkFinding("info", "AGENTS.md",
                                     f"Taste Invariant '{name}' ohne maschinelle Regel [ARCH-NN]"))
    return funde


def check_adr_links(root: Path, adr_dir: str) -> list[LinkFinding]:
    """Ohne `.sdd/architecture.yaml` keine Befunde (Verhalten wie vor SPEC-0054)."""
    try:
        raw = load_raw(root)
        arch = parse_architecture(raw)
    except FileNotFoundError:
        return []
    except ArchConfigError as exc:
        return [LinkFinding("error", f"{ARCH_FILE}:{p}", m) for p, m in exc.problems]

    adrs = adr_titles(root, adr_dir)
    funde: list[LinkFinding] = []
    gesehen: set[str] = set()
    for rule in arch.rules:
        pfad = f"{ARCH_FILE}:{rule.id}"
        if rule.id in gesehen:
            funde.append(LinkFinding("error", pfad, f"doppelte Regel-ID {rule.id}"))
        gesehen.add(rule.id)
        adr = adrs.get(rule.adr)
        if adr is None:
            funde.append(LinkFinding("error", pfad,
                                     f"{rule.id} verweist auf {rule.adr}, das nicht existiert"))
        elif str(adr.get("status", "")).lower() in INACTIVE_ADR:
            funde.append(LinkFinding("warning", pfad,
                                     f"{rule.id} hängt an {rule.adr} mit Status {adr['status']}"))
        unbekannt = rule.unknown_layers(list(arch.layers))
        if unbekannt:
            funde.append(LinkFinding("error", pfad,
                                     f"{rule.id}: unbekannte Schicht {', '.join(unbekannt)}"))
    for adr_id, fm in adrs.items():
        if str(fm.get("status", "")).lower() != "accepted":
            continue
        for rid in fm.get("enforced_by") or []:
            if rid not in gesehen:
                funde.append(LinkFinding("warning", f"{adr_dir}/{adr_id}",
                                         f"{adr_id} nennt enforced_by {rid}, "
                                         f"das in {ARCH_FILE} fehlt"))
    return funde + _invarianten_ohne_regel(root)
