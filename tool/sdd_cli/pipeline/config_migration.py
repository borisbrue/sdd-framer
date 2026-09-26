"""Config-Migration `task_routing` + `llm.local_llm` → Rollen-Profile (SPEC-0062 FR-07, CON-0215).

Adapter von der alten Routing-Konfiguration auf `llm.profiles` und
`llm.roles.implementer.by_complexity`. Gearbeitet wird zeilengenau auf dem Text von
`config.yaml`, damit Kommentare und Reihenfolge erhalten bleiben: neue Einträge werden eingefügt,
die alten Blöcke mit `# [SPEC-0062] ` auskommentiert. Liegt schon ein Profil `lokal` oder eine
Zuordnung `by_complexity` vor, ändert die Migration nichts und meldet den Konflikt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .providers import COMPLEXITIES, PROFILE_KEYS

PREFIX = "# [SPEC-0062] "
PROFILE = "lokal"
# Score je Komplexität, wie ihn das alte Routing verwendete (task_exec.decide_routing).
SCORES = {"low": 15, "medium": 50, "high": 80}
DEFAULT_THRESHOLD = 30
# Alte Schlüssel von llm.local_llm, die im Profil anders heißen.
RENAMED = {"enable_thinking": "thinking"}


@dataclass
class MigrationResult:
    changed: bool = False
    messages: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)


def _indent(zeile: str) -> int:
    return len(zeile) - len(zeile.lstrip(" "))


def _code(zeile: str) -> bool:
    return bool(zeile.strip()) and not zeile.lstrip().startswith("#")


def _block_end(zeilen: list[str], start: int) -> int:
    """Ende (exklusiv) des Blocks, dessen Schlüssel in `start` steht. Eine Zeile mit gleichem
    oder kleinerem Einzug beendet ihn, auch ein Kommentar (er gehört zum nächsten Eintrag);
    Leerzeilen am Ende zählen nicht dazu."""
    tiefe = _indent(zeilen[start])
    ende = start + 1
    while ende < len(zeilen) and not (zeilen[ende].strip() and _indent(zeilen[ende]) <= tiefe):
        ende += 1
    while ende > start + 1 and not zeilen[ende - 1].strip():
        ende -= 1
    return ende


def _find(zeilen: list[str], pfad: tuple[str, ...]) -> int | None:
    """Zeile des Schlüssels `pfad` (Blockstil) oder None."""
    von, bis = 0, len(zeilen)
    treffer = None
    for schluessel in pfad:
        kinder = [i for i in range(von, bis) if _code(zeilen[i])]
        if not kinder:
            return None
        tiefe = min(_indent(zeilen[i]) for i in kinder)
        treffer = next((i for i in kinder if _indent(zeilen[i]) == tiefe
                        and zeilen[i].strip().split(":", 1)[0] == schluessel), None)
        if treffer is None:
            return None
        von, bis = treffer + 1, _block_end(zeilen, treffer)
    return treffer


def _child_indent(zeilen: list[str], kopf: int) -> int:
    for z in zeilen[kopf + 1:_block_end(zeilen, kopf)]:
        if _code(z):
            return _indent(z)
    return _indent(zeilen[kopf]) + 2


def _yaml_lines(daten: dict, einzug: int) -> list[str]:
    text = yaml.safe_dump(daten, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return [" " * einzug + z + "\n" for z in text.splitlines()]


def _insert(zeilen: list[str], pfad: tuple[str, ...], daten: dict) -> None:
    """Fügt `daten` unter `pfad` ein; fehlende Zwischenebenen werden mit angelegt."""
    for n in range(len(pfad), 0, -1):
        kopf = _find(zeilen, pfad[:n])
        if kopf is not None:
            break
    else:
        kopf, n = None, 0
    rest: dict = daten
    for schluessel in reversed(pfad[n:]):
        rest = {schluessel: rest}
    if kopf is None:
        if zeilen and not zeilen[-1].endswith("\n"):
            zeilen[-1] += "\n"
        zeilen.extend(_yaml_lines(rest, 0))
        return
    ende = _block_end(zeilen, kopf)
    zeilen[ende:ende] = _yaml_lines(rest, _child_indent(zeilen, kopf))


def _comment_out(zeilen: list[str], pfad: tuple[str, ...]) -> bool:
    kopf = _find(zeilen, pfad)
    if kopf is None:
        return False
    for i in range(kopf, _block_end(zeilen, kopf)):
        if zeilen[i].strip():
            zeilen[i] = PREFIX + zeilen[i]
    return True


def _profile(local_llm: dict, result: MigrationResult) -> dict:
    profil = {}
    for schluessel, wert in local_llm.items():
        ziel = RENAMED.get(schluessel, schluessel)
        if ziel in PROFILE_KEYS:
            profil[ziel] = wert
        else:
            result.messages.append(f"llm.local_llm.{schluessel} hat im Profil keine Entsprechung "
                                   f"und bleibt nur als Kommentar erhalten.")
    return profil


def migrate_task_routing(config_path: Path) -> MigrationResult:
    """Führt die Migration auf `config_path` aus (CON-0215 INV-03 bis INV-05)."""
    result = MigrationResult()
    if not config_path.is_file():
        return result
    text = config_path.read_text(encoding="utf-8")
    daten = yaml.safe_load(text) or {}
    llm = daten.get("llm") or {}
    routing = daten.get("task_routing")
    local_llm = llm.get("local_llm")
    if routing is None and local_llm is None:
        return result

    zeilen = text.splitlines(keepends=True)
    if isinstance(local_llm, dict) and local_llm:
        vorhanden = [p for p, da in (
            (f"llm.profiles.{PROFILE}", PROFILE in (llm.get("profiles") or {})),
            ("llm.roles.implementer.by_complexity",
             "by_complexity" in ((llm.get("roles") or {}).get("implementer") or {})),
        ) if da]
        if vorhanden:
            result.conflicts.extend(f"{p} existiert bereits; task_routing und llm.local_llm "
                                    f"bitte von Hand übernehmen." for p in vorhanden)
            return result
        _insert(zeilen, ("llm", "profiles"), {PROFILE: _profile(local_llm, result)})
        result.messages.append(f"llm.local_llm → llm.profiles.{PROFILE}")
        routing_an = isinstance(routing, dict) and bool(routing.get("enabled"))
        if routing_an:
            schwelle = routing.get("complexity_threshold", DEFAULT_THRESHOLD)
            stufen = {s: PROFILE for s in COMPLEXITIES if SCORES[s] <= schwelle}
            if stufen:
                _insert(zeilen, ("llm", "roles", "implementer"), {"by_complexity": stufen})
                result.messages.append(
                    f"task_routing (Schwelle {schwelle}) → llm.roles.implementer.by_complexity: "
                    + ", ".join(f"{s}={p}" for s, p in stufen.items()))
        _comment_out(zeilen, ("llm", "local_llm"))
        result.messages.append("llm.local_llm auskommentiert")
    elif routing is not None:
        result.messages.append("task_routing ohne llm.local_llm: kein Profil übernommen.")
    if routing is not None and _comment_out(zeilen, ("task_routing",)):
        result.messages.append("task_routing auskommentiert")
    config_path.write_text("".join(zeilen), encoding="utf-8")
    result.changed = True
    return result
