---
id: TST-0151
project: ""
title: "Token-History agent_type/model Schema-Erweiterung – Schreib- und Lesekonformität"
level: contract
spec: SPEC-0036
contract: CON-0129
status: planned
framework: pytest
artifact: "tests/contract/test_tst_0151.py"
tags: []
---

# Test: Token-History agent_type/model Schema-Erweiterung

> **Level:** contract · **Spec:** SPEC-0036 · **Contract:** CON-0129 · **Status:** planned

## Was wird geprüft?

Ob `agent_type` und `model` korrekt in `token-history` geschrieben und gelesen werden,
ob Rückwärtskompatibilität mit CON-0121-Einträgen (ohne agent_type) gewährleistet ist,
und ob ungültige agent_type-Werte abgelehnt werden (FR-07).

## Vorbedingungen

- `jsonschema` installiert
- Schema `token-history-agent-type.schema.json` lesbar
- Test-DB oder in-memory SQLite mit `token_usage`-Tabelle

## Ablauf

1. Eintrag mit `agent_type: "local"` und `model: "llama3.1:8b"` →
   Schema-Validation: kein Fehler; Eintrag lesbar
2. Eintrag mit `agent_type: "cloud"` und `model: "claude-sonnet-4-6"` →
   Schema-Validation: kein Fehler
3. Eintrag ohne `agent_type` (CON-0121-kompatibler Eintrag) →
   Schema-Validation: kein Fehler (optionales Feld)
4. Eintrag mit `agent_type: "local"` ohne `model` →
   Schema-Validation: Fehler (model Pflicht wenn agent_type gesetzt)
5. Eintrag mit `agent_type: "unknown"` →
   Schema-Validation: Fehler (enum: ["local", "cloud", null])
6. `sdd calibrate SPEC-XXXX` mit gemischten Einträgen (local + cloud) →
   Output zeigt `cloud_tokens` und `local_tokens` getrennt

## Erwartetes Ergebnis

- Fall 1: Valid, Daten korrekt persistent
- Fall 2: Valid
- Fall 3: Valid (Rückwärtskompatibilität)
- Fall 4: `jsonschema.ValidationError`
- Fall 5: `jsonschema.ValidationError`
- Fall 6: Breakdown im calibrate-Output korrekt summiert

## Verknüpfung mit Contract

- [x] INV-01: agent_type ist optional, enum ["local", "cloud", null]
- [x] INV-02: model Pflicht wenn agent_type gesetzt
- [x] INV-03: Rückwärtskompatibilität mit CON-0121-Einträgen
- [x] INV-04: Lokale Tasks → agent_type="local"; Cloud-Tasks → agent_type="cloud"
