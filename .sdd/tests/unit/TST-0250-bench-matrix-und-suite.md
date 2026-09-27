---
id: TST-0250
title: "Bench-Matrix und Suite"
level: unit
spec: SPEC-0056
contract: CON-0221
status: planned
framework: pytest
artifact: "tests/unit/test_con_0221.py"
tags: [bench]
---

# Test: Bench-Matrix und Suite

> **Level:** unit · **Spec:** SPEC-0056 · **Contract:** CON-0221 · **Status:** planned

## Was wird geprüft?

Schema von Matrix und Suite, Matrix-Expansion (Varianten, `*`, Sweep), Fehlerfälle.

## Vorbedingungen

- Temporäres Projekt über `sdd init`; Rollen gegen den Fake-LLM-Server, kein Netzwerk.

## Verknüpfung mit Contract

Alle Invarianten und Szenarien aus CON-0221.
