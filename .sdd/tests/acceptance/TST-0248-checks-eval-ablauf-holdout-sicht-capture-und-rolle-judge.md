---
id: TST-0248
title: "Checks, Eval-Ablauf, Holdout-Sicht, capture und Rolle judge"
level: acceptance
spec: SPEC-0055
contract: CON-0219
status: planned
framework: pytest
artifact: "tests/acceptance/test_con_0219.py"
tags: [evals]
---

# Test: Checks, Eval-Ablauf, Holdout-Sicht, capture und Rolle judge

> **Level:** acceptance · **Spec:** SPEC-0055 · **Contract:** CON-0219 · **Status:** planned

## Was wird geprüft?

Szenarien von CON-0219: jeder Check mit Positiv- und Negativfall, Eval-Ablauf mit Isolation, Holdout-Sicht und Scanner, capture, Judge blind und in `sdd quality --judge`.

## Vorbedingungen

- Temporäres Projekt über `sdd init`; Rollen und Judge gegen den Fake-LLM-Server.
- Kein echter `claude`-Aufruf, kein Netzwerk.

## Verknüpfung mit Contract

Alle Invarianten und Szenarien aus CON-0219.
