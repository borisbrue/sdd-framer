---
id: TST-0095
project: PRJ-0001
title: "Tests: GET /api/server-info (CON-0085)"
contract: CON-0085
contracts: ["CON-0085"]
spec: SPEC-0025
level: contract
status: draft
artifact: "tests/unit/test_tst_0095.py"
---

# Test: Server-Info Endpoint

> **Contract:** CON-0085 · **Typ:** Contract-Test · **Status:** draft

## Abgedeckte Garantien

- CON-0085 G-01: HTTP 200 ohne Authorization-Header
- CON-0085 G-02: Response enthält name/externalUrl/tokenHash
- CON-0085 G-03: tokenHash = SHA-256(token)[:8], nie der rohe Token
- CON-0085 G-04: tokenHash ist leer wenn kein Token konfiguriert
- CON-0085 G-06: name kommt aus project.name in config.yaml
