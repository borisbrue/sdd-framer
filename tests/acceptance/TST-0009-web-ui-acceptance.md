---
id: TST-0009
title: "web-ui-acceptance"
level: acceptance
spec: SPEC-0003
contract: CON-0008
status: planned
framework: playwright
artifact: "tests/acceptance/test_web_ui_acceptance.py"
tags: [ui, playwright, e2e, gherkin]
---

# Test: web-ui-acceptance

> **Level:** acceptance · **Spec:** SPEC-0003 · **Contract:** CON-0008 · **Status:** planned

## Was wird geprüft?

Die Kernszenarien aus CON-0008 (`web-ui-behavior.feature`) werden gegen die laufende SDD Web UI geprüft. Die Tests verifizieren das beobachtbare Verhalten aus Nutzersicht: Projektnavigation, Spec anlegen, Validierung starten, Maintenance-Sweep auslösen und Autonomy-Level setzen.

## Vorbedingungen

- SDD-Server läuft auf `http://localhost:8000` gegen ein Test-SDD-Projekt
- Playwright installiert (`playwright install chromium`)
- Python-Abhängigkeiten: `pytest-playwright`, `pytest`
- Test-SDD-Projekt enthält: min. 1 Projekt, 2 Specs (eine mit fehlendem `owner`), 1 Contract, 1 Test

## Ablauf

1. Playwright startet Chromium und navigiert zu `http://localhost:8000`
2. Jedes Szenario aus CON-0008 wird als separater Testfall ausgeführt
3. UI-Interaktionen werden über Playwright-Locatoren (ARIA-Rollen, `data-testid`) adressiert
4. HTTP-Aufrufe werden über Playwrights `page.expect_request()` verifiziert

## Erwartetes Ergebnis

- **Sidebar** zeigt Projektliste mit Autonomy-Level-Badge nach Seitenaufruf
- **+ Spec** öffnet Modal, Formular-Submit erstellt Spec und zeigt sie in Sidebar
- **Validierung** ohne Fehler: StatusBar zeigt grünes Häkchen
- **Validierung** mit fehlendem `owner`: Fehlerlist erscheint mit Dateiname + Meldung
- **Maintenance-Sweep**: Issues-Liste mit Severity, Datei und empfohlener Aktion
- **Autonomy-Level ändern**: Badge aktualisiert sofort, `PATCH /api/projects/{id}/level` wird aufgerufen
- **Dark Mode**: Theme-Wechsel sofort sichtbar, bleibt nach F5 erhalten

## Negativfälle / Edge Cases

- Netzwerkfehler (API down): UI zeigt Fehlermeldung statt leerem Zustand
- Ungültige Spec-ID in URL: Hauptbereich zeigt „Nicht gefunden"-Hinweis
- Dark-Mode-Einstellung bleibt nach Browser-Refresh erhalten (localStorage)

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0008:

- [x] G-01: Sidebar lädt Projekte und Specs aus GET /api/projects + /api/specs
- [x] G-02: `+ Spec` / `+ Projekt` rufen POST /api/specs bzw. /api/projects auf
- [x] G-03: SpecDetail zeigt Frontmatter, Body, Contracts und Tests
- [x] G-07: "Validieren" listet Fehler mit Dateiname und Meldung auf
- [x] G-09: "Maintenance" zeigt Issues mit Severity und empfohlener Aktion
- [x] G-10: Autonomy-Level-Badge; Änderung ruft PATCH /api/projects/{id}/level auf
- [x] G-11: Dark/Light-Theme wird in localStorage gespeichert
- [ ] G-04: "Im Editor öffnen" (nur auf Desktop mit VS Code, nicht in CI)
- [ ] G-05/G-06: AI-Panel (erfordert Claude CLI, nicht in CI-Scope)

## Hinweise zur Implementierung

```python
# tests/acceptance/test_web_ui_acceptance.py
import pytest
from playwright.sync_api import Page, expect

BASE = "http://localhost:8000"

def test_sidebar_loads_projects(page: Page):
    page.goto(BASE)
    expect(page.get_by_role("list", name="projects")).not_to_be_empty()

def test_create_spec(page: Page):
    page.goto(BASE)
    page.get_by_text("+ Spec").click()
    page.get_by_label("Titel").fill("Playwright-Test-Spec")
    with page.expect_request("**/api/specs") as req_info:
        page.get_by_role("button", name="Speichern").click()
    assert req_info.value.method == "POST"
    expect(page.get_by_text("Playwright-Test-Spec")).to_be_visible()

def test_validate_shows_errors(page: Page):
    page.goto(BASE)
    page.get_by_role("button", name="Validieren").click()
    # Wenn Fehler vorhanden
    expect(page.get_by_testid("validation-errors")).to_be_visible()

def test_maintenance_sweep(page: Page):
    page.goto(BASE)
    page.get_by_role("button", name="Maintenance").click()
    expect(page.get_by_testid("maintenance-issues")).to_be_visible()

def test_dark_mode_persists(page: Page):
    page.goto(BASE)
    page.get_by_role("button", name="Theme").click()
    page.reload()
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
```

Für CI: SDD-Server per `conftest.py`-Fixture mit `subprocess.Popen` starten und nach Tests beenden.
AI-Tests (`test_ai_*.py`) separat taggen und in CI überspringen: `pytest -m "not ai"`.
