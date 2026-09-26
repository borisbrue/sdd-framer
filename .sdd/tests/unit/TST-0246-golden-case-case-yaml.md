---
id: TST-0246
title: "Golden Case case.yaml"
level: unit
spec: SPEC-0055
contract: CON-0217
status: planned
framework: pytest
artifact: "tests/unit/test_con_0217.py"
tags: [evals]
---

# Test: Golden Case case.yaml

> **Level:** unit · **Spec:** SPEC-0055 · **Contract:** CON-0217 · **Status:** planned

## Was wird geprüft?

Schema von `case.yaml`: gültige und ungültige Beispiele, Ort bestimmt Holdout, Pflicht von `test_command` und Fall-Bestandteilen, Score-Formel, Entwurfsfälle; alle Blueprint-Fälle sind gültig.

## Vorbedingungen

- Temporäres Projekt über `sdd init`; Rollen und Judge gegen den Fake-LLM-Server.
- Kein echter `claude`-Aufruf, kein Netzwerk.

## Verknüpfung mit Contract

Alle Invarianten und Szenarien aus CON-0217.
