---
id: TST-0002
title: "Akzeptanz: Login-Szenarien"
level: acceptance
spec: SPEC-0001
contract: CON-0002
status: planned
framework: behave
artifact: "tests/acceptance/features/login.feature"
tags: [auth, acceptance, gherkin]
---

# Test: Akzeptanz Login-Szenarien

> **Level:** acceptance · **Spec:** SPEC-0001 · **Contract:** CON-0002

## Was wird geprüft?

Die Gherkin-Szenarien aus `contracts/behavior/login.feature` werden als ausführbare Tests gegen das laufende System gefahren. Jedes Szenario MUSS bestanden werden.

## Vorbedingungen

- Test-Datenbank mit definierten Fixtures (Nutzer "alice@example.com")
- Rate-Limit-Konfiguration auf Test-Werte gestellt (5 Versuche / 15 min)
- Uhr deterministisch (Freezegun o.ä.) für Sperr-Tests

## Ablauf

1. Test-Runner (behave) lädt das Feature-File
2. Step-Definitions mappen Gherkin-Schritte auf HTTP-Calls
3. Jedes Szenario wird isoliert ausgeführt (DB-Rollback zwischen Tests)

## Erwartetes Ergebnis

Alle 5 Szenarien aus CON-0002 sind grün, einschließlich der Tabellen-getriebenen Validierungsfälle.

## Verknüpfung mit Contract

Dieser Test prüft folgende Szenarien aus CON-0002:

- [x] Erfolgreicher Login
- [x] Falsches Passwort
- [x] Nicht existierender Nutzer (INV-01: ununterscheidbar)
- [x] Account-Sperre nach 5 Fehlversuchen
- [x] Validierungsfehler (Tabellen-getrieben)

## Hinweise zur Implementierung

- Step "Angenommen es existiert ein Nutzer mit ..." nutzt Factory-Boy für Fixtures
- Step "JWT mit Algorithmus ES256" dekodiert ohne Verifikation und prüft Header
- Timing-Constancy für INV-01 wird hier NICHT geprüft (das ist Aufgabe eines Security-Tests)
