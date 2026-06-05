---
id: TST-0148
project: ""
title: "LocalSubAgentProxy: Ausführung, Env-Override und Fehler-Eskalation"
level: unit
spec: SPEC-0036
contract: CON-0126
status: planned
framework: pytest
artifact: "tests/unit/test_tst_0148.py"
tags: []
---

# Test: LocalSubAgentProxy – Ausführung und Fehler-Eskalation

> **Level:** unit · **Spec:** SPEC-0036 · **Contract:** CON-0126 · **Status:** planned

## Was wird geprüft?

Ob `LocalSubAgentProxy.execute()` korrekt `ANTHROPIC_BASE_URL` und `ANTHROPIC_API_KEY`
im Subprocess-Environment setzt, api_key nicht loggt, und Fehler sofort zu Cloud
eskaliert (FR-04, FR-09).

## Vorbedingungen

- `subprocess.run` via Mock ersetzbar
- `CloudSubAgentProxy` via Mock ersetzbar
- Logging via `caplog` (pytest) oder Log-Handler-Mock

## Ablauf

1. `execute(task)` erfolgreich → prüfe Subprocess-Env: `ANTHROPIC_BASE_URL` gesetzt,
   `ANTHROPIC_API_KEY` gesetzt, Host-Env unverändert nach Aufruf
2. `execute(task)` erfolgreich → prüfe dass `"secret-key"` in keinem Log-Eintrag erscheint
3. `execute(task)` wirft `ConnectionError` → `CloudSubAgentProxy.execute()` wird
   aufgerufen, kein lokaler Retry
4. Subprocess bricht mit Exit-Code ≠ 0 ab → Eskalation zu Cloud, kein lokaler Retry
5. Cloud-Eskalation schlägt ebenfalls fehl → `DagSchedulerError` wird geraist,
   kein weiterer Task dispatcht
6. `LocalSubAgentProxy` und `CloudSubAgentProxy` teilen dasselbe `SubAgentProxy`-Protocol
   → duck-typing-Test via `isinstance(proxy, SubAgentProxy)`

## Erwartetes Ergebnis

- Fall 1: Subprocess-Env enthält korrekte Variablen, Host-Env sauber
- Fall 2: Kein Log-Eintrag mit `"secret-key"`
- Fall 3: `CloudSubAgentProxy.execute.call_count == 1`
- Fall 4: `CloudSubAgentProxy.execute.call_count == 1`
- Fall 5: `DagSchedulerError` raised
- Fall 6: `isinstance` True für beide Proxy-Typen

## Verknüpfung mit Contract

- [x] INV-01: Env-Variablen als Subprocess-Env, nicht Prozess-weit
- [x] INV-02: Polymorphes Interface
- [x] INV-03: Sofortiger Cloud-Retry bei lokalem Fehler
- [x] INV-04: api_key nicht in Logs
