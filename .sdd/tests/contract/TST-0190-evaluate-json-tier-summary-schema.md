---
id: TST-0190
title: "sdd evaluate JSON-Output: tier_summary Schema (Contract)"
spec: SPEC-0042
contract: CON-0162
level: contract
artifact: "tests/contract/test_tst_0190.py"
status: draft
---

# Test: Evaluation-Report JSON tier_summary

> **Contract:** CON-0162 · **Spec:** SPEC-0042 · **Level:** contract

## Testfälle

| TC | Beschreibung                                                   | Erwartet                         |
|----|----------------------------------------------------------------|----------------------------------|
| 01 | `--output-json` enthält `tier_summary`-Block                   | Block vorhanden                  |
| 02 | `tier_summary` enthält alle drei Tier-Keys                     | critical, normal, edge-case      |
| 03 | Szenarien enthalten `priority`-Feld                            | "critical"/"normal"/"edge-case"  |
| 04 | Szenarien enthalten `task_delta` (null wenn kein Provider)     | null oder string                 |
| 05 | `tier_summary` Summen-Invariante: passed+failed+skipped = total | arithmetisch korrekt             |
| 06 | Fehlender `priority:` im Holdout-Frontmatter → Fallback "normal" | "normal" im Output              |
