---
id: TST-0113
project: PRJ-0001
title: "Extension Flow – Gherkin-Szenarien Server-Management & Pipeline-Execute"
level: acceptance
spec: SPEC-0017
contract: CON-0054
contracts: ["CON-0054", "CON-0055"]
status: planned
framework: vscode-extension-tester
artifact: "vscode-extension/test/extension.test.ts"
tags: ["vscode", "acceptance", "gherkin", "server", "pipeline"]
---

# Acceptance Test: Extension Flow – Server-Management & Pipeline-Execute

> **Level:** acceptance · **Spec:** SPEC-0017 · **Contracts:** CON-0054, CON-0055 · **Status:** planned

## Was wird geprüft?

Die Gherkin-Szenarien aus CON-0054 und CON-0055 im echten Extension-Host:

- Server startet auf freiem Port, Status Bar zeigt `SDD ⚡ :<PORT>`
- Server stoppt sauber, kein Zombie-Prozess
- `Execute Current Spec` prüft `approved`-Status vor API-Call
- Workspace-Close ruft `dispose()` auf

## Szenarien (aus CON-0054 + CON-0055)

### SC-01: Server auf freiem Port starten (CON-0054)

```gherkin
Given kein SDD-Server läuft
And sdd.webUi.port ist auf 0 gesetzt
When der Nutzer "SDD: Start Web UI" ausführt
Then startet ein uvicorn-Prozess auf einem freien Port > 1024
And das Status Bar Item zeigt "SDD ⚡ :<PORT>"
And Output Channel zeigt "Server gestartet auf Port <PORT>"
```

### SC-02: Server-Stop ohne Zombie (CON-0054)

```gherkin
Given ein Server läuft auf einem freien Port
When der Nutzer "SDD: Stop Web UI" ausführt
Then wird der Prozess innerhalb von 3 s beendet
And das Status Bar Item zeigt "SDD ○"
```

### SC-03: Execute Current Spec – nicht approved (CON-0055)

```gherkin
Given die aktuelle Datei ist eine Spec mit status: draft
When der Nutzer "SDD: Execute Current Spec" ausführt
Then erscheint eine Warning Message mit "hat Status 'draft'"
And kein POST /api/orchestrate wird gesendet
```

### SC-04: Execute Current Spec – Server gestoppt (CON-0055)

```gherkin
Given die aktuelle Datei ist eine approved Spec
And der SDD-Server ist gestoppt
When der Nutzer "SDD: Execute Current Spec" ausführt
Then erscheint eine Information Message "SDD-Server läuft nicht. Jetzt starten?"
```

### SC-05: Workspace-Cleanup (CON-0054)

```gherkin
Given ein Server läuft
When VS Code den Workspace schließt (deactivate-Hook)
Then wird ServerManager.dispose() aufgerufen
And der Server-Prozess ist beendet
```

## Ablauf

1. Extension in isoliertem VS Code Extension Host starten
2. Test-SDD-Projekt als Workspace öffnen
3. Jeden Gherkin-Szenario sequenziell ausführen
4. Mock für uvicorn-Prozess und HTTP-Calls verwenden

## Hinweis zur Infrastruktur

Da der Extension-Host-Test-Setup (VS Code Extension Tester / `@vscode/test-electron`)
noch nicht konfiguriert ist, wird TST-0113 initial als **manueller Smoke-Test** durchgeführt
und erst nach Einrichtung des Test-Frameworks automatisiert.

## Erwartetes Ergebnis

Alle 5 Szenarien bestehen im Extension-Host ohne Regression in bestehenden Extension-Commands.
