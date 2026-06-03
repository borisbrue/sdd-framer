---
id: TST-0141
project: ""
title: "Fallback-Logik: Single-Context-Mode bei Nicht-Claude-Provider"
level: unit
spec: SPEC-0035
contract: CON-0122
status: planned
framework: "pytest"
artifact: "tests/unit/test_tst_0141.py"
tags: []
---

# Test: Fallback-Logik Single-Context-Mode

> **Level:** unit · **Spec:** SPEC-0035 · **Contract:** CON-0122 · **Status:** planned

## Was wird geprüft?

Ob der Provider-Guard bei Nicht-Claude-Provider korrekt auf Single-Context-Mode
umschaltet und den Fallback im Output kennzeichnet (FR-09, G-04 von CON-0122).

## Vorbedingungen

- Provider-Guard-Funktion isolierbar (keine echte API-Verbindung)
- Testdaten: Provider-Namen "claude" und "openai"

## Ablauf

1. Provider-Guard mit Provider="claude" aufrufen → erwartet: Sub-Agent-Mode aktiv
2. Provider-Guard mit Provider="openai" aufrufen → erwartet: Single-Context-Mode
3. Provider-Guard mit Provider="gemini" aufrufen → erwartet: Single-Context-Mode
4. Im Fallback-Modus prüfen: token-history erhält keine task_id-Einträge

## Erwartetes Ergebnis

- Claude-Provider: Delegations-Modus aktiviert (bool True / enum)
- Nicht-Claude-Provider: Single-Context-Modus (bool False / enum)
- Fallback-Output enthält Kennzeichnung

## Verknüpfung mit Contract

- [x] G-04: Non-Claude-Provider → Single-Context-Mode + Kennzeichnung
- [x] INV-03: Kein task_id-Eintrag bei Fallback
