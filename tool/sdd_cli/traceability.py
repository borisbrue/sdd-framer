"""Erzeugt die Traceability-Matrix Spec ↔ Contract ↔ Test."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from .config import SddConfig
from .frontmatter import parse_safe


def _collect(base: Path) -> list:
    if not base.exists():
        return []
    out = []
    for md in base.rglob("*.md"):
        if "_archive" in md.parts:
            continue
        d = parse_safe(md)
        if d and d.frontmatter.get("id"):
            out.append(d)
    return out


def build_matrix(config: SddConfig) -> str:
    specs = sorted(_collect(config.specs_dir), key=lambda d: d.frontmatter["id"])
    contracts = {d.frontmatter["id"]: d for d in _collect(config.contracts_dir)}
    tests = {d.frontmatter["id"]: d for d in _collect(config.tests_dir)}

    lines: list[str] = []
    lines.append("# Traceability-Matrix\n")
    lines.append("> Automatisch generiert durch `sdd trace`. Manuelle Änderungen werden überschrieben.")
    lines.append(f"> Letzte Aktualisierung: {date.today().isoformat()}\n")

    lines.append("## Spec → Contract → Test\n")
    lines.append("| Spec | Spec-Titel | Status | Contract | Contract-Typ | Test | Test-Level | Test-Status |")
    lines.append("|------|------------|--------|----------|--------------|------|------------|-------------|")

    for spec in specs:
        sid = spec.frontmatter["id"]
        stitle = spec.frontmatter.get("title", "")
        sstatus = spec.frontmatter.get("status", "")
        spec_contracts = spec.frontmatter.get("contracts") or []

        if not spec_contracts:
            lines.append(f"| {sid} | {stitle} | {sstatus} | — | — | — | — | — |")
            continue

        for cid in spec_contracts:
            c = contracts.get(cid)
            ctype = c.frontmatter.get("type", "?") if c else "FEHLT"
            c_tests = (c.frontmatter.get("tests") if c else None) or []
            if not c_tests:
                lines.append(f"| {sid} | {stitle} | {sstatus} | {cid} | {ctype} | — | — | — |")
                continue
            for tid in c_tests:
                t = tests.get(tid)
                tlevel = t.frontmatter.get("level", "?") if t else "FEHLT"
                tstatus = t.frontmatter.get("status", "?") if t else "?"
                lines.append(
                    f"| {sid} | {stitle} | {sstatus} | {cid} | {ctype} | {tid} | {tlevel} | {tstatus} |"
                )

    lines.append("\n## Coverage-Übersicht\n")
    lines.append("| Spec | # Contracts | # Tests | Lücken |")
    lines.append("|------|-------------|---------|--------|")
    for spec in specs:
        sid = spec.frontmatter["id"]
        cs = spec.frontmatter.get("contracts") or []
        ts = spec.frontmatter.get("tests") or []
        gaps = []
        if not cs:
            gaps.append("kein Contract")
        if not ts:
            gaps.append("kein Test")
        lines.append(f"| {sid} | {len(cs)} | {len(ts)} | {', '.join(gaps) or '—'} |")

    return "\n".join(lines) + "\n"


def write_matrix(config: SddConfig) -> Path:
    output_path = config.root / config.raw.get("traceability", {}).get(
        "output_path", "docs/traceability.md"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_matrix(config), encoding="utf-8")
    return output_path
