---
id: TST-0210
project: PRJ-0001
title: "PatternRegistry.catalog_summary() – Ausgabeformat"
level: unit
spec: SPEC-0048
contract: CON-0183
status: draft
framework: pytest
artifact: "tests/unit/test_tst_0210.py"
tags:
  - patterns
  - design-decisions
---

# Test: PatternRegistry.catalog_summary() – Ausgabeformat

> **Level:** unit · **Spec:** SPEC-0048 · **Contract:** CON-0183

## Was wird geprüft?

Prüft `PatternRegistry.catalog_summary()`: Rückgabe bei leerem/fehlendem Katalog,
Zeilenformat, Kürzung der Begründung auf 120 Zeichen, Begrenzung auf `max_entries`
mit Sortierung nach `accepted_at` absteigend, Ausschluss von `exclude_spec_id`,
Verhalten bei korrupter `_catalog.json`.

## Vorbedingungen

- `PatternRegistry` existiert in `sdd_cli.pattern` (SPEC-0015)
- `catalog_summary()` ist als neue Methode implementiert (SPEC-0048)

## Ablauf

1. Registry mit leerem/fehlendem Katalog → leerer String
2. Registry mit 1 Eintrag → eine Zeile im Format `- {pattern_name} ({spec_id}): {reason}`
3. Eintrag mit `acceptance_reason` > 120 Zeichen → gekürzt mit `…`-Suffix
4. 15 Einträge, `max_entries=10` → genau 10 Zeilen, neueste zuerst
5. `exclude_spec_id` gesetzt → Einträge dieser Spec fehlen, zählen nicht gegen das Limit
6. Korrupte `_catalog.json` → leerer String, kein Exception-Propagieren

## Verknüpfung mit Contract (CON-0183)

- [x] INV-01: Rückgabetyp immer `str`, nie `None`
- [x] INV-02: Begründung auf 120 Zeichen gekürzt, `…`-Suffix bei Kürzung
- [x] INV-03: Maximal `max_entries` Zeilen, neueste zuerst
- [x] INV-04: `exclude_spec_id` wird vor der `max_entries`-Begrenzung gefiltert
- [x] INV-05: Korrupte/fehlende `_catalog.json` wird wie leerer Katalog behandelt
