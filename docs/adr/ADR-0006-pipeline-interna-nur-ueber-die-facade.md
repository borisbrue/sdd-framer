---
id: ADR-0006
title: "Pipeline-Interna nur über die Facade"
status: accepted
date: 2026-09-26
deciders: [Boris, Claude]
related_specs: [SPEC-0062]
supersedes: ""
enforced_by: [ARCH-05]
---

# ADR-0006: Pipeline-Interna nur über die Facade

## Status

accepted

## Kontext

Seit SPEC-0062 ist `sdd pipeline` der einzige Ausführungspfad. Andere Module griffen direkt auf
Interna zu (`providers`, `runner`), die Web-UI plante dasselbe mit dem Mediator. Jede solche
Abhängigkeit macht einen Umbau der Pipeline zum Umbau der Aufrufer (DIP-Befund aus SPEC-0061).

## Optionen

### Option A: Schicht `pipeline` mit Facade
- **Pro:** Interna (`mediator`, `runner`, `steps`, `gates`, `providers`, `decisions`, `context`)
  bleiben austauschbar; Aufrufer sehen `facade`, `monitor`, `store`, `schemas`, `roles`,
  `path_policy` und `config_migration`
- **Contra:** eine zusätzliche Weiterleitung in `pipeline/facade.py`

### Option B: Keine Regel
- **Pro:** kein Aufwand
- **Contra:** die Kopplung wächst mit jedem Einstieg

## Entscheidung

Option A. Die Schicht `pipeline` umfasst `tool/sdd_cli/pipeline/**` (außer `path_policy`, das zu
`core` gehört). ARCH-05 (`forbidden_dependency`): Außerhalb von `pipeline` und `entry` importiert
kein Modul die Interna. Die CLI-Befehle in `main.py` und `pipeline_cli.py` (Schicht `entry`) sind
die Kompositionswurzel und dürfen sie nutzen. `pipeline` und `cli` stehen in ARCH-02 auf einer
Stufe, weil die Pipeline bestehende Werkzeuge (`decompose`, `finalize`, Evaluator) aufruft.
Als Teil der CLI (`sdd pipeline`) ist `pipeline` in ARCH-01 Schreiber für SDD-Artefakte (Run-Verzeichnis,
Rollen, Config-Migration).

## Folgen

`config_validator`, `decompose` und `validate` nutzen `pipeline.facade`; die Web-Route
`orchestrate` nutzt `store` und startet die Pipeline als Prozess.

Maschinell geprüft durch `ARCH-05` in `.sdd/architecture.yaml` (`sdd arch check`, Pre-Commit-Hook).
Bezug: AGENTS.md, Abschnitt „Architektur“.
