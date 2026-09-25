---
id: TST-0229
title: "Rollenausgaben: decomposer, test_author, implementer, reviewer"
level: unit
spec: SPEC-0053
contract: CON-0200
status: planned
framework: pytest
artifact: "tests/unit/test_con_0200.py"
tags: [pipeline, roles]
---

# Test: Rollenausgaben: decomposer, test_author, implementer, reviewer

> **Level:** unit · **Spec:** SPEC-0053 · **Contract:** CON-0200 · **Status:** planned

## Was wird geprüft?

Ausgabeschemata der vier Arbeitsrollen.

Schematests prüfen das Contract-Artefakt und laufen sofort. Verhaltenstests laufen gegen die echte
CLI mit einem OpenAI-kompatiblen Fake-Server und werden mit `requires_pipeline_cli` übersprungen,
bis `sdd pipeline` existiert.

## Vorbedingungen

- Schema-Artefakt von CON-0200.

## Ablauf

1. Je Rolle gültige und ungültige Ausgaben gegen `$defs/<rolle>` prüfen.

## Erwartetes Ergebnis

- code/test-Tasks ohne FR, ohne `test_file`, ohne `allowed_paths` und leere Zerlegungen werden abgelehnt; doc-Tasks ohne FR sind gültig.
- `fail` ohne Befund und Pfadflucht im implementer werden abgelehnt.

## Verknüpfung mit Contract

- [x] INV-01
- [x] INV-02
- [x] INV-03
- [x] INV-04
- [x] INV-05

## Verknüpfung mit Spec

FR-05, FR-11
