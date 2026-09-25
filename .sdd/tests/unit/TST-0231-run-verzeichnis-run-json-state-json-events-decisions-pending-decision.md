---
id: TST-0231
title: "Run-Verzeichnis: run.json, state.json, events, decisions, pending-decision"
level: unit
spec: SPEC-0053
contract: CON-0202
status: planned
framework: pytest
artifact: "tests/unit/test_con_0202.py"
tags: [pipeline, roles]
---

# Test: Run-Verzeichnis: run.json, state.json, events, decisions, pending-decision

> **Level:** unit · **Spec:** SPEC-0053 · **Contract:** CON-0202 · **Status:** planned

## Was wird geprüft?

Dateien des Run-Verzeichnisses.

Schematests prüfen das Contract-Artefakt und laufen sofort. Verhaltenstests laufen gegen die echte
CLI mit einem OpenAI-kompatiblen Fake-Server und werden mit `requires_pipeline_cli` übersprungen,
bis `sdd pipeline` existiert.

## Vorbedingungen

- Schema-Artefakt von CON-0202.

## Ablauf

1. Gültige und ungültige Instanzen je `$defs`-Eintrag prüfen.

## Erwartetes Ergebnis

- Entscheidungen und Anfragen tragen `request_id`; Anfragen nennen mindestens ein zulässiges Command.
- Unbekannte Status, Task-Zustände und Klartextfelder werden abgelehnt.

## Verknüpfung mit Contract

- [x] INV-02
- [x] INV-05

## Verknüpfung mit Spec

FR-12, FR-15
