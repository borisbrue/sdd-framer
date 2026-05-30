---
id: TST-0136
project: ""                # PRJ-XXXX
title: "Two-Stage Regression Check Behavior"
level: contract
spec: SPEC-0030
contract: CON-0117
status: planned
framework: "behave"
artifact: "tests/contract/test_tst_0136_regression_check_behavior.feature"
tags: []
---

# Test: Two-Stage Regression Check Behavior

> **Level:** contract · **Spec:** SPEC-0030 · **Contract:** CON-0117 · **Status:** planned

## Was wird geprüft?

Ob `sdd regression-check` die regelbasierte Stufe 1 und den LLM-Semantik-Check
(Stufe 2) in der richtigen Reihenfolge ausführt, korrekte Exit-Codes liefert und
bei nicht erreichbarem LLM sicher degradiert — gemäß CON-0117 INV-01 bis INV-04.

## Vorbedingungen

- `sdd regression-check` ist im PATH verfügbar
- Eine Ziel-Spec (SPEC-TEST) mit Status `approved` oder `in-progress` existiert
- Mindestens eine Spec mit Status `implemented` existiert als Vergleichsbasis
- Eine Spec mit Status `draft` existiert (für INV-04-Test)

## Ablauf

1. `sdd regression-check SPEC-TEST` aufrufen mit konfliktfreien Specs
2. Dasselbe mit einer Vergleichs-Spec, die einen Endpoint-Konflikt hat (→ `error`)
3. Dasselbe mit einer Vergleichs-Spec, die nur eine semantische Überschneidung hat (→ `warning`)
4. LLM-Erreichbarkeit simuliert abschalten, erneut aufrufen
5. Draft-Spec als Vergleichsbasis eintragen, prüfen ob sie ignoriert wird

## Erwartetes Ergebnis

- Ausgabe enthält immer eine Stufe-1-Sektion vor der Stufe-2-Sektion
- Exit-Code 1 wenn mindestens ein `[rule]`- oder `[llm]`-Befund mit `severity: error`
- Exit-Code 0 bei ausschließlich `warning`/`info`-Befunden
- Bei LLM-Ausfall: Zeile `[llm] ⚠ LLM-Check übersprungen (kein API-Zugang)` in der Ausgabe; Stufe-1-Ergebnisse vollständig vorhanden; Exit-Code entspricht nur Stufe-1-Befunden
- Draft-Spec erscheint nicht in den `spec_id`-Feldern eines Befunds

## Negativfälle / Edge Cases

- Keine implementierten Specs vorhanden: Stufe 1 gibt `✓ Keine implementierten Specs zum Vergleich` aus, Stufe 2 gibt `✓ Kein inhaltlicher Regressionskonflikt` aus; Exit-Code 0
- Nur draft-Specs vorhanden: selbes Verhalten wie oben (INV-04)
- LLM-Fehler nach Teilantwort (Abbruch mitten im Stream): Stufe 2 wird verworfen, Warnung erscheint, kein Crash

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0117:

- [ ] INV-01: Stufe-1-Ausgabe erscheint vor Stufe-2-Ausgabe
- [ ] INV-02a: Exit-Code 1 bei mindestens einem `error`-Befund
- [ ] INV-02b: Exit-Code 0 bei ausschließlich `warning`/`info`
- [ ] INV-03: LLM-Ausfall → Warnung + Stufe 1 vollständig + kein Crash
- [ ] INV-04: `draft`-Specs erscheinen nicht in Befunden

## Hinweise zur Implementierung

Framework: `behave` (BDD, passend zum Gherkin-Artifact in CON-0117).
Fixture: Temp-Verzeichnis mit Mini-SDD-Projekt (2–3 Stub-Specs, steuerbar per Status).
LLM-Ausfall simulieren: Env-Variable `ANTHROPIC_API_KEY` auf ungültigen Wert setzen oder
Mock-Adapter injizieren.
