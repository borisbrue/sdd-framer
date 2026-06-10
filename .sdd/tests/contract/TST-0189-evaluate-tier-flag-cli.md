---
id: TST-0189
title: "sdd evaluate --tier CLI-Flags und Exit-Codes (Contract)"
spec: SPEC-0042
contract: CON-0161
level: contract
artifact: "tests/contract/test_tst_0189.py"
status: draft
---

# Test: sdd evaluate --tier CLI-Interface

> **Contract:** CON-0161 · **Spec:** SPEC-0042 · **Level:** contract

## Testfälle

| TC | Beschreibung                                             | Erwartet             |
|----|----------------------------------------------------------|----------------------|
| 01 | `--tier critical` filtert nur critical-Holdouts          | 1 executed, 2 skipped |
| 02 | `--tier normal` filtert nur normal-Holdouts              | 1 executed, 2 skipped |
| 03 | `--tier edge-case` filtert nur edge-case-Holdouts        | 1 executed, 2 skipped |
| 04 | `--tier critical` ohne Matches → Exit 0 + Meldung        | Exit 0               |
| 05 | `--tier` + `--hol-ids` kombiniert → --hol-ids hat Vorrang + Warning | Warning ausgegeben |
| 06 | `--smoke` ignoriert `--base-url` und `--tier`            | kein HTTP-Aufruf     |
