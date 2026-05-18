---
id: SPEC-XXXX
title: "<Kurzer, prägnanter Titel des Features>"
type: feature           # feature | bug-fix
status: draft           # draft | review | approved | implemented | deprecated
owner: "<Name oder Team>"
created: YYYY-MM-DD
updated: YYYY-MM-DD
version: 0.1.0
priority: medium        # low | medium | high | critical
tags: []
depends_on: []          # z.B. ["SPEC-0001"]
contracts: []           # z.B. ["CON-0001"] – MUSS mindestens einen Eintrag enthalten
tests: []               # z.B. ["TST-0001"] – MUSS mindestens einen Eintrag enthalten
adrs: []                # z.B. ["ADR-0001"]
---

# {{title}}

> **Status:** {{status}} · **Owner:** {{owner}} · **Version:** {{version}}

## 1. Kontext & Motivation

<!--
Warum existiert dieses Feature? Welches Problem löst es?
Wer sind die Nutzer/Stakeholder? In welchen Workflow passt es?
-->

## 2. Zielsetzung

**Primärziel:**
<!-- Ein Satz, der den Kernzweck beschreibt -->

**Erfolgskriterien (messbar):**
- [ ] <!-- z.B. "Login dauert < 500ms im 95. Perzentil" -->
- [ ] <!-- z.B. "Fehlerquote < 0.1%" -->

**Nicht-Ziele (explizit):**
<!-- Was diese Spec NICHT abdeckt, um Scope-Creep zu vermeiden -->
- ...

## 3. User Stories

| ID    | Als ...           | möchte ich ...                | um ...                          |
|-------|-------------------|-------------------------------|---------------------------------|
| US-01 | <Rolle>           | <Fähigkeit>                   | <Nutzen>                        |

## 4. Funktionale Anforderungen

- **FR-01:** <Klare, testbare Aussage im Aktiv>
- **FR-02:** ...

## 5. Nicht-funktionale Anforderungen

| Kategorie       | Anforderung                                           |
|-----------------|-------------------------------------------------------|
| Performance     | <z.B. p95 Antwortzeit < 200ms>                        |
| Security        | <z.B. OAuth2 PKCE, alle Endpunkte authentifiziert>    |
| Accessibility   | <z.B. WCAG 2.1 AA>                                    |
| Observability   | <z.B. strukturiertes Logging, Trace-IDs>              |
| Datenschutz     | <z.B. DSGVO-konform, keine PII im Log>                |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: <Feature-Name>

  Scenario: <Happy Path>
    Given <Ausgangssituation>
    When <Aktion>
    Then <erwartetes Ergebnis>

  Scenario: <Edge Case>
    Given <...>
    When <...>
    Then <...>
```

## 7. Edge Cases & Fehlerfälle

- ...

## 8. Contracts (was wird garantiert)

Diese Spec wird durch folgende Contracts maschinell prüfbar gemacht:

| Contract-ID | Typ        | Was wird garantiert?                       |
|-------------|------------|--------------------------------------------|
| CON-XXXX    | api        | <z.B. POST /login Request/Response-Schema> |
| CON-XXXX    | behavior   | <z.B. Gherkin-Szenarien>                   |
| CON-XXXX    | performance| <z.B. SLO p95 < 200ms>                     |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level        | Was prüft der Test?                      |
|----------|--------------|------------------------------------------|
| TST-XXXX | contract     | OpenAPI-Konformität gegen CON-XXXX       |
| TST-XXXX | acceptance   | Gherkin-Szenarien aus Sektion 6          |
| TST-XXXX | unit         | Validierungslogik einzelner Funktionen   |

## 10. Offene Fragen

- [ ] ...

## 11. Änderungshistorie

| Datum      | Version | Autor   | Änderung           |
|------------|---------|---------|--------------------|
| YYYY-MM-DD | 0.1.0   | <Name>  | Initiale Erstellung|
