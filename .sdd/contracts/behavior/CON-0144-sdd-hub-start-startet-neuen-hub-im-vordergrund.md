---
id: CON-0144
project: ""
title: "sdd hub start startet hub/app.py im Vordergrund auf Port 4711"
type: behavior
format: gherkin
spec: SPEC-0039
version: 0.1.0
status: approved
artifact: ".sdd/contracts/behavior/sdd-hub-start-startet-neuen-hub-im-vordergrund.feature"
tests: ["TST-0167"]
---

# Contract: sdd hub start startet hub/app.py im Vordergrund auf Port 4711

> **Spec:** SPEC-0039 · **Typ:** Verhalten · **Status:** draft

## Zweck

`sdd hub start` startet die neue Hub-Implementierung (`hub/app.py`) als
Vordergrundprozess. Der Prozess blockiert bis Strg+C. Die Endpunkte
`/hub/projects`, `/hub/projects/{id}/start`, `/hub/projects/stream`
und `/hub/` sind identisch zu denen des systemd-Daemons.

## Garantien

- **G-01:** Nach `sdd hub start` antwortet `GET /hub/projects` mit HTTP 200
  und einer JSON-Liste.
- **G-02:** `GET /hub/` liefert HTTP 200 mit `Content-Type: text/html`.
- **G-03:** Der Standardport ist 4711; `--port` überschreibt ihn.
- **G-04:** `sdd hub start` ruft nicht mehr `start_hub()` aus `ui.py` auf;
  die alte Web-API (`web/api/main.py`) wird nicht gestartet.

## Invarianten

- **INV-01:** Der Hub-Prozess ist ein Kind des aufrufenden Terminals —
  er stirbt wenn das Terminal geschlossen wird (kein Detach).
- **INV-02:** `hub/app.py` ist die einzige gestartete ASGI-Applikation.
