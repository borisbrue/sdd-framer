---
id: TST-0102
project: PRJ-0001
title: "Tests: Service Worker Push-Handler (CON-0092)"
contract: CON-0092
contracts: ["CON-0092"]
spec: SPEC-0024
level: contract
status: draft
artifact: "tests/unit/test_tst_0102.py"
---

# Test: Service Worker Push-Handler

> **Contract:** CON-0092 · **Typ:** Contract-Test · **Status:** draft

## Abgedeckte Garantien

- CON-0092: Push-Payload-Format wird vom Server korrekt gesendet
- CON-0092: NotificationStrategy Auswahl (Vordergrund vs. Hintergrund)

## Hinweis

Vollständige Tests erfordern SPEC-0023's `/api/push/subscribe`-Endpoint.
Python-Stubs bis zur SPEC-0023-Implementierung.
