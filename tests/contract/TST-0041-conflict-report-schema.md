---
id: TST-0041
title: "Conflict Report JSON Schema"
level: contract
spec: SPEC-0014
contract: CON-0029
status: implemented
framework: pytest
artifact: "tests/contract/test_con-0029.py"
tags: [schema, json-schema, conflict-report]
---

# Test: Conflict Report JSON Schema (CON-0029)

> **Level:** contract · **Spec:** SPEC-0014 · **Contract:** CON-0029

## Was wird geprüft?

Valide und invalide Conflict-Report-Dokumente gegen das JSON-Schema in `contracts/data/conflict-report.schema.json` validiert.

## Vorbedingungen

- `contracts/data/conflict-report.schema.json` vorhanden
- `jsonschema` installiert

## Ablauf

1. Minimal-valides Dokument besteht Validierung
2. Vollständiges Dokument mit allen optionalen Feldern besteht
3. `cf_id` ohne Präfix `CF-` → Fehler
4. `severity` mit ungültigem Wert → Fehler
5. `status` mit ungültigem Wert → Fehler
6. Alle 5 Konflikttypen als `type` akzeptiert
7. `resolution` null oder Objekt erlaubt

## Verknüpfung mit Contract

- [x] CF-ID-Pattern `^CF-[0-9]+-[0-9]{3,}$`
- [x] `type` enum: 5 Typen
- [x] `severity` enum: low/medium/high
- [x] `status` enum: open/resolved/acknowledged
