---
id: TST-0142
project: ""
title: "Token-History-Task-Schema: task_id-Felder"
level: contract
spec: SPEC-0035
contract: CON-0121
status: planned
framework: "pytest+jsonschema"
artifact: "tests/contract/test_tst_0142.py"
tags: []
---

# Test: Token-History-Task-Schema

> **Level:** contract · **Spec:** SPEC-0035 · **Contract:** CON-0121 · **Status:** planned

## Was wird geprüft?

Ob das JSON-Schema in `token-history-task-schema.schema.json` alle 5 Invarianten
aus CON-0121 korrekt durchsetzt: Pflichtfelder, optionale task_id/task_label,
task_id+task_label Kopplung, und Null-Verhalten.

## Vorbedingungen

- Schema-Artifact `.sdd/contracts/data/token-history-task-schema.schema.json` existiert
- `jsonschema`-Bibliothek ist installiert

## Ablauf

1. Vollständigen Row ohne task_id/task_label validieren → soll durchlaufen
2. Row mit task_id + task_label (beide gesetzt) validieren → soll durchlaufen
3. Row mit task_id gesetzt, task_label fehlt → ValidationError erwartet
4. Row mit task_id=null, task_label gesetzt → soll durchlaufen (null task_id erlaubt)
5. Pflichtfeld `input_tokens` weglassen → ValidationError erwartet
6. `task_id` als Integer statt String → ValidationError erwartet

## Erwartetes Ergebnis

- Schritte 1, 2, 4: Schema-Validierung erfolgreich
- Schritt 3: ValidationError (task_label muss bei task_id gesetzt sein)
- Schritte 5, 6: ValidationError

## Verknüpfung mit Contract

- [x] INV-01: Pflichtfelder bleiben unverändert
- [x] INV-02: task_id optional, korrekte Typen
- [x] INV-03: task_label required wenn task_id gesetzt
- [x] INV-04: task_label null erlaubt wenn task_id null
