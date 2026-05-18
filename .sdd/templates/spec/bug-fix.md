---
id: SPEC-XXXX
title: "<Kurze Symptombeschreibung>"
type: bug-fix           # feature | bug-fix
status: draft           # draft | review | approved | implemented | deprecated
owner: "<Name oder Team>"
created: YYYY-MM-DD
updated: YYYY-MM-DD
version: 0.1.0
priority: high          # low | medium | high | critical
tags: ["bug"]
depends_on: []
contracts: []           # z.B. ["CON-0001"] – MUSS mindestens einen Eintrag enthalten
tests: []               # z.B. ["TST-0001"] – MUSS mindestens einen Eintrag enthalten
adrs: []
---

# {{title}}

> **Status:** {{status}} · **Owner:** {{owner}} · **Version:** {{version}}
> **Typ:** Bug-Fix — beschreibt nur das Symptom, keine Root-Cause-Annahmen.

## 1. Symptom

<!--
Was genau passiert? Wo tritt der Fehler auf?
Beschreibe das beobachtete Fehlverhalten so präzise wie möglich.
Keine Vermutungen zur Ursache — der Agent untersucht die Codebasis selbst.
-->

**Fehlverhalten:** <!-- z.B. "POST /api/auth/login gibt HTTP 500 zurück wenn supplier null ist" -->
**Betroffener Endpunkt / Bereich:** <!-- z.B. "POST /api/auth/login" -->
**Reproduzierbar:** <!-- immer | manchmal | einmalig beobachtet -->

### Schritte zur Reproduktion

1. <!-- Ausgangszustand -->
2. <!-- Aktion -->
3. <!-- Beobachtetes Ergebnis -->

### Fehlermeldung / Log-Ausgabe (falls vorhanden)

```
<!-- Stacktrace, Log-Zeile oder Fehlermeldung hier einfügen -->
```

## 2. Erwartetes Verhalten

<!--
Was sollte stattdessen passieren?
Sei konkret: HTTP-Status, Response-Format, Fehlermeldungstext etc.
-->

**Erwartet:** <!-- z.B. "HTTP 400 mit JSON-Fehler {'error': 'supplier darf nicht null sein'}" -->

> ⚠️ **Hinweis für den Code-Agenten:** Untersuche die Codebasis eigenständig.
> Nimm keine Root-Cause-Annahmen aus dieser Spec an. Finde die Ursache selbst.

## 3. Kontext & Umgebung

| Feld              | Wert                              |
|-------------------|-----------------------------------|
| Service / Repo    | <!-- z.B. WritebackService -->    |
| Branch / Version  | <!-- z.B. release / v2.3.1 -->    |
| Umgebung          | <!-- z.B. production, staging --> |
| Erstmals gesehen  | <!-- z.B. 2026-05-16 -->          |
| Häufigkeit        | <!-- z.B. 3× täglich -->          |

## 4. Akzeptanzkriterien

```gherkin
Feature: Bug-Fix: {{title}}

  Scenario: Reproduzierter Fehler ist behoben
    Given <!-- Ausgangszustand wie in Reproduktionsschritten -->
    When  <!-- Aktion die zuvor den Fehler auslöste -->
    Then  <!-- Erwartetes Ergebnis (kein 500, stattdessen korrekte Antwort) -->

  Scenario: Kein Regressionsfall
    Given <!-- normaler Betriebsfall -->
    When  <!-- Standard-Aktion -->
    Then  <!-- Normales Ergebnis bleibt unverändert -->
```

## 5. Contracts

| Contract-ID | Typ      | Was wird garantiert?                          |
|-------------|----------|-----------------------------------------------|
| CON-XXXX    | behavior | Gherkin-Szenarien aus Sektion 4               |
| CON-XXXX    | api      | Korrektes HTTP-Response-Schema                |

## 6. Tests

| Test-ID  | Level      | Was prüft der Test?                           |
|----------|------------|-----------------------------------------------|
| TST-XXXX | unit       | Isolierter Fix der gefundenen Ursache         |
| TST-XXXX | acceptance | Gherkin-Szenarien aus Sektion 4               |

## 7. Änderungshistorie

| Datum      | Version | Autor   | Änderung           |
|------------|---------|---------|--------------------|
| YYYY-MM-DD | 0.1.0   | <Name>  | Initiale Erstellung|
