---
id: TST-0074
project: PRJ-0001
title: "Tests: Docker Spec Lifecycle – sdd start / exec / close"
contract: CON-0065
contracts: ["CON-0065"]
spec: SPEC-0021
level: contract
status: draft
artifact: "tests/contract/test_docker_spec_lifecycle.py"
---

# Test: Docker Spec Lifecycle

> **Contract:** CON-0065 · **Typ:** Contract-Test · **Status:** draft

## Abgedeckte Garantien

- CON-0065 G-01: `sdd start` erzeugt Branch + Container atomar
- CON-0065 G-02: Volume-Mount und Env-Variablen korrekt gesetzt
- CON-0065 G-03: Idempotenz – kein zweiter Container bei aktivem Container
- CON-0065 G-04: Gestoppter Container wird wieder gestartet
- CON-0065 G-05: `sdd exec` leitet Output und Exit-Code weiter
- CON-0065 G-06: `sdd close` stoppt und entfernt Container

## Test-Datei

`tests/contract/test_docker_spec_lifecycle.py`

## Testfälle

| ID | Szenario | Erwartetes Ergebnis |
|---|---|---|
| TC-01 | `sdd start` – frischer Zustand | Branch + Container erstellt, Exit 0 |
| TC-02 | `sdd start` – Container läuft bereits | Warnung, kein zweiter Container, Exit 0 |
| TC-03 | `sdd start` – Container gestoppt | Container neu gestartet (kein docker run), Exit 0 |
| TC-04 | `sdd start` – Docker-Fehler | Rollback Branch, Exit != 0 |
| TC-05 | `sdd exec` – Container aktiv | Output + Exit-Code 1:1 weitergeleitet |
| TC-06 | `sdd exec` – Container inaktiv | Fehlermeldung mit Hinweis, Exit != 0 |
| TC-07 | `sdd close` | Container gestoppt + entfernt, Branch erhalten |
| TC-08 | `sdd close --delete-branch` | Container + Branch entfernt |
