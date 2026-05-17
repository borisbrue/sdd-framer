---
id: TST-0098
project: PRJ-0001
title: "Tests: PWA Projects Schema Kompatibilität (CON-0088)"
contract: CON-0088
contracts: ["CON-0088"]
spec: SPEC-0025
level: contract
status: draft
artifact: "tests/unit/test_tst_0098.py"
---

# Test: PWA Projects Schema

> **Contract:** CON-0088 · **Typ:** Contract-Test · **Status:** draft

## Abgedeckte Garantien

- CON-0088 G-01: token von rotate-token ist 64 Hex-Zeichen
- CON-0088 G-04: url in qr-payload = baseUrl für Project
- CON-0088 G-05: name in qr-payload = name für Project
- CON-0088 G-06: server-info tokenHash ist nie der rohe Token
- CON-0088 G-07: Jede Rotation erzeugt einzigartigen Token (blacklist verhindert Wiederholung)
- CON-0088 G-03: sdd-Version 1 im QR-Payload
