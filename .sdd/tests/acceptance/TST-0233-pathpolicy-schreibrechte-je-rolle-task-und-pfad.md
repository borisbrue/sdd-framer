---
id: TST-0233
title: "PathPolicy: Schreibrechte je Rolle, Task und Pfad"
level: acceptance
spec: SPEC-0053
contract: CON-0204
status: planned
framework: pytest
artifact: "tests/acceptance/test_con_0204.py"
tags: [pipeline, roles]
---

# Test: PathPolicy: Schreibrechte je Rolle, Task und Pfad

> **Level:** acceptance · **Spec:** SPEC-0053 · **Contract:** CON-0204 · **Status:** planned

## Was wird geprüft?

Alle 13 Szenarien der PathPolicy.

Schematests prüfen das Contract-Artefakt und laufen sofort. Verhaltenstests laufen gegen die echte
CLI mit einem OpenAI-kompatiblen Fake-Server und werden mit `requires_pipeline_cli` übersprungen,
bis `sdd pipeline` existiert.

## Vorbedingungen

- `sdd_cli.pipeline.path_policy.PathPolicy(root, protected_paths).check(role, path, task)` liefert ein Objekt mit `allowed` und `reason`.
- Für tc09: Fake-Server `tests/support/fake_llm.py`.

## Ablauf

1. Regeln direkt über `PathPolicy.check` prüfen.
2. tc09: Pipeline-Lauf, in dem der implementer außerhalb von `allowed_paths` schreibt.

## Erwartetes Ergebnis

- Gründe wörtlich wie in der Regeltabelle von CON-0204.
- Abgelehnte Schreibvorgänge erscheinen als `write_rejected`, die Datei fehlt, der Aufruf hat `gate_failed`.
- `check` hat keinen Provider-Parameter.

## Verknüpfung mit Contract

- [x] INV-01
- [x] INV-02
- [x] INV-03
- [x] INV-05

## Verknüpfung mit Spec

FR-07, FR-09
