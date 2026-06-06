---
id: TST-0167
title: "sdd hub start startet hub/app.py auf Port 4711"
level: contract
spec: SPEC-0039
contract: CON-0144
status: planned
framework: pytest
artifact: "tests/contract/test_tst_0167.py"
tags: []
---

# Test: sdd hub start startet hub/app.py auf Port 4711

## Was wird geprüft?

G-01/G-02/G-03/G-04 aus CON-0144: Nach `sdd hub start` ist der neue Hub
erreichbar (`/hub/projects` → JSON, `/hub/` → HTML); Standardport ist 4711;
`start_hub()` aus `ui.py` wird nicht aufgerufen.

## Vorbedingungen

- Port 4711 frei
- `hub/app.py` vorhanden

## Ablauf

1. `hub_start`-Funktion in `main.py` per Unittest isolieren
2. Prüfen dass `create_app()` aus `hub/app.py` aufgerufen wird
3. Prüfen dass `start_hub()` aus `ui.py` **nicht** aufgerufen wird
4. Integration: Hub via subprocess starten, `GET /hub/projects` → 200 JSON,
   `GET /hub/` → 200 HTML, danach beenden

## Erwartetes Ergebnis

- `create_app` wird aufgerufen ✓
- `start_hub` wird nicht aufgerufen ✓
- `GET http://localhost:4711/hub/projects` → 200, `application/json`
- `GET http://localhost:4711/hub/` → 200, `text/html`

## Negativfälle

- `--port 9876`: Hub antwortet auf 9876, nicht auf 4711

## Verknüpfung mit Contract

- [ ] G-01: `/hub/projects` → 200 JSON
- [ ] G-02: `/hub/` → 200 HTML
- [ ] G-03: Standardport 4711, `--port` überschreibt
- [ ] G-04: `start_hub()` nicht aufgerufen
