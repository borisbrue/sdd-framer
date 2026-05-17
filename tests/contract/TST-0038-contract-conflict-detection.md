---
id: TST-0038
title: "Contract Conflict Detection – Analyse-Verhalten"
level: contract
spec: SPEC-0014
contract: CON-0026
status: implemented
framework: pytest
artifact: "tests/contract/test_con-0026.py"
tags: [conflict, detection, cache]
---

# Test: Contract Conflict Detection (CON-0026)

> **Level:** contract · **Spec:** SPEC-0014 · **Contract:** CON-0026

## Was wird geprüft?

Korrekte Erkennung aller 5 Konflikttypen, Auflösungsregeln, Cache-Verhalten und Phase-5-Gate-Enforcement bei offenen Konflikten.

## Vorbedingungen

- `tool/sdd_cli/conflict_detector.py` implementiert
- Temporäre Contracts als `.md`-Fixtures

## Ablauf

1. Zwei Contracts mit identischem Endpunkt → `endpoint-overlap` erkannt
2. Disjunkte Contracts → leerer Konfliktbericht
3. Workspace-Scan erfasst `active` und `draft`, nicht `deprecated`
4. `can_start_phase("tests-generated")` blockiert wenn `status=open` Konflikt existiert
5. `resolve()` setzt `status=resolved`
6. `acknowledge()` ohne `reason` → `ValueError`
7. Cache-Invalidierung bei Datei-Hash-Änderung

## Erwartetes Ergebnis

Alle Invarianten aus CON-0026 werden eingehalten.

## Verknüpfung mit Contract

- [x] INV-01: Alle 5 Konflikttypen erkennbar
- [x] INV-03: Phase-5-Gate bei offenem Konflikt
- [x] INV-05: File-Hash-Cache wird korrekt invalidiert
- [x] INV-07: Acknowledge ohne Begründung abgelehnt
