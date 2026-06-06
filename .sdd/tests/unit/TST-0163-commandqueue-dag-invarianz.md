---
id: TST-0163
project: ""
title: "CommandQueue apply — DAG-Invarianz bei skip (offene Deps → reject)"
level: unit
spec: SPEC-0037
contract: CON-0142
status: implemented
framework: pytest
artifact: "tests/unit/test_tst_0163.py"
tags: []
---

# Test: CommandQueue — DAG-Invarianz

> **Level:** unit · **Spec:** SPEC-0037 · **Contract:** CON-0142 · **Status:** implemented

## Was wird geprüft?

Ob `CommandQueue.apply()` bei `skip_task` die Abhängigkeitsvalidierung korrekt
durchführt und Tasks mit offenen Deps zurückweist (CON-0142 INV-02).

## Verknüpfung mit Contract

- [x] INV-01: apply ist idempotent
- [x] INV-02: skip_task mit offenen Deps → reject
- [x] INV-03: restart_task nur für failed-Tasks zulässig
- [x] INV-04: Unbekannte Command-Typen → 422
