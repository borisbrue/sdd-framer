---
id: ADR-0002
title: "CLI ist einziger Schreiber für SDD-Artefakte"
status: accepted
date: 2026-09-25
deciders: [Boris, Claude]
related_specs: [SPEC-0059]
supersedes: ""
enforced_by: [ARCH-01]
---

# ADR-0002: CLI ist einziger Schreiber für SDD-Artefakte

## Status

accepted

## Kontext

SDD-Artefakte (`.sdd/specs`, `.sdd/contracts`, `.sdd/tests`, `docs/adr`, Gate- und
Run-Zustand unter `.sdd/`) tragen IDs, Status-Übergänge und Content-Hashes. AGENTS.md verlangt als
Taste Invariant, dass nur die CLI sie schreibt, damit IDs eindeutig bleiben und Lifecycle-Regeln
greifen. Tatsächlich schreibt die Web-API heute selbst (`web/api/routes/specs.py` u. a.).

## Optionen

### Option A: Nur die CLI schreibt (Web/UI/PWA/Hub delegieren an die CLI)
- **Pro:** eine Stelle für IDs, Status und Hashes
- **Contra:** Web-Routen müssen umgebaut werden

### Option B: Jede Schicht darf schreiben, Konventionen regeln den Rest
- **Pro:** kein Umbau
- **Contra:** Konventionen werden nicht geprüft; genau das hat die heutigen Direktschreiber ermöglicht

## Entscheidung

Option A. Die Regel ARCH-01 (`write_ownership`) erlaubt Schreibzugriffe auf `.sdd/**` und
`docs/adr/**` nur aus den Schichten `cli`, `entry` und `core` (Basismodule wie
`frontmatter.patch_status`, über die die CLI schreibt). Weil Schreibziele im Code fast immer
Variablen sind, gilt `unresolved: violation` (CON-0208): ein Schreibzugriff mit unbekanntem Ziel
aus einer anderen Schicht ist ein Verstoß.

## Folgen

Die heutigen Schreibzugriffe von Web-API, Hub und des CodeGen-Pfads stehen mit Grund in der
Baseline. Die Baseline ist für unaufgelöste Ziele dateigenau (CON-0208 INV-07).

Maschinell geprüft durch `ARCH-01` in `.sdd/architecture.yaml` (`sdd arch check`, Pre-Commit-Hook).
Bezug: AGENTS.md, Abschnitt „Architektur“.
