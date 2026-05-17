---
id: TST-0097
project: PRJ-0001
title: "Tests: GET /api/auth/qr-payload (CON-0087)"
contract: CON-0087
contracts: ["CON-0087"]
spec: SPEC-0025
level: contract
status: draft
artifact: "tests/unit/test_tst_0097.py"
---

# Test: QR-Onboarding-Flow (server-side)

> **Contract:** CON-0087 · **Typ:** Contract-Test · **Status:** draft

## Abgedeckte Garantien

- CON-0087 G-01: Response {sdd, name, url, token} wenn konfiguriert
- CON-0087 G-02: token ist vollständiger Token (64 Hex), nicht der Hash
- CON-0087 G-03: HTTP 404 wenn kein Token konfiguriert
- CON-0087 G-04: HTTP 404 wenn keine External-URL konfiguriert
- CON-0087 G-05: name stammt aus project.name in config.yaml
