---
id: TST-0186
project: ""
title: "Holdout-Status ContainerView Verhalten (Acceptance)"
level: acceptance
spec: SPEC-0043
contract: CON-0160
status: planned
framework: pytest
artifact: "tests/acceptance/test_tst_0186.py"
tags: [acceptance, holdout, frontend, behavior]
---

# Test: Holdout-Status ContainerView Verhalten

> **Level:** acceptance · **Spec:** SPEC-0043 · **Contract:** CON-0160 · **Status:** planned

## Was wird geprüft?

Die Gherkin-Szenarien aus CON-0160 gegen die API-Schicht:
Korrekte Status-Auslieferung pro Szenario, INV-02 (nur neuester Lauf),
INV-03 (keine Trigger-Aktionen), SSE-Reconnect-Verhalten.

## Vorbedingungen

- HoldoutService mit kontrollierbarem State (Fixtures)
- FastAPI TestClient

## Ablauf

1. Laufender Holdout → GET liefert status=running
2. Bestandener Holdout → GET liefert status=passed, scenarios leer
3. Fehlgeschlagener Holdout → GET liefert status=failed, scenarios befüllt
4. Kein Lauf → GET liefert status=none
5. Zwei Läufe vorhanden → GET liefert nur neuesten (INV-02)
6. API-Endpunkt liefert keine Trigger-/Konfigurations-Felder (INV-03)

## Erwartetes Ergebnis

- Alle 6 Szenarien liefern die in CON-0160 definierten Ergebnisse
- INV-02: älterer Lauf wird nicht zurückgegeben
- INV-03: Response enthält keine action- oder config-Felder

## Negativfälle / Edge Cases

- SSE-Stream bei laufendem Holdout: Event-Payload entspricht HoldoutStatusEvent-Schema

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0160:

- [ ] INV-01: status-Wert ist immer als Text vorhanden (kein null-status bei vorhandenem Lauf)
- [ ] INV-02: nur neuester Lauf sichtbar
- [ ] INV-03: keine Trigger-Aktionen in der API-Response
- [ ] INV-04: SSE-Reconnect-Verhalten testbar via Mock
- [ ] Szenario "fehlgeschlagen": Szenario-Name in scenarios-Liste

## Hinweise zur Implementierung

HoldoutRepository als Fixture mocken.
SSE-Stream-Szenario via StreamingResponse-Mock prüfen.
