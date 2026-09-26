---
id: TST-0249
title: "Ratchet, Übernahme und Skill sdd-role-tune"
level: acceptance
spec: SPEC-0055
contract: CON-0220
status: planned
framework: pytest
artifact: "tests/acceptance/test_con_0220.py"
tags: [evals]
---

# Test: Ratchet, Übernahme und Skill sdd-role-tune

> **Level:** acceptance · **Spec:** SPEC-0055 · **Contract:** CON-0220 · **Status:** planned

## Was wird geprüft?

Szenarien von CON-0220: compare-Regeln, accept mit Versionierung, Baseline und CHANGELOG, --force, Skill-Text.

## Vorbedingungen

- Temporäres Projekt über `sdd init`; Rollen und Judge gegen den Fake-LLM-Server.
- Kein echter `claude`-Aufruf, kein Netzwerk.

## Verknüpfung mit Contract

Alle Invarianten und Szenarien aus CON-0220.
