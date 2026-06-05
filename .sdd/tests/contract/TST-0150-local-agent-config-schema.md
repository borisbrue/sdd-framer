---
id: TST-0150
project: ""
title: "local_agent Konfigurationsschema – Validierung und Fallback"
level: contract
spec: SPEC-0036
contract: CON-0128
status: planned
framework: pytest
artifact: "tests/contract/test_tst_0150.py"
tags: []
---

# Test: local_agent Konfigurationsschema

> **Level:** contract · **Spec:** SPEC-0036 · **Contract:** CON-0128 · **Status:** planned

## Was wird geprüft?

Ob das JSON-Schema für `local_agent` (CON-0128) korrekte Configs akzeptiert,
fehlerhafte ablehnt, und ob das Fallback-Verhalten bei fehlender Sektion
greifen (FR-10, FR-11, §5).

## Vorbedingungen

- `jsonschema` installiert
- Schema-Datei `local-agent-config.schema.json` lesbar
- SddConfig-Loader via Unit-Aufruf testbar

## Ablauf

1. Vollständige gültige Config (`enabled: true`, alle Pflichtfelder) →
   Schema-Validation: kein Fehler
2. `enabled: true` ohne `proxy_url` → Schema-Validation: Fehler
3. `enabled: true` ohne `context_window` → Schema-Validation: Fehler
4. `enabled: false` ohne `proxy_url` → Schema-Validation: kein Fehler (Pflicht nur bei enabled=true)
5. `local_agent`-Sektion fehlt vollständig → SddConfig-Loader gibt `enabled=False`-Verhalten
6. `max_parallel_local: 0` → Schema-Validation: Fehler (minimum: 1)
7. `api_key: "${MY_KEY}"` und `MY_KEY` nicht in Env → Factory wirft `RuntimeError`
8. `api_key: "${MY_KEY}"` und `MY_KEY=secret` in Env → Factory löst Wert auf, kein Fehler

## Erwartetes Ergebnis

- Fall 1: Valid
- Fall 2: `jsonschema.ValidationError`
- Fall 3: `jsonschema.ValidationError`
- Fall 4: Valid
- Fall 5: Cloud-Only-Modus aktiv, kein Fehler
- Fall 6: `jsonschema.ValidationError`
- Fall 7: `RuntimeError`
- Fall 8: `api_key == "secret"`, kein Fehler

## Verknüpfung mit Contract

- [x] INV-01: Fehlende Sektion → Cloud-Only, kein Fehler
- [x] INV-02: proxy_url muss gültige URL sein
- [x] INV-03: context_window > 0
- [x] INV-04: max_parallel ≥ 1
- [x] INV-05: ${ENV_VAR} wird aufgelöst
