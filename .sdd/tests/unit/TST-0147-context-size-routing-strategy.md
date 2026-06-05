---
id: TST-0147
project: ""
title: "ContextSizeRoutingStrategy: Routing-Entscheidung nach Token-Größe"
level: unit
spec: SPEC-0036
contract: CON-0125
status: planned
framework: pytest
artifact: "tests/unit/test_tst_0147.py"
tags: []
---

# Test: ContextSizeRoutingStrategy – Routing-Entscheidung

> **Level:** unit · **Spec:** SPEC-0036 · **Contract:** CON-0125 · **Status:** planned

## Was wird geprüft?

Ob `ContextSizeRoutingStrategy.route()` korrekt `"local"` oder `"cloud"` zurückgibt
basierend auf Token-Größe, context_window, context_reserve_tokens und enabled-Flag (FR-02, FR-03).

## Vorbedingungen

- `ContextSizeRoutingStrategy` isolierbar ohne Netzwerkzugang
- `tiktoken` installiert
- Testdaten: TaskContext-Objekte mit vordefinierten Token-Größen (via Mock)

## Ablauf

1. `route(task)` mit 20 000 Tokens, window=32 768, reserve=4 096, enabled=True → `"local"`
2. `route(task)` mit 30 000 Tokens, window=32 768, reserve=4 096, enabled=True → `"cloud"`
3. `route(task)` mit exakt 28 672 Tokens (= 32 768 - 4 096), enabled=True → `"local"`
4. `route(task)` mit 28 673 Tokens (1 über Grenze), enabled=True → `"cloud"`
5. `route(task)` mit 1 000 Tokens, enabled=False → `"cloud"` (unabhängig von Größe)
6. `route(task)` ohne Netzwerkzugang (Socket-Mock geschlossen) → kein Netzwerkfehler

## Erwartetes Ergebnis

- Fall 1: `"local"`
- Fall 2: `"cloud"`
- Fall 3: `"local"` (Grenzwert inklusiv)
- Fall 4: `"cloud"`
- Fall 5: `"cloud"`
- Fall 6: Kein `ConnectionError`, Ergebnis `"local"`

## Verknüpfung mit Contract

- [x] INV-01: Rückgabe ist immer `"local"` oder `"cloud"`
- [x] INV-02: `enabled=False` → immer `"cloud"`
- [x] INV-03: Deterministisch (gleiche Eingabe → gleiche Ausgabe)
- [x] INV-04: Kein Netzwerkaufruf
