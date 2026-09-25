---
id: ADR-0003
title: "Schichtrichtung Einstieg, Web/UI/PWA/Hub, CLI, LLM, Core"
status: accepted
date: 2026-09-25
deciders: [Boris, Claude]
related_specs: [SPEC-0059]
supersedes: ""
enforced_by: [ARCH-02]
---

# ADR-0003: Schichtrichtung Einstieg, Web/UI/PWA/Hub, CLI, LLM, Core

## Status

accepted

## Kontext

AGENTS.md beschreibt die Richtung Web/UI → CLI → Filesystem. Ein Probelauf zeigte zwei
Strukturen, die eine einfache Kette nicht abbildet: `main.py` startet als Einstiegspunkt Web, Hub
und PWA, und fast alle Schichten brauchen Basismodule wie `config.py`.

## Optionen

### Option A: Kette web → cli → llm ohne Sonderschichten
- **Pro:** einfach
- **Contra:** Einstiegspunkt und Basismodule erscheinen als Verstöße; die Baseline würde groß und bedeutungslos

### Option B: Zusätzliche Schichten `entry` (Kompositionswurzel) und `core` (Basismodule)
- **Pro:** die Regel beschreibt die echte Struktur
- **Contra:** zwei Schichten mehr zu pflegen

## Entscheidung

Option B. ARCH-02 (`allowed_dependencies`): `entry` darf alles; `web|ui|pwa|hub` dürfen `cli`,
`llm` und `core`; `cli` darf `llm` und `core`; `llm` darf nur `core`; `core` hängt von nichts ab.
`core` umfasst `config.py`, `frontmatter.py`, `quality/files.py` und `pipeline/path_policy.py`.

## Folgen

Neue Pakete unter `tool/sdd_cli/` landen in `cli`. Wer eine neue Oberfläche oder einen neuen
Server ergänzt, ordnet ihn in `.sdd/architecture.yaml` einer eigenen Schicht zu.

Maschinell geprüft durch `ARCH-02` in `.sdd/architecture.yaml` (`sdd arch check`, Pre-Commit-Hook).
Bezug: AGENTS.md, Abschnitt „Architektur“.
