---
id: SPEC-0002
title: "SDD VS Code Extension"
project: PRJ-0001
status: implemented
owner: "Boris"
created: 2026-05-11
updated: 2026-05-12
version: 1.0.0
priority: high
tags: [tooling, vscode, developer-experience]
depends_on: []
contracts: [CON-0004, CON-0005, CON-0006]
tests: [TST-0005, TST-0006, TST-0007]
adrs: []
---

# SDD VS Code Extension

> **Status:** approved · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Die `sdd`-CLI ist das Herzstück des Spec-Driven Development Blueprints. Entwickler
verlassen aber selten ihr IDE. Die Extension bringt SDD direkt in VS Code: Specs
anlegen, Verknüpfungen prüfen und die Traceability-Matrix einsehen – ohne Terminal.

Die Extension ruft die CLI intern per Subprozess auf. Keine Doppellogik.

## 2. Zielsetzung

**Primärziel:** Entwickler können SDD-Dokumente direkt in VS Code anlegen, navigieren
und validieren, ohne die `sdd`-CLI manuell aufrufen zu müssen.

**Erfolgskriterien (messbar):**
- [ ] Sidebar zeigt alle Specs/Contracts/Tests mit Statusfarben innerhalb 500ms nach Öffnen
- [ ] "Go to Definition" auf eine ID öffnet die referenzierte Datei in < 100ms
- [ ] `sdd validate` läuft bei jedem Speichern und zeigt Fehler als Diagnostics im Problems-Panel
- [ ] Alle 5 Befehle aus der Befehlspalette funktionieren ohne Fehler

**Nicht-Ziele:**
- Kein eigener Language Server (LSP) – Frontmatter-Linting per einfacher Regex
- Keine Web-UI / WebView für die TreeView
- Keine eigene Datenbank – alles wird aus den Markdown-Dateien gelesen

## 3. User Stories

| ID    | Als ...         | möchte ich ...                                          | um ...                                      |
|-------|-----------------|---------------------------------------------------------|---------------------------------------------|
| US-01 | Entwickler      | eine neue Spec per Befehlspalette anlegen               | nicht ins Terminal wechseln zu müssen       |
| US-02 | Entwickler      | auf eine Spec-ID klicken und die Datei öffnen           | schnell zwischen Spec/Contract/Test springen|
| US-03 | Entwickler      | beim Speichern sofort Validierungsfehler sehen          | Verknüpfungsfehler früh zu bemerken         |
| US-04 | Entwickler      | die Traceability-Matrix in der Sidebar sehen            | den Überblick über Lücken zu behalten       |
| US-05 | Entwickler      | Code Lens über Specs sehen ("2 contracts · 3 tests")    | Coverage auf einen Blick zu erkennen        |

## 4. Funktionale Anforderungen

- **FR-01:** TreeView in der Activity Bar listet alle Specs gruppiert nach Status
- **FR-02:** Jede Spec-Node ist aufklappbar und zeigt ihre Contracts und Tests als Kinder
- **FR-03:** Klick auf eine Node öffnet die referenzierte Datei
- **FR-04:** Befehlspalette bietet: `SDD: New Spec`, `SDD: New Contract`, `SDD: New Test`, `SDD: New ADR`, `SDD: Validate`, `SDD: Update Trace Matrix`
- **FR-05:** Bei jedem Speichern einer `.md`-Datei im SDD-Projekt wird `sdd validate` im Hintergrund ausgeführt
- **FR-06:** Validierungsfehler erscheinen als VS Code Diagnostics (Problems-Panel + rote Unterstreichung)
- **FR-07:** Code Lens über jeder Spec-Überschrift zeigt Anzahl der Contracts und Tests
- **FR-08:** Hover über eine ID (z.B. `CON-0001`) zeigt Title und Status der referenzierten Datei

## 5. Nicht-funktionale Anforderungen

| Kategorie   | Anforderung                                                          |
|-------------|----------------------------------------------------------------------|
| Performance | TreeView-Aufbau < 500ms; Validierung nach Save < 2s                  |
| Kompatibilität | VS Code >= 1.85; keine Abhängigkeit auf Python-Pfad (sdd via Einstellung konfigurierbar) |
| Konfiguration | sdd-Pfad, automatische Validierung on/off, TreeView refresh interval |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: SDD VS Code Extension

  Scenario: Neue Spec per Befehlspalette anlegen
    Given ein SDD-Projekt ist im Workspace geöffnet
    When der Nutzer "SDD: New Spec" aus der Befehlspalette wählt
    And einen Titel eingibt
    Then wird eine neue Spec-Datei mit korrektem Frontmatter angelegt
    And die TreeView aktualisiert sich

  Scenario: Validierungsfehler werden angezeigt
    Given eine Spec ohne Contract existiert
    When der Nutzer die Spec speichert
    Then erscheint ein Fehler im Problems-Panel
    And die betroffene Zeile ist rot unterstrichen

  Scenario: Navigation per Go to Definition
    Given eine Spec referenziert CON-0001
    When der Nutzer F12 auf "CON-0001" drückt
    Then öffnet VS Code die Datei contracts/api/CON-0001-*.md
```

## 7. Edge Cases & Fehlerfälle

- `sdd` nicht im PATH / nicht konfiguriert → Fehlermeldung mit Link zu Installationsanleitung
- Kein `.sdd/config.yaml` im Workspace → Extension bleibt inaktiv, zeigt Hinweis
- Mehrere Workspace-Ordner → nur der mit `.sdd/` wird aktiviert

## 8. Contracts

| Contract-ID | Typ      | Was wird garantiert?                              |
|-------------|----------|---------------------------------------------------|
| CON-0004    | behavior | Gherkin-Szenarien für alle Befehle                |
| CON-0005    | data     | JSON Schema für Extension-Einstellungen           |
| CON-0006    | behavior | UI-Verhalten: TreeView, Diagnostics, Code Lens    |

## 9. Tests

| Test-ID  | Level      | Was prüft der Test?                              |
|----------|------------|--------------------------------------------------|
| TST-0005 | acceptance | Gherkin-Szenarien der Befehle (CON-0004)         |
| TST-0006 | unit       | Konfigurationsschema-Validierung (CON-0005)      |
| TST-0007 | acceptance | UI-Verhalten in VS Code Extension Host (CON-0006)|

## 10. Änderungshistorie

| Datum      | Version | Autor   | Änderung            |
|------------|---------|---------|---------------------|
| 2026-05-11 | 0.1.0   | Boris   | Initiale Erstellung |
