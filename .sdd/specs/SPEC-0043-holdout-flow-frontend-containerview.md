---
id: SPEC-0043
title: Holdout-Flow im Frontend ContainerView sichtbar machen
type: feature
status: implemented
owner: Boris
created: 2026-06-09
updated: '2026-06-09'
version: 0.2.0
priority: medium
tags:
- frontend
- holdout
- ux
depends_on:
- SPEC-0042
- SPEC-0003
- SPEC-0006
- SPEC-0007
contracts:
- CON-0159
- CON-0160
tests:
- TST-0185
- TST-0186
- TST-0187
fr_test_map:
  FR-01:
  - TST-0185
  - TST-0187
  FR-02:
  - TST-0186
  FR-03:
  - TST-0186
  FR-04:
  - TST-0185
  FR-05:
  - TST-0186
adrs: []
started_at: '2026-06-09T13:15:43Z'
---
# Holdout-Flow im Frontend ContainerView sichtbar machen

> **Status:** draft · **Owner:** Boris · **Version:** 0.2.0

## 1. Kontext & Motivation

Als Entwickler sehe ich im SDD Hub nicht, ob ein Holdout läuft, abgebrochen wurde oder bestanden hat – es gibt keine visuelle Rückmeldung in den ContainerViews. Der Holdout-Runner (SPEC-0042) liefert bereits Backend-Ergebnisse, diese sind aber im UI nicht sichtbar. Betroffen: Entwickler (Boris / Team) und optional CI/CD-Pipelines, die den Status programmatisch auslesen.

## 2. Zielsetzung

**Primärziel:**
Den Holdout-Status (running / passed / failed) pro ContainerView sichtbar machen, sodass Entwickler ohne Terminal-Zugriff den Evaluierungsfortschritt verfolgen können.

**Erfolgskriterien (messbar):**
- [ ] Jeder ContainerView zeigt einen Status-Badge (running / passed / failed) für den zugehörigen Holdout-Lauf
- [ ] Der Badge aktualisiert sich ohne Seiten-Reload via SSE (EventSource)
- [ ] Bei Status `failed` sind die fehlgeschlagenen Szenarien als Detail-Liste im ContainerView sichtbar

**Nicht-Ziele (explizit):**
- Keinen neuen Holdout aus dem Frontend starten
- Keine Konfiguration der Holdout-Parameter im UI
- Kein E-Mail / Notification-Versand bei Status-Änderung

## 3. User Stories

| ID    | Als ...      | möchte ich ...                                    | um ...                                          |
|-------|--------------|---------------------------------------------------|-------------------------------------------------|
| US-01 | Entwickler   | den Holdout-Status im ContainerView sehen         | sofort zu wissen, ob eine Evaluierung läuft     |
| US-02 | Entwickler   | fehlgeschlagene Szenarien direkt im UI lesen      | ohne Terminal den Fehlergrund zu verstehen      |
| US-03 | CI/CD        | den Status per API abfragen                       | Build-Entscheidungen automatisch treffen        |

## 4. Funktionale Anforderungen

- **FR-01:** Das Frontend abonniert den Holdout-Status über den SSE-Endpunkt `GET /api/holdouts/{spec_id}/stream` (`EventSource`) – erweitert die bestehende SSE-Infrastruktur aus SPEC-0007 (`orchestrate/stream`), ohne einen zweiten unabhängigen Kanal aufzubauen.
- **FR-02:** Jeder ContainerView zeigt einen Status-Badge für den aktuellen Holdout-Lauf (running / passed / failed / none) – die Badge-Komponente aus SPEC-0006 (Test-Run-Status) wird wiederverwendet oder erweitert.
- **FR-03:** Bei Status `failed` werden die fehlgeschlagenen Szenarien als aufklappbare Detail-Liste im ContainerView angezeigt – die Detail-Listenkomponente aus SPEC-0006 (fehlgeschlagene Tests) wird wiederverwendet oder erweitert.
- **FR-04:** Es existiert ein REST-Endpunkt `GET /api/holdouts/{spec_id}` (Pfad-Segment gemäß Konvention aus SPEC-0003), der Status, Zeitstempel und Szenario-Details des neuesten Laufs zurückgibt.
- **FR-05:** Die Status-Anzeige ist rein lesend – keine Trigger- oder Konfigurations-Aktionen sind im UI möglich.

## 5. Nicht-funktionale Anforderungen

| Kategorie     | Anforderung                                              |
|---------------|----------------------------------------------------------|
| Performance   | SSE-Events innerhalb 1 s nach Status-Änderung, API p95 < 200 ms |
| Accessibility | Badge-Farben mit Text-Label (nicht nur Farbe allein)     |
| Observability | API-Endpunkt loggt Status-Abfragen mit Trace-ID          |

## 6. Architektur & Design Patterns

### Observer Pattern
**Begründung:** ContainerView-Komponenten abonnieren Holdout-Status-Updates. Sobald das Backend einen neuen Status liefert, werden alle registrierten Views automatisch benachrichtigt — ohne sie untereinander zu koppeln.
[Refactoring Guru – Observer](https://refactoring.guru/design-patterns/observer)

### Strategy Pattern
**Begründung:** Die Update-Strategie ist hinter einer `StatusFetcher`-Schnittstelle abstrahiert. Implementierung: SSE (`EventSource`) – konsistent mit `orchestrate/stream` und `pipeline/log` im Projekt. Ein Austausch gegen WebSocket wäre ohne Änderung an den Konsumenten möglich.
[Refactoring Guru – Strategy](https://refactoring.guru/design-patterns/strategy)

### Decorator Pattern
**Begründung:** Bestehende ContainerView-Komponenten werden mit einem Status-Badge-Decorator erweitert, ohne die Basis-Komponente zu verändern. Ermöglicht unabhängige Weiterentwicklung beider Teile.
[Refactoring Guru – Decorator](https://refactoring.guru/design-patterns/decorator)

## 7. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Holdout-Status im ContainerView

  Scenario: Laufender Holdout wird angezeigt
    Given ein Holdout-Lauf für SPEC-0042 ist aktiv
    When der Entwickler den ContainerView öffnet
    Then zeigt der Badge den Status "running"
    And der Badge aktualisiert sich automatisch

  Scenario: Bestandener Holdout
    Given ein Holdout-Lauf hat alle Szenarien bestanden
    When der Entwickler den ContainerView öffnet
    Then zeigt der Badge den Status "passed"

  Scenario: Fehlgeschlagener Holdout mit Szenario-Details
    Given ein Holdout-Lauf hat Szenario "Login" nicht bestanden
    When der Entwickler den ContainerView öffnet
    Then zeigt der Badge den Status "failed"
    And die Detail-Liste enthält "Login"

  Scenario: Kein Holdout vorhanden
    Given kein Holdout-Lauf existiert für diesen Container
    When der Entwickler den ContainerView öffnet
    Then zeigt der Badge keinen Status (neutral / leer)
```

## 8. Edge Cases & Fehlerfälle

- Holdout-API nicht erreichbar → Badge zeigt "unknown", SSE-Reconnect mit Backoff
- Holdout läuft länger als erwartet → "running"-Badge bleibt sichtbar, kein Timeout im Frontend
- Mehrere Holdout-Läufe für denselben Container → nur der neueste wird angezeigt

## 9. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert?                                   |
|-------------|----------|--------------------------------------------------------|
| CON-0159    | api      | GET /api/holdouts/{spec_id} Response-Schema (Status + Szenarien) |
| CON-0160    | behavior | Gherkin-Szenarien aus Sektion 7                        |

## 10. Tests (wie wird verifiziert)

| Test-ID  | Level      | Was prüft der Test?                              |
|----------|------------|--------------------------------------------------|
| TST-0185 | contract   | API-Schema CON-0159 (GET /api/holdouts/{spec_id}, SSE, Fehlerfälle) |
| TST-0186 | acceptance | Gherkin-Szenarien CON-0160 (INV-01–04, alle Status-Varianten)       |
| TST-0187 | unit       | HoldoutStatusFetcher Strategy (SSE-Parsing, Reconnect-Backoff)      |

## 11. Offene Fragen

- [x] Existiert bereits ein API-Endpunkt für den Holdout-Status, oder muss er neu gebaut werden? → Muss neu gebaut werden.
- [x] Polling oder WebSocket als Standard-Update-Strategie? → SSE (EventSource) – konsistent mit dem bestehenden Stream-Muster des Projekts.
- [x] Sollen historische Holdout-Läufe (nicht nur der neueste) ebenfalls angezeigt werden? → Nein, nur der neueste Lauf.

## 12. Implementierungsreihenfolge

1. API-Endpunkt `GET /api/holdouts/{spec_id}` + SSE-Stream (Backend, neu)
2. Contract CON-XXXX (API-Schema, Pfad-Konvention gemäß SPEC-0003)
3. SSE-Integration in bestehende EventSource-Infrastruktur (SPEC-0007)
4. StatusFetcher-Strategy (Frontend-Service)
5. Badge-Komponente aus SPEC-0006 wiederverwenden / erweitern
6. Detail-Listenkomponente aus SPEC-0006 wiederverwenden / erweitern
7. ContainerView-Integration
8. Acceptance-Tests

## 13. Änderungshistorie

| Datum      | Version | Autor  | Änderung            |
|------------|---------|--------|---------------------|
| 2026-06-09 | 0.1.0   | Boris  | Initiale Erstellung |
| 2026-06-09 | 0.2.0   | Boris  | Regression-Fixes: Pfad-Konvention (FR-04), SSE-Infrastruktur-Referenz (FR-01), Komponenten-Wiederverwendung SPEC-0006 (FR-02/03), depends_on erweitert |
