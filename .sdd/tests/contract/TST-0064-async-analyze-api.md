---
id: TST-0064
project: PRJ-0001
title: "Tests: Async Analyze API + Job Lifecycle"
contract: CON-0049
contracts: ["CON-0049", "CON-0052"]
spec: SPEC-0016
level: contract
status: draft
artifact: "tests/unit/test_analyze_async.py"
---

# Test: Async Analyze API + Job Lifecycle

> **Contract:** CON-0049, CON-0052 · **Typ:** Contract-Test · **Status:** draft

## Abgedeckte Garantien

- CON-0049 G-01: POST /analyze/start → 202 + job_id
- CON-0049 G-02: GET /analyze/status/{job_id}
- CON-0049 G-03: GET /analyses (listing)
- CON-0049 G-04: GET /analyses/{result_id}
- CON-0049 G-05: PATCH /dismiss
- CON-0052: Job-Lifecycle (queued → complete/failed, TTL, concurrent-limit)

## Test-Datei

`tests/unit/test_analyze_async.py`
