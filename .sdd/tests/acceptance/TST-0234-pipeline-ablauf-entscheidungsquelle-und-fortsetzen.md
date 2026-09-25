---
id: TST-0234
title: "Pipeline-Ablauf, Entscheidungsquelle und Fortsetzen"
level: acceptance
spec: SPEC-0053
contract: CON-0205
status: planned
framework: pytest
artifact: "tests/acceptance/test_con_0205.py"
tags: [pipeline, roles]
---

# Test: Pipeline-Ablauf, Entscheidungsquelle und Fortsetzen

> **Level:** acceptance · **Spec:** SPEC-0053 · **Contract:** CON-0205 · **Status:** planned

## Was wird geprüft?

Alle 17 Szenarien des Pipeline-Ablaufs sowie `pipeline report` und der Skill `/sdd-supervise`.

Schematests prüfen das Contract-Artefakt und laufen sofort. Verhaltenstests laufen gegen die echte
CLI mit einem OpenAI-kompatiblen Fake-Server und werden mit `requires_pipeline_cli` übersprungen,
bis `sdd pipeline` existiert.

## Vorbedingungen

- `sdd pipeline` ist implementiert (sonst übersprungen).
- Fake-Server `tests/support/fake_llm.py`; Rollen auf `fake-<rolle>` konfiguriert.
- Testprojekt ohne Python: Shell-Tests, JUnit-Sonde (`tests/support/pipeline_project.py`).

## Ablauf

1. Antworten je Rolle vorbereiten (Funktionen übernehmen die `task_id` aus der Entscheidungsanfrage).
2. `sdd pipeline run|decide|report` über `CliRunner` ausführen.
3. Run-Verzeichnis, Aufrufe am Fake-Server und `token_usage` auswerten.

## Erwartetes Ergebnis

- Exit-Codes 0/1/2/3 laut CON-0205.
- Supervisor nur an S1–S3; revise- und Versuchsgrenzen; Dialogmodus mit `request_id` und Archiv; `--resume` ohne Wiederholung erledigter Tasks.
- Usage-Zeilen mit Rolle, Run, Versuch, Ergebnis und Reasoning-Tokens.

## Verknüpfung mit Contract

- [x] INV-01
- [x] INV-02
- [x] INV-03
- [x] INV-04
- [x] INV-05
- [x] INV-06
- [x] INV-07
- [x] INV-08

## Verknüpfung mit Spec

FR-04, FR-05, FR-06, FR-08, FR-10, FR-11, FR-12, FR-13, FR-14, FR-15, FR-16
