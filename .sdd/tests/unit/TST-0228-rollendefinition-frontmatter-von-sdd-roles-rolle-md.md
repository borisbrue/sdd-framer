---
id: TST-0228
title: "Rollendefinition: Frontmatter von .sdd/roles/<rolle>.md"
level: unit
spec: SPEC-0053
contract: CON-0199
status: planned
framework: pytest
artifact: "tests/unit/test_con_0199.py"
tags: [pipeline, roles]
---

# Test: Rollendefinition: Frontmatter von .sdd/roles/<rolle>.md

> **Level:** unit · **Spec:** SPEC-0053 · **Contract:** CON-0199 · **Status:** planned

## Was wird geprüft?

Schema der Rollendefinition; Installation der Default-Rollen durch `sdd init`/`sdd upgrade`.

Schematests prüfen das Contract-Artefakt und laufen sofort. Verhaltenstests laufen gegen die echte
CLI mit einem OpenAI-kompatiblen Fake-Server und werden mit `requires_pipeline_cli` übersprungen,
bis `sdd pipeline` existiert.

## Vorbedingungen

- Schema-Artefakt von CON-0199.
- Für FR-02: Default-Rollen im Blueprint (übersprungen bis `sdd pipeline` existiert).

## Ablauf

1. Gültige und ungültige Frontmatter gegen das Schema prüfen.
2. Projekt mit `init_project` anlegen, Rollendateien lesen und gegen das Schema prüfen.
3. Rolle lokal ändern, `sdd upgrade`, `.new` prüfen.

## Erwartetes Ergebnis

- Holdout als Quelle, fehlende SemVer, unbekannte Felder und `output_schema: null` werden abgelehnt.
- Alle fünf Rollen existieren, sind schema-gültig und haben einen Prompt.
- Lokal geänderte Rolle bleibt erhalten, Vorschlag als `.new`.

## Verknüpfung mit Contract

- [x] INV-01
- [x] INV-02
- [x] INV-04
- [x] INV-05
- [x] INV-06

## Verknüpfung mit Spec

FR-01, FR-02, FR-03
