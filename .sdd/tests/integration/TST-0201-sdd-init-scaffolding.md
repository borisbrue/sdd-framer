---
id: TST-0201
project: PRJ-0001
title: "`sdd init` integriert Skill-Dateien-Check und GitHub-Actions-Rückfrage"
level: integration
spec: SPEC-0044
contract: CON-0169
status: draft
framework: pytest
artifact: "tests/integration/test_tst_0197.py"
tags:
  - cli
  - cleanup
---

# Test: `sdd init` Scaffolding-Integration

> **Level:** integration · **Spec:** SPEC-0044 · **Contract:** CON-0169

## Was wird geprüft?

Prüft dass `sdd new agents-md` und `sdd new github-workflow` nicht mehr
als öffentliche Befehle verfügbar sind, und `sdd upgrade --help` ohne Fehler
antwortet (Nachrüst-Logik vorhanden).

## Vorbedingungen

- `sdd` CLI im PATH nach Implementierung von SPEC-0044

## Ablauf

1. `sdd new agents-md` → Exit ≠ 0 + Hinweis auf `sdd init`
2. `sdd new github-workflow` → Exit ≠ 0 + Hinweis auf `sdd init`
3. `sdd upgrade --help` → Exit 0

## Verknüpfung mit Contract

- [x] `sdd new agents-md` nicht mehr öffentlich
- [x] `sdd new github-workflow` nicht mehr öffentlich
- [x] `sdd upgrade` enthält Nachrüst-Logik
