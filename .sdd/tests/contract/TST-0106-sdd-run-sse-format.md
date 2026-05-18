---
id: TST-0106
project: PRJ-0001
title: "Tests: POST /api/sdd/run SSE-Format + Exit-Code (CON-0075)"
contract: CON-0075
contracts: ["CON-0075"]
spec: SPEC-0023
level: contract
status: draft
artifact: "tests/unit/test_tst_0106.py"
---

# Test: POST /api/sdd/run SSE-Format

> **Contract:** CON-0075 · **Typ:** Contract-Test · **Status:** draft

## Abgedeckte Garantien

- G-01: Fehlende Auth → HTTP 401
- G-02: Request-Body mit cmd + optionale args
- G-03: Unbekannter Command → HTTP 422 `unknown_command`
- G-04: SSE-Event pro Zeile: `data: {"type": "line", "data": "...", "stream": "stdout"|"stderr"}`
- G-05: Abschluss-Event: `data: {"type": "done", "exit_code": 0|-1}`
- G-08: Content-Type: `text/event-stream`
- G-09: Command-Allowlist: orchestrate, start, validate, dev, contract, spec, estimate
