---
id: TST-0059
project: PRJ-0001
title: "cost_estimation-Konfiguration: Preisberechnung und Fallback"
level: unit
spec: SPEC-0011
contract: CON-0044
status: planned
framework: pytest
artifact: "tests/unit/test_estimation.py"
tags: ["config", "pricing", "estimation"]
---

# Test: `cost_estimation`-Konfiguration – Preisberechnung und Fallback

> **Level:** unit · **Spec:** SPEC-0011 · **Contract:** CON-0044 · **Status:** planned

## Was wird geprüft?

- Kostenberechnung mit bekanntem Preismodell ist korrekt
- Unbekanntes Modell fällt auf `default`-Preis zurück
- `model_fallback: True` wird gesetzt wenn Modell nicht in `model_prices`
- Cache-Read-Tokens werden separat berechnet

## Ablauf

### TC-01: Korrekte Kostenberechnung

Gegeben:
- 1.000 Input-Tokens × 3.00 USD/M = 0.003000 USD
- 500 Output-Tokens × 15.00 USD/M = 0.007500 USD
- Gesamt = 0.010500 USD

Prüfe: `_calc_usd(price, 1000, 500) == 0.0105`.

### TC-02: Fallback auf default-Preis

Gegeben Modell `"unknown-model-xyz"` nicht in `model_prices`.
Prüfe: `model_fallback == True` und Preis aus `default`-Eintrag verwendet.

### TC-03: Cache-Read-Kosten

Gegeben 10.000 Cache-Read-Tokens × 0.08 USD/M = 0.0008 USD.
Prüfe: Gesamtkosten enthalten Cache-Read-Anteil.

### TC-04: Kein budget_alert_usd → budget_exceeded False

Gegeben Config ohne `budget_alert_usd`.
Prüfe: `budget_exceeded == False` unabhängig von Schätzhöhe.

## Erwartetes Ergebnis

Alle 4 Test-Cases bestehen mit rein lokaler Arithmetik, kein LLM-Aufruf.
