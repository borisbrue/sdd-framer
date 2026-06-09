---
id: SPEC-0033
title: sdd generate-holdouts – Automatische Holdout-Generierung per CLI
type: feature
status: implemented
owner: Boris
created: 2026-05-30
updated: '2026-06-09'
version: 0.2.0
priority: medium
tags:
- cli
- holdout
- llm
depends_on:
- SPEC-0020
contracts:
- CON-0157
- CON-0158
tests:
- TST-0183
- TST-0184
fr_test_map:
  FR-01: TST-0183
  FR-02: TST-0183
  FR-03: TST-0184
  FR-04: TST-0183
  FR-05: TST-0183
  FR-06: TST-0183
  FR-07: TST-0183
adrs: []
started_at: '2026-06-09T10:41:30Z'
---
# sdd generate-holdouts – Automatische Holdout-Generierung per CLI

> **Status:** draft · **Owner:** Boris · **Version:** 0.2.0

## 1. Kontext & Motivation

Holdout-Szenarien werden bisher entweder manuell via `sdd new holdout` einzeln angelegt
oder implizit durch den `/sdd-implement`-Skill (Schritt 1.5) per Subagent erzeugt.
Es fehlt ein direkter CLI-Befehl, mit dem Holdouts für eine Spec auf Knopfdruck generiert
werden können — unabhängig vom Implementierungsflow.

**Anwendungsfälle:**
- Vor `sdd start`: Holdouts anlegen bevor die Implementierung beginnt
- Nachträgliche Ergänzung: Holdouts für ältere Specs ohne Holdouts nachgenerieren
- Review: Sicherstellen dass alle Contracts Holdout-Abdeckung haben

## 2. Zielsetzung

**Primärziel:**
`sdd generate-holdouts SPEC-XXXX` liest Spec und Contracts, leitet via LLM 2–4
Holdout-Szenarien pro Contract ab und legt die HOL-Dateien automatisch an.

**Erfolgskriterien (messbar):**
- [ ] Befehl erzeugt mindestens 2 HOL-Dateien pro verlinktem Contract
- [ ] Keine Implementierungsdatei wird gelesen (tool/, web/, tests/ bleiben unberührt)
- [ ] Bestehende HOL-Dateien für dieselbe Spec werden nicht überschrieben
- [ ] Laufzeit < 60s für eine Spec mit bis zu 5 Contracts

**Nicht-Ziele (explizit):**
- Keine interaktive Bestätigung vor dem Schreiben (anders als `/sdd-holdout`-Skill)
- Kein Editieren oder Löschen bestehender HOL-Dateien
- Keine Bewertung ob Holdouts "gut genug" sind

## 3. User Stories

| ID    | Als ...           | möchte ich ...                              | um ...                                         |
|-------|-------------------|---------------------------------------------|------------------------------------------------|
| US-01 | Entwickler        | `sdd generate-holdouts SPEC-XXXX` aufrufen | Holdouts vor der Implementierung automatisch zu erzeugen |
| US-02 | Entwickler        | einen Überblick der erzeugten HOL-IDs sehen | zu wissen was generiert wurde                  |
| US-03 | Entwickler        | eine Fehlermeldung bei fehlenden Contracts erhalten | den Prozess korrekt abzuschließen         |

## 4. Funktionale Anforderungen

- **FR-01:** `sdd generate-holdouts SPEC-XXXX` liest ausschließlich die Spec-Datei und alle verlinkten Contracts.
- **FR-02:** Pro Contract werden via LLM 2–4 Szenarien abgeleitet (Happy Path + mindestens 1 Fehlerfall).
- **FR-03:** Jedes Szenario wird als HOL-Datei gespeichert: `id`, `spec`, `status: ready`, `title`, `## Input`, `## Expected`, `## Evaluation Hint`.
- **FR-04:** Bereits existierende HOL-Dateien für dieselbe Spec werden übersprungen (kein Überschreiben), mit Hinweis im Output.
- **FR-05:** Spec ohne verlinkte Contracts → Abbruch mit: "Keine Contracts gefunden. Erstelle zuerst Contracts mit `sdd new contract`."
- **FR-06:** Spec mit `status: draft` → Abbruch mit: "Spec muss `approved` oder `in-progress` sein."
- **FR-07:** Am Ende: tabellarische Ausgabe aller angelegten HOL-IDs mit Contract-Zuordnung.

## 5. Nicht-funktionale Anforderungen

| Kategorie     | Anforderung                                                               |
|---------------|---------------------------------------------------------------------------|
| Isolation     | Liest niemals `tool/`, `web/`, `tests/`, `*.py`, `*.ts` — Implementierungsdetails bleiben außen vor |
| Idempotenz    | Mehrfaches Ausführen erzeugt keine Duplikate                              |
| Observability | Jede erzeugte HOL-Datei wird mit Pfad in stdout ausgegeben               |
| LLM-Provider  | Nutzt den konfigurierten Provider aus `.sdd/config.yaml` (SPEC-0008)     |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: sdd generate-holdouts

  Scenario: Happy Path – Holdouts für Spec mit 2 Contracts generieren
    Given eine Spec mit status "approved" und 2 verlinkten Contracts
    And keine HOL-Dateien für diese Spec existieren noch
    When der Nutzer `sdd generate-holdouts SPEC-XXXX` ausführt
    Then werden mindestens 4 HOL-Dateien angelegt (2 pro Contract)
    And jede HOL-Datei enthält id, spec, status, title, Input, Expected, Evaluation Hint
    And die Ausgabe listet alle angelegten HOL-IDs

  Scenario: Spec ohne Contracts
    Given eine Spec mit status "approved" aber leerer contracts-Liste
    When der Nutzer `sdd generate-holdouts SPEC-XXXX` ausführt
    Then bricht der Befehl mit einer Fehlermeldung ab
    And es werden keine Dateien geschrieben

  Scenario: Spec mit status draft
    Given eine Spec mit status "draft"
    When der Nutzer `sdd generate-holdouts SPEC-XXXX` ausführt
    Then bricht der Befehl mit "Spec muss approved oder in-progress sein" ab

  Scenario: HOL-Dateien bereits vorhanden
    Given eine Spec mit 1 verlinktem Contract
    And bereits 2 HOL-Dateien für diese Spec existieren
    When der Nutzer `sdd generate-holdouts SPEC-XXXX` ausführt
    Then werden die bestehenden HOL-Dateien übersprungen
    And die Ausgabe zeigt "N Holdouts übersprungen (bereits vorhanden)"
```

## 7. Edge Cases & Fehlerfälle

- Contract-Datei nicht gefunden (referenziert aber fehlt auf Disk) → Warnung + überspringen, restliche Contracts verarbeiten
- LLM-Aufruf schlägt fehl → Retry 1x, danach Abbruch mit Fehlermeldung
- Spec-ID nicht gefunden → "Spec SPEC-XXXX nicht gefunden."

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert?                                          |
|-------------|----------|---------------------------------------------------------------|
| CON-0157    | behavior | CLI-Verhalten: Eingabe, Ausgabe, Fehlerfälle von `sdd generate-holdouts` |
| CON-0158    | behavior | HOL-Datei-Struktur: Pflichtfelder, Format, Idempotenz-Garantie |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level    | Was prüft der Test?                                      |
|----------|----------|----------------------------------------------------------|
| TST-0183 | contract | CLI-Verhalten: Eingabe, Ausgabe, Fehlerfälle (CON-0157)  |
| TST-0184 | contract | HOL-Datei entspricht CON-0158 (Pflichtfelder vorhanden)  |

## 10. Offene Fragen

- [ ] Soll `--dry-run` unterstützt werden (Szenarien anzeigen ohne zu speichern)?
- [ ] Soll `--force` bestehende HOL-Dateien überschreiben dürfen?

## 11. Änderungshistorie

| Datum      | Version | Autor | Änderung                          |
|------------|---------|-------|-----------------------------------|
| 2026-05-30 | 0.1.0   | Boris | Initiale Erstellung (Platzhalter) |
| 2026-06-09 | 0.2.0   | Boris | Spec vollständig ausgearbeitet    |
