---
id: CON-0145
project: ""
title: "sdd hub start gibt Warnung aus wenn Standardport belegt ist"
type: behavior
format: gherkin
spec: SPEC-0039
version: 0.1.0
status: approved
artifact: ".sdd/contracts/behavior/sdd-hub-start-warnt-bei-belegtem-port.feature"
tests: []
---

# Contract: sdd hub start gibt Warnung aus wenn Standardport belegt ist

> **Spec:** SPEC-0039 · **Typ:** Verhalten · **Status:** draft

## Zweck

Ist der Hub-Port (Standard: 4711) bereits belegt, gibt `sdd hub start`
eine lesbare Warnung aus — bricht aber nicht ab. Der Nutzer kann mit
`--port` einen anderen Port wählen oder den Konflikt selbst auflösen.

## Garantien

- **G-01:** Ist Port 4711 vor dem Start belegt, erscheint eine Warnung
  im Terminal (z.B. `[WARN] Port 4711 belegt — ggf. läuft der Hub-Daemon bereits`).
- **G-02:** Das Programm bricht bei belegtem Port **nicht** mit Exit-Code ≠ 0 ab;
  uvicorn meldet den Bind-Fehler selbst und beendet sich danach sauber.
- **G-03:** Ist der Port frei, erscheint keine Warnung.

## Invarianten

- **INV-01:** Die Warnung erscheint **vor** dem uvicorn-Start, nicht danach.
- **INV-02:** Die Warnung enthält den konkreten Port-Wert.
