---
id: TST-0074
project: PRJ-0001
title: "Tests: Docker Spec Lifecycle – sdd start / Finalisierung"
contract: CON-0065
contracts: ["CON-0065"]
spec: SPEC-0021
level: contract
status: draft
artifact: "tests/unit/test_tst_0074.py"
---

# Test: Docker Spec Lifecycle

> **Contract:** CON-0065 (v0.4.0) · **Typ:** Contract-Test · **Status:** draft

## Abgedeckte Garantien

- CON-0065 G-01: `sdd start` erzeugt Branch + Container atomar
- CON-0065 G-02: Volume-Mount und Env-Variablen korrekt gesetzt
- CON-0065 G-03: Idempotenz – kein zweiter Container bei aktivem Container
- CON-0065 G-04: Gestoppter Container wird wieder gestartet
- CON-0065 G-06: Die Finalisierung entfernt den Container nach grünen Tests und
  lässt ihn nach roten stehen; der Branch bleibt

G-05 ist mit v0.4.0 entfallen (#121). TC-05/06 (`sdd dev exec`) und TC-08
(`--delete-branch`) prüften Code, den nur noch diese Tests erreichten; sie sind
mit ihm entfernt.

## Test-Dateien

- `tests/unit/test_tst_0074.py` — `DevContainerManager.start()` und `close()`
- `tests/unit/test_finalize_container.py` — wann die Finalisierung `close()` aufruft

## Testfälle

| ID | Szenario | Erwartetes Ergebnis |
|---|---|---|
| TC-01 | `sdd start` – frischer Zustand | Branch + Container erstellt, Exit 0 |
| TC-02 | `sdd start` – Container läuft bereits | Warnung, kein zweiter Container, Exit 0 |
| TC-03 | `sdd start` – Container gestoppt | Container neu gestartet (kein docker run), Exit 0 |
| TC-04 | `sdd start` – Docker-Fehler | Rollback Branch, Exit != 0 |
| TC-07 | `close()` | Container gestoppt + entfernt, Branch erhalten |
| TC-09 | Finalisierung, Tests grün | `close()` wird aufgerufen |
| TC-10 | Finalisierung, Tests rot | `close()` wird nicht aufgerufen, Container bleibt |
| TC-11 | Finalisierung mit `docker.compose_file` | Stack bleibt unberührt |
