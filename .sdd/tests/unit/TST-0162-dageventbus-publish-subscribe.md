---
id: TST-0162
project: ""
title: "DagEventBus: publish/subscribe — Event-Ordering, run_id-Isolation"
level: unit
spec: SPEC-0037
contract: CON-0140
status: implemented
framework: pytest
artifact: "tests/unit/test_tst_0162.py"
tags: []
---

# Test: DagEventBus publish/subscribe

> **Level:** unit · **Spec:** SPEC-0037 · **Contract:** CON-0140 · **Status:** implemented

## Was wird geprüft?

Ob `DagEventBus` Events korrekt an Subscriber ausliefert, FIFO-Reihenfolge hält,
`run_id`-Isolation garantiert und publish ohne Subscriber nicht wirft (CON-0140
INV-01–INV-05).

## Verknüpfung mit Contract

- [x] INV-01: run_id und task_id Pflichtfelder (via Pydantic)
- [x] INV-04: Events verschiedener run_ids strikt isoliert
- [x] INV-05: publish ohne Subscriber wirft keine Exception
