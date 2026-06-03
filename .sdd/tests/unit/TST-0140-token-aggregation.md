---
id: TST-0140
project: ""
title: "Token-Aggregation: Summe Sub-Agenten-Token"
level: unit
spec: SPEC-0035
contract: CON-0121
status: planned
framework: "pytest"
artifact: "tests/unit/test_tst_0140.py"
tags: []
---

# Test: Token-Aggregation

> **Level:** unit · **Spec:** SPEC-0035 · **Contract:** CON-0121 · **Status:** planned

## Was wird geprüft?

Ob die Summe der task-granularen Token-Einträge dem Gesamt-Token-Verbrauch einer Spec
in `token-history` entspricht (INV-05 von CON-0121).

## Vorbedingungen

- `TokenHistoryRow` enthält `task_id` und `task_label` Felder
- Testdaten: 3 task-granulare Einträge mit bekannten Token-Werten

## Ablauf

1. Drei `TokenHistoryRow`-Objekte mit task_id erstellen (input/output je bekannt)
2. Summe input_tokens und output_tokens berechnen
3. Gegen erwarteten Gesamtwert vergleichen
4. Prüfen: Einträge ohne task_id fließen nicht in Task-Aggregation ein

## Erwartetes Ergebnis

- Summe input_tokens der 3 Einträge == erwartete Gesamtsumme
- Einträge mit task_id == None werden nicht gezählt

## Verknüpfung mit Contract

- [x] INV-05: Summe Sub-Agenten-Token == Gesamt-Eintrag
