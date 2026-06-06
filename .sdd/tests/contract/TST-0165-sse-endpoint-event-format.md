---
id: TST-0165
project: ""
title: "SSE-Endpoint /orchestrate/stream — Event-Format, Content-Type, Heartbeat"
level: contract
spec: SPEC-0037
contract: CON-0141
status: implemented
framework: pytest
artifact: "tests/contract/test_tst_0165.py"
tags: []
---

# Test: SSE-Endpoint Event-Format

> **Level:** contract · **Spec:** SPEC-0037 · **Contract:** CON-0141 · **Status:** implemented

## Was wird geprüft?

Ob `GET /orchestrate/stream/{run_id}` den korrekten Content-Type liefert,
publizierte Events als SSE-Datenstrom ausgibt und Heartbeat-Comments sendet
(CON-0141 INV-01–INV-03).

## Verknüpfung mit Contract

- [x] INV-01: Content-Type text/event-stream
- [x] INV-02: Events als JSON im data:-Feld
- [x] INV-03: Heartbeat-Comment `: heartbeat` gesendet
