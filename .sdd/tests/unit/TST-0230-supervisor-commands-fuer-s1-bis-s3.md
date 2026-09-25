---
id: TST-0230
title: "Supervisor-Commands fuer S1 bis S3"
level: unit
spec: SPEC-0053
contract: CON-0201
status: planned
framework: pytest
artifact: "tests/unit/test_con_0201.py"
tags: [pipeline, roles]
---

# Test: Supervisor-Commands fuer S1 bis S3

> **Level:** unit · **Spec:** SPEC-0053 · **Contract:** CON-0201 · **Status:** planned

## Was wird geprüft?

Supervisor-Commands je Entscheidungspunkt.

Schematests prüfen das Contract-Artefakt und laufen sofort. Verhaltenstests laufen gegen die echte
CLI mit einem OpenAI-kompatiblen Fake-Server und werden mit `requires_pipeline_cli` übersprungen,
bis `sdd pipeline` existiert.

## Vorbedingungen

- Schema-Artefakt von CON-0201.

## Ablauf

1. Alle Kombinationen aus Punkt (S1–S3) und Command gegen das Schema prüfen.

## Erwartetes Ergebnis

- Genau die Commands aus der Tabelle in INV-02 sind je Punkt gültig.
- Begründung Pflicht; reassign nie an supervisor; accept_frs mit Beleg.

## Verknüpfung mit Contract

- [x] INV-01
- [x] INV-02
- [x] INV-03
- [x] INV-04

## Verknüpfung mit Spec

FR-08
