---
id: TST-0107
project: PRJ-0001
title: "Tests: POST /api/push/subscribe Dedup + 503 ohne VAPID (CON-0076)"
contract: CON-0076
contracts: ["CON-0076"]
spec: SPEC-0023
level: contract
status: draft
artifact: "tests/unit/test_tst_0107.py"
---

# Test: POST /api/push/subscribe

> **Contract:** CON-0076 · **Typ:** Contract-Test · **Status:** draft

## Abgedeckte Garantien

- G-01: Fehlende Auth → HTTP 401
- G-02: Request-Body mit endpoint + keys (p256dh, auth)
- G-03: Gleicher endpoint → Deduplication (kein Duplikat im PushStore)
- G-04: Fehlende VAPID-Keys → HTTP 503 `vapid_not_configured`
- G-05: Erfolgreiche Registrierung → HTTP 201 `{"subscribed": true}`
