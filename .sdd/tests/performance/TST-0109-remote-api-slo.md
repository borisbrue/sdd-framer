---
id: TST-0109
project: PRJ-0001
title: "Tests: Remote API SLO (CON-0078)"
contract: CON-0078
contracts: ["CON-0078"]
spec: SPEC-0023
level: performance
status: draft
artifact: "tests/unit/test_tst_0109.py"
---

# Test: Remote API SLO

> **Contract:** CON-0078 · **Typ:** Performance-Test · **Status:** draft

## Abgedeckte SLOs

- CON-0078: /ws/chat first-token p95 < 200ms (10 Messungen, LLM gemockt)
- CON-0078: /api/sdd/run first SSE-Zeile p95 < 1000ms (10 Messungen, subprocess gemockt)
- CON-0078: /api/push/subscribe Response p95 < 100ms (20 Messungen)
