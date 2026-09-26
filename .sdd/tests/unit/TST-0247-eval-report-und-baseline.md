---
id: TST-0247
title: "Eval-Report und Baseline"
level: unit
spec: SPEC-0055
contract: CON-0218
status: planned
framework: pytest
artifact: "tests/unit/test_con_0218.py"
tags: [evals]
---

# Test: Eval-Report und Baseline

> **Level:** unit · **Spec:** SPEC-0055 · **Contract:** CON-0218 · **Status:** planned

## Was wird geprüft?

Schema von Report und `baseline.json`, Aggregation (Mittel, Streuung, pass@1, pass^k), Holdout-Aggregat ohne IDs, keine Prompt-Texte und Keys.

## Vorbedingungen

- Temporäres Projekt über `sdd init`; Rollen und Judge gegen den Fake-LLM-Server.
- Kein echter `claude`-Aufruf, kein Netzwerk.

## Verknüpfung mit Contract

Alle Invarianten und Szenarien aus CON-0218.
