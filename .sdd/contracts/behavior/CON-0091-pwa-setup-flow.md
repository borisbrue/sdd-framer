---
id: CON-0091
title: "pwa-setup-flow"
type: behavior
format: gherkin
spec: SPEC-0024
version: 0.1.0
status: draft
tests: [TST-0101]
---

# Contract: PWA Setup-Flow

> **Spec:** SPEC-0024 · **Typ:** Behavior (Gherkin) · **Status:** draft

## Zweck

Definiert das Verhalten des Setup-Screens beim ersten Start der PWA.
URL und Token werden nur nach erfolgreicher Validierung in localStorage gespeichert.

## Szenarien

```gherkin
Feature: PWA Setup-Flow

  Background:
    Given die PWA läuft ohne gültigen sdd_config in localStorage
    # sdd_config fehlt entweder ganz ODER wurde bei HTTP 401 vollständig gelöscht (CON-0090 G-02)

  Scenario: Erfolgreiche Einrichtung
    Given der Nutzer gibt eine gültige Backend-URL ein
    And der Nutzer gibt einen gültigen Bearer-Token ein
    When der Nutzer auf "Verbinden" tippt
    And GET <baseUrl>/api/specs antwortet mit HTTP 200
    Then speichert die PWA URL und Token in localStorage unter "sdd_config"
    And navigiert zum Dashboard-Tab

  Scenario: Ungültige URL
    Given der Nutzer gibt eine malformierte URL ein (kein http:// oder https://)
    When der Nutzer auf "Verbinden" tippt
    Then zeigt der Setup-Screen eine Validierungsfehlermeldung
    And localStorage bleibt unverändert

  Scenario: Falscher Token (HTTP 401)
    Given der Nutzer gibt eine erreichbare Backend-URL ein
    And der Nutzer gibt einen falschen Bearer-Token ein
    When der Nutzer auf "Verbinden" tippt
    And GET <baseUrl>/api/specs antwortet mit HTTP 401
    Then zeigt der Setup-Screen "Ungültiger Token"
    And localStorage bleibt unverändert

  Scenario: Backend nicht erreichbar
    Given der Nutzer gibt eine nicht erreichbare URL ein
    When der Nutzer auf "Verbinden" tippt
    And die Verbindung schlägt mit Netzwerkfehler fehl
    Then zeigt der Setup-Screen "Backend nicht erreichbar"
    And localStorage bleibt unverändert

  Scenario: Folgestart mit gültigem Token
    Given localStorage enthält sdd_config mit gültiger URL und Token
    When die PWA gestartet wird
    Then überspringt die PWA den Setup-Screen
    And navigiert direkt zum Dashboard-Tab

  Scenario: Folgestart — Token abgelaufen (HTTP 401 im Hintergrund)
    Given localStorage enthält sdd_config mit URL und Token
    When die PWA im Hintergrund GET /api/specs aufruft
    And die Antwort ist HTTP 401
    Then löscht der ApiClient den gesamten sdd_config-Key aus localStorage (CON-0090 G-02)
    And setzt ConnectionStore auf setup_required
    And leitet die PWA zum Setup-Screen weiter

  Scenario: Manueller Setup nach QR-Onboarding
    Given ein QR-Onboarding-Flow wurde zuvor durchgeführt (CON-0087)
    And der Token wurde dabei rotiert (CON-0086 INV-02)
    When der Nutzer den Setup-Screen manuell öffnet
    Then muss der Nutzer den neuen (rotierten) Token eingeben
    # Der Original-QR-Token ist blacklistet und ergibt HTTP 401 (CF-0024-001 resolved)
```

## Invarianten

| ID | Invariante |
|---|---|
| INV-01 | localStorage wird nie mit einem nicht-validierten Token beschrieben |
| INV-02 | Bei HTTP 401 → ApiClient löscht gesamten sdd_config-Key (nicht nur token-Feld), kein Retry mit altem Token |
| INV-03 | URL-Validierung erfolgt client-seitig vor dem Netzwerkaufruf |
| INV-04 | Setup-Guard-Bedingung: `sdd_config` fehlt im localStorage (nicht: leeres token-Feld) |
