---
id: TST-0232
title: "Task-Schema-Erweiterung: fr_ids und allowed_paths"
level: unit
spec: SPEC-0053
contract: CON-0203
status: planned
framework: pytest
artifact: "tests/unit/test_con_0203.py"
tags: [pipeline, roles]
---

# Test: Task-Schema-Erweiterung: fr_ids und allowed_paths

> **Level:** unit · **Spec:** SPEC-0053 · **Contract:** CON-0203 · **Status:** planned

## Was wird geprüft?

Erweiterung des Task-Schemas um `fr_ids` und `allowed_paths`.

Schematests prüfen das Contract-Artefakt und laufen sofort. Verhaltenstests laufen gegen die echte
CLI mit einem OpenAI-kompatiblen Fake-Server und werden mit `requires_pipeline_cli` übersprungen,
bis `sdd pipeline` existiert.

## Vorbedingungen

- Schema-Artefakte von CON-0203 und CON-0096.

## Ablauf

1. Erweiterung allein prüfen.
2. Vollständige Task-Instanz gegen beide Schemas prüfen (übersprungen bis `sdd pipeline` existiert).

## Erwartetes Ergebnis

- code-Tasks mit leerer FR-Liste werden abgelehnt.
- Eine vollständige Task-Instanz mit den neuen Feldern erfüllt CON-0096 und CON-0203.

## Verknüpfung mit Contract

- [x] INV-01
- [x] INV-03

## Verknüpfung mit Spec

FR-05
