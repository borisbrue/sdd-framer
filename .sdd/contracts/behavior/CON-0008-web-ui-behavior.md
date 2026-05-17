---
id: CON-0008
title: "web-ui-behavior"
type: behavior
format: gherkin
spec: SPEC-0003
version: 0.2.0
status: active
artifact: "contracts/behavior/web-ui-behavior.feature"
tests: [TST-0009]
---

# Contract: web-ui-behavior

> **Spec:** SPEC-0003 · **Typ:** Verhalten (Gherkin) · **Status:** implemented

## Zweck

Dieses Contract beschreibt das beobachtbare Verhalten der SDD Web UI gegenüber dem Benutzer. Es deckt die Kerninteraktionen ab: Projektnavigation, Spec/Contract/Test-Verwaltung, KI-Integration, Validierung und Autonomy-Level-Management.

Das Artifact (`contracts/behavior/web-ui-behavior.feature`) ist ausführbare Spezifikation und Referenz für Acceptance-Tests.

## Garantien

Die im Artifact hinterlegten Szenarien sind **ausführbare Spezifikation**.
Jedes Szenario MUSS durch einen automatisierten Test (behave, Playwright + Cucumber) abgedeckt sein.

| ID    | Garantie                                                                                          |
|-------|---------------------------------------------------------------------------------------------------|
| G-01  | Die Sidebar lädt Projekte und Specs aus `GET /api/projects` + `GET /api/specs`                   |
| G-02  | `+ Spec` / `+ Projekt` öffnen Formulare, die `POST /api/specs` bzw. `POST /api/projects` aufrufen |
| G-03  | SpecDetail zeigt Frontmatter, Body, verknüpfte Contracts und Tests                               |
| G-04  | "Im Editor öffnen" ruft `POST /api/open` mit dem absoluten Dateipfad auf                         |
| G-05  | AiPanel ruft `POST /api/ai/generate-spec` bzw. `/improve-spec` auf und zeigt das Ergebnis        |
| G-06  | AiUsageView liest `GET /api/ai/usage` und zeigt Kosten, Token und Aufschlüsselung nach Operation  |
| G-07  | "Validieren" ruft `POST /api/validate` auf; Fehler werden mit Dateiname und Meldung aufgelistet  |
| G-08  | "Traceability" ruft `POST /api/trace` auf und zeigt Erfolgsmeldung mit Pfad                      |
| G-09  | "Maintenance" ruft `GET /api/maintenance` auf und zeigt Issues mit Severity und empfohlener Aktion |
| G-10  | Autonomy-Level-Badge zeigt das aktuelle Level; Änderung ruft `PATCH /api/projects/{id}/level` auf |
| G-11  | Dark/Light-Theme wird in localStorage gespeichert und nach Refresh wiederhergestellt              |
| G-12  | Breadcrumb-Navigation nutzt die Browser-History (kein Hash-Routing, kein Full-Reload)            |

## Invarianten (über alle Szenarien hinweg)

- **INV-01:** Alle API-Aufrufe gehen gegen denselben Origin (kein separater Backend-Host nötig)
- **INV-02:** Bei HTTP-Fehlern zeigt die UI eine lesbare Fehlermeldung statt einer leeren Seite
- **INV-03:** Dateioperationen schreiben immer ins Dateisystem (kein flüchtiger In-Memory-State)
- **INV-04:** Autonomy Level ist immer einer der Werte 1, 2, 3, 3.5, 4
- **INV-05:** Die Sidebar bleibt nach Navigation sichtbar (2-Spalten-Layout)

## Begriffe

| Begriff           | Definition                                                                 |
|-------------------|----------------------------------------------------------------------------|
| Spec              | Markdown-Dokument mit YAML-Frontmatter im `specs/`-Verzeichnis             |
| Contract          | Markdown-Dokument mit Artifact-Verweis im `contracts/`-Verzeichnis        |
| Autonomy Level    | Numerischer Reifegrad eines Projekts (1–4) gemäß SPEC-0004                |
| StatusBar         | Obere Leiste mit Projektname, Validierungs- und Traceability-Schnellzugriff |
| Sidebar           | Linke Spalte mit Projekt-/Spec-Liste und Schnellzugriff-Buttons           |
| AiPanel           | Seitenbereich für KI-Operationen (generate, improve, suggest)              |
| Maintenance-Sweep | Drift-Erkennung: veraltete Specs, fehlende Contracts/Tests                 |

## Änderungshistorie

| Datum      | Version | Autor | Änderung                                          |
|------------|---------|-------|---------------------------------------------------|
| 2026-05-11 | 0.1.0   | Boris | Initialer Entwurf (Placeholder)                   |
| 2026-05-12 | 0.2.0   | Boris | Vollständige Garantien, Invarianten und Feature-File |
