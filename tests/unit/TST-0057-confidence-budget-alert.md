---
id: TST-0057
project: PRJ-0001
title: "Konfidenz-Level und Budget-Alert"
level: unit
spec: SPEC-0011
contract: CON-0042
status: planned
framework: pytest
artifact: "tests/unit/test_estimation.py"
tags: ["confidence", "budget", "estimation"]
---

# Test: Konfidenz-Level und Budget-Alert

> **Level:** unit · **Spec:** SPEC-0011 · **Contract:** CON-0042 · **Status:** planned

## Was wird geprüft?

- Konfidenz-Klassifikation: < 3 → LOW, 3–9 → MEDIUM, ≥ 10 → HIGH
- Budget-Alert wird ausgelöst wenn `estimated_usd > budget_alert_usd`
- Budget-Alert fehlt wenn `budget_alert_usd` nicht konfiguriert

## Ablauf

### TC-01: Konfidenz LOW

Gegeben 2 historische Datenpunkte.
Prüfe: `confidence == "LOW"`.

### TC-02: Konfidenz MEDIUM

Gegeben 5 historische Datenpunkte.
Prüfe: `confidence == "MEDIUM"`.

### TC-03: Konfidenz HIGH

Gegeben 10 historische Datenpunkte.
Prüfe: `confidence == "HIGH"`.

### TC-04: Budget-Alert ausgelöst

Gegeben `budget_alert_usd: 0.001` (sehr klein).
Prüfe: `EstimateResult.budget_exceeded == True`.

### TC-05: Kein Budget-Alert ohne Konfiguration

Gegeben kein `budget_alert_usd` in config.
Prüfe: `EstimateResult.budget_exceeded == False`.

## Erwartetes Ergebnis

Alle 5 Test-Cases bestehen mit rein lokalen Berechnungen.
