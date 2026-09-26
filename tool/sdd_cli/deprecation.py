"""Specs und Contracts ablösen (SPEC-0058 FR-09, CON-0210 INV-03/INV-05).

`sdd spec deprecate` und `sdd contract deprecate` sind der einzige Weg, ein Artefakt auf
`deprecated` zu setzen. Geschrieben werden nur die betroffenen Frontmatter-Zeilen; der Rest der
Datei bleibt byte-gleich (wie `frontmatter.patch_status`).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .config import SddConfig
from .frontmatter import FRONTMATTER_RE, parse_safe, patch_status
from .lifecycle import write_audit_log


class DeprecationError(Exception):
    """Artefakt unbekannt oder Angaben ungültig."""


@dataclass
class DeprecationResult:
    artifact_id: str
    path: Path
    old_status: str
    contracts: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)
    dependents: list[str] = field(default_factory=list)


def set_frontmatter_fields(path: Path, fields: dict[str, str]) -> None:
    """Setzt einfache Frontmatter-Felder zeilengenau; fehlende werden angehängt."""
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise DeprecationError(f"{path.name}: kein Frontmatter")
    fm = match.group("yaml")
    for key, value in fields.items():
        zeile = f"{key}: {json.dumps(value, ensure_ascii=False)}"
        fm, treffer = re.subn(rf"(?m)^{re.escape(key)}:.*$", lambda _m, z=zeile: z, fm, count=1)
        if not treffer:
            fm = f"{fm.rstrip()}\n{zeile}"
    start, ende = match.span("yaml")
    path.write_text(text[:start] + fm + text[ende:], encoding="utf-8")


def _finde(verzeichnis: Path, artifact_id: str) -> tuple[Path, dict]:
    for md in sorted(verzeichnis.rglob(f"{artifact_id}-*.md")):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == artifact_id:
            return md, doc.frontmatter
    raise DeprecationError(f"{artifact_id} nicht gefunden")


def _abloesen(config: SddConfig, pfad: Path, fm: dict, reason: str,
              replaced_by: str | None = None) -> str:
    alt = str(fm.get("status") or "")
    patch_status(pfad, "deprecated")
    felder = {"deprecated_reason": reason}
    if replaced_by:
        felder["replaced_by"] = replaced_by
    set_frontmatter_fields(pfad, felder)
    grund = reason + (f"; Nachfolger {replaced_by}" if replaced_by else "")
    write_audit_log(config, str(fm["id"]), alt, "deprecated", grund)
    return alt


def deprecate_contract(config: SddConfig, con_id: str, reason: str) -> DeprecationResult:
    if not reason.strip():
        raise DeprecationError("--reason darf nicht leer sein")
    pfad, fm = _finde(config.root / ".sdd" / "contracts", con_id)
    alt = _abloesen(config, pfad, fm, reason)
    return DeprecationResult(con_id, pfad, alt)


def deprecate_spec(config: SddConfig, spec_id: str, reason: str,
                   replaced_by: str | None = None, keep: tuple[str, ...] = ()) -> DeprecationResult:
    """Löst eine Spec und ihre Contracts ab (außer `keep`); meldet abhängige Specs."""
    if not reason.strip():
        raise DeprecationError("--reason darf nicht leer sein")
    specs = config.root / ".sdd" / "specs"
    pfad, fm = _finde(specs, spec_id)
    if replaced_by:
        _finde(specs, replaced_by)
    alt = _abloesen(config, pfad, fm, reason, replaced_by)
    ergebnis = DeprecationResult(spec_id, pfad, alt)

    for md in sorted((config.root / ".sdd" / "contracts").rglob("CON-*.md")):
        doc = parse_safe(md)
        if not doc or doc.frontmatter.get("spec") != spec_id:
            continue
        cid = str(doc.frontmatter.get("id"))
        if cid in keep:
            ergebnis.kept.append(cid)
        elif doc.frontmatter.get("status") != "deprecated":
            _abloesen(config, md, doc.frontmatter, f"mit {spec_id} abgelöst: {reason}")
            ergebnis.contracts.append(cid)

    for md in sorted(specs.rglob("SPEC-*.md")):
        doc = parse_safe(md)
        if (doc and doc.frontmatter.get("status") != "deprecated"
                and spec_id in (doc.frontmatter.get("depends_on") or [])):
            ergebnis.dependents.append(str(doc.frontmatter.get("id")))
    return ergebnis
