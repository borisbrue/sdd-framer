---
id: TST-0238
title: "Architekturprüfung für sdd-framer und Pre-Commit-Hook"
level: acceptance
spec: SPEC-0059
contract: CON-0209
status: planned
framework: pytest
artifact: "tests/acceptance/test_con_0209.py"
tags: [architecture, dogfooding]
---

# Test: Architekturprüfung für sdd-framer und Pre-Commit-Hook

> **Level:** acceptance · **Spec:** SPEC-0059 · **Contract:** CON-0209 · **Status:** planned

## Was wird geprüft?

`sdd arch check` auf dem Repo-Stand und auf einer Kopie mit eingebautem Verstoß; Pre-Commit-Hook in einem temporären Git-Projekt.

## Verknüpfung mit Contract

- [x] INV-01
- [x] INV-02
- [x] INV-03
- [x] INV-04
- [x] INV-05
- [x] INV-06

## Verknüpfung mit Spec

FR-01, FR-02, FR-03, FR-04, FR-05, FR-06, FR-08
