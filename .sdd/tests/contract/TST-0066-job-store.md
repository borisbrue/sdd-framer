---
id: TST-0066
project: PRJ-0001
title: "Tests: JobStore – In-Memory Job-Verwaltung"
contract: CON-0051
contracts: ["CON-0051"]
spec: SPEC-0016
level: contract
status: draft
artifact: "tests/unit/test_job_store.py"
---

# Test: JobStore

> **Contract:** CON-0051 · **Typ:** Contract-Test · **Status:** draft

## Abgedeckte Garantien

- CON-0051: AnalysisJob-Datenstruktur
- JobStore-Interface: create, get, update_*, active_count, cleanup_expired

## Test-Datei

`tests/unit/test_job_store.py`
