---
id: CON-0146
project: ""
title: "sdd hub run ist als hidden markiert und erscheint nicht in sdd hub --help"
type: behavior
format: gherkin
spec: SPEC-0039
version: 0.1.0
status: approved
artifact: ".sdd/contracts/behavior/sdd-hub-run-ist-hidden.feature"
tests: ["TST-0169"]
---

# Contract: sdd hub run ist als hidden markiert und erscheint nicht in sdd hub --help

> **Spec:** SPEC-0039 · **Typ:** Verhalten · **Status:** draft

## Zweck

`sdd hub run` ist der interne Befehl für den systemd-ExecStart. Er soll
für Endnutzer unsichtbar sein, aber weiterhin funktionieren wenn er
direkt aufgerufen wird (z.B. durch systemd oder in Tests).

## Garantien

- **G-01:** `sdd hub --help` listet `run` **nicht** in der Befehlsübersicht auf.
- **G-02:** `sdd hub run --help` funktioniert weiterhin und zeigt die
  Optionen (Port, Help) — der Befehl ist hidden, nicht entfernt.
- **G-03:** `sdd hub run --port 4711` startet `hub/app.py` identisch
  zu `sdd hub start --port 4711`.

## Invarianten

- **INV-01:** Hidden-Flag ist in Click gesetzt (`hidden=True`), nicht
  durch Entfernen des Befehls realisiert.
