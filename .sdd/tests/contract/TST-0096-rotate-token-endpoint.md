---
id: TST-0096
project: PRJ-0001
title: "Tests: POST /api/auth/rotate-token (CON-0086)"
contract: CON-0086
contracts: ["CON-0086"]
spec: SPEC-0025
level: contract
status: draft
artifact: "tests/unit/test_tst_0096.py"
---

# Test: Rotate-Token Endpoint

> **Contract:** CON-0086 · **Typ:** Contract-Test · **Status:** draft

## Abgedeckte Garantien

- CON-0086 G-01: HTTP 401 ohne Authorization-Header
- CON-0086 G-01: HTTP 401 mit falschem Token
- CON-0086 G-05: HTTP 401 mit blacklistem Token
- CON-0086 G-02: Neuer Token ist 64 Hex-Zeichen
- CON-0086 G-03: Alter Token wird blacklistet
- CON-0086 G-06: Response enthält {token: newToken}
