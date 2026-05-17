---
id: CON-0054
title: "extension-server-management"
type: behavior
format: gherkin
spec: SPEC-0017
version: 0.1.0
status: draft
artifact: "contracts/behavior/extension-server-management.feature"
tests: [TST-0062]
---

# Contract: extension-server-management

> **Spec:** SPEC-0017 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Dieses Contract beschreibt das beobachtbare Verhalten des `ServerManager` und
des `StatusBarItem` bei Start, Stop und Fehlerbehandlung des Web-UI-Servers.
Besonderes Augenmerk liegt auf der dynamischen Port-Ermittlung und dem
sauberen Cleanup beim Schließen des Workspaces.

## Garantien

- **G-01:** `SDD: Start Web UI` startet uvicorn exakt einmal pro Workspace-Session;
  ein zweiter Aufruf zeigt Quick Pick statt zweiten Prozess zu spawnen.
- **G-02:** Bei `sdd.webUi.port == 0` wird der OS-Zufallsport via Python ermittelt;
  der zurückgegebene Port ist immer > 1024 und war zum Zeitpunkt der Ermittlung frei.
- **G-03:** `deactivate()` beendet den Server-Prozess innerhalb von 5 s (SIGTERM + SIGKILL).
- **G-04:** Das Status Bar Item spiegelt exakt den Zustand des `ServerManager` wider
  ohne eigene Zustandshaltung.

## Invarianten

- **INV-01:** Kein Moment, in dem zwei uvicorn-Prozesse gleichzeitig für denselben
  Workspace laufen.
- **INV-02:** Server wird nie auf `0.0.0.0` oder einer externen Adresse gestartet –
  immer `127.0.0.1`.
- **INV-03:** `ServerManager.getPort()` gibt `null` zurück, solange `status != 'running'`.

## Szenarien

```gherkin
Feature: SDD Server Management – Dynamic Port & Lifecycle

  Background:
    Given ein SDD-Projekt ist im VS Code Workspace geöffnet
    And die Extension ist aktiviert

  Scenario: Server mit dynamischem Port starten
    Given sdd.webUi.port ist auf 0 konfiguriert
    And kein SDD-Server läuft
    When der Nutzer "SDD: Start Web UI" aus der Befehlspalette ausführt
    Then wird ein freier Port via Python socket ermittelt
    And uvicorn startet auf diesem Port mit host=127.0.0.1
    And das Status Bar Item wechselt zu "SDD ⚡ :<PORT>" innerhalb von 3 s
    And der Output Channel zeigt "Server gestartet auf Port <PORT>"
    And ServerManager.getStatus() == 'running'

  Scenario: Server mit fixem Port starten
    Given sdd.webUi.port ist auf 9876 konfiguriert
    And Port 9876 ist frei
    When der Nutzer "SDD: Start Web UI" ausführt
    Then startet uvicorn auf Port 9876
    And Status Bar zeigt "SDD ⚡ :9876"

  Scenario: Fixer Port ist belegt
    Given sdd.webUi.port ist auf 8000 konfiguriert
    And Port 8000 wird von einem anderen Prozess verwendet
    When der Nutzer "SDD: Start Web UI" ausführt
    Then erscheint eine Error Message "Port 8000 ist bereits belegt"
    And Status Bar zeigt "SDD ✗"
    And ServerManager.getStatus() == 'error'

  Scenario: Server stoppen
    Given ein Server läuft auf Port 54231
    When der Nutzer "SDD: Stop Web UI" ausführt
    Then erhält der uvicorn-Prozess SIGTERM
    And nach max. 3 s ist der Prozess beendet
    And Port 54231 ist wieder frei
    And Status Bar zeigt "SDD ○"
    And ServerManager.getStatus() == 'stopped'

  Scenario: Doppelter Start-Aufruf
    Given ein Server läuft auf Port 54231
    When der Nutzer "SDD: Start Web UI" nochmals ausführt
    Then erscheint ein Quick Pick mit Optionen: "Neustarten", "Browser öffnen", "Abbrechen"
    And kein zweiter Prozess wird gestartet

  Scenario: Workspace schließen mit laufendem Server
    Given ein Server läuft auf Port 54231
    When VS Code den Workspace schließt und deactivate() aufruft
    Then ruft ServerManager.dispose() auf
    And der Prozess wird beendet (SIGTERM, Fallback SIGKILL nach 3 s)
    And kein Prozess belegt Port 54231 danach

  Scenario: Server-Crash (unerwartet beendet)
    Given ein Server läuft auf Port 54231
    When der uvicorn-Prozess unerwartet mit Exit-Code != 0 endet
    Then wechselt ServerManager.getStatus() zu 'error'
    And Status Bar zeigt "SDD ✗"
    And Output Channel zeigt den letzten stderr-Output

  Scenario: Web UI im Browser öffnen
    Given ein Server läuft auf Port 54231
    When der Nutzer "SDD: Open Web UI" ausführt
    Then öffnet vscode.env.openExternal("http://localhost:54231") den Systembrowser

  Scenario: Open Web UI – Server gestoppt
    Given kein Server läuft
    And sdd.webUi.openBrowser ist true
    When der Nutzer "SDD: Open Web UI" ausführt
    Then erscheint eine Information Message "Server nicht aktiv. Jetzt starten?"
    And bei Bestätigung startet der Server
    And danach öffnet sich der Browser auf dem neuen Port
```

## Begriffe

| Begriff        | Definition                                                              |
|----------------|-------------------------------------------------------------------------|
| uvicorn        | ASGI-Server, der `web.api.main:app` als Subprozess der Extension startet|
| Status Bar     | VS Code-Leiste unten rechts; zeigt Server-Status + Port                 |
| Zufallsport    | Port 0 ans OS delegiert; OS wählt freien Port; Extension liest ihn aus  |
| dispose()      | Methode die beim Extension-Deactivate aufgerufen wird; gibt Ressourcen frei |
