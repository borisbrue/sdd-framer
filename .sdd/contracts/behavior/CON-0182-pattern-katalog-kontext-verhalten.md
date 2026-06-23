---
id: CON-0182
project: PRJ-0001
title: "Pattern-Katalog-Kontext – Verhalten bei Prompt-Aufbau und Skill-Kontextladen"
type: behavior
format: gherkin
spec: SPEC-0048
version: 0.1.0
status: approved
artifact: ""
tests:
- TST-0211
---

# Contract: Pattern-Katalog-Kontext – Verhalten bei Prompt-Aufbau und Skill-Kontextladen

> **Spec:** SPEC-0048 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Definiert das beobachtbare Verhalten, wenn der globale Pattern-Katalog
(`.sdd/patterns/_catalog.json`) als Kontext in den Pattern-Suggestion-Prompt
(`PatternSuggester.suggest()`) und in den `/sdd-implement`-Kontextladeschritt einfließt.

## Invarianten (über alle Szenarien hinweg)

- **INV-01:** Ist der Katalog leer oder nicht vorhanden, ist `catalog_summary()` ein
  leerer String — der Prompt enthält dann **keinen** Abschnitt
  "BEREITS AKZEPTIERTE PATTERNS IM PROJEKT".
- **INV-02:** Ist der Katalog nicht leer, enthält der Prompt diesen Abschnitt mit
  maximal `max_entries` (Default 10) Einträgen.
- **INV-03:** Der Pattern-Eintrag der gerade analysierten Spec/Contract-ID selbst wird
  aus der Katalog-Zusammenfassung ausgeschlossen (kein Duplikat zum separat geladenen
  spec-eigenen Pattern-File).
- **INV-04:** Die Prompt-Reihenfolge bleibt invariant: Instruktion → Artefakt-Info →
  Katalog-Kontext (falls vorhanden) → Output-Format-Anweisung.

## Gherkin-Szenarien

```gherkin
Feature: Pattern-Katalog-Kontext

  Scenario: Katalog enthält Einträge anderer Specs
    Given ".sdd/patterns/_catalog.json" enthält akzeptierte Patterns aus SPEC-0034 und SPEC-0037
    When "PatternSuggester.suggest()" für SPEC-0048 aufgerufen wird
    Then enthält der generierte Prompt den Abschnitt "BEREITS AKZEPTIERTE PATTERNS IM PROJEKT"
    And der Abschnitt listet die Patterns aus SPEC-0034 und SPEC-0037 mit Pattern-Name, Spec-ID und Begründung

  Scenario: Katalog ist leer
    Given ".sdd/patterns/_catalog.json" existiert nicht oder enthält keine Einträge
    When "PatternSuggester.suggest()" aufgerufen wird
    Then enthält der generierte Prompt KEINEN Abschnitt "BEREITS AKZEPTIERTE PATTERNS IM PROJEKT"

  Scenario: Katalog enthält nur den Eintrag der eigenen Spec
    Given ".sdd/patterns/_catalog.json" enthält ausschließlich Patterns mit spec_id "SPEC-0048"
    When "PatternSuggester.suggest()" für SPEC-0048 aufgerufen wird
    Then ist die Katalog-Zusammenfassung leer
    And der Prompt enthält KEINEN Abschnitt "BEREITS AKZEPTIERTE PATTERNS IM PROJEKT"

  Scenario: Katalog hat mehr als max_entries Einträge
    Given ".sdd/patterns/_catalog.json" enthält 15 akzeptierte Patterns aus anderen Specs
    When "catalog_summary(max_entries=10)" aufgerufen wird
    Then enthält die Zusammenfassung genau 10 Einträge
    And es sind die 10 zuletzt akzeptierten Einträge (neueste zuerst)

  Scenario: /sdd-implement zeigt Katalog-Zusammenfassung im Kontextschritt
    Given SPEC-0048 wird über "/sdd-implement SPEC-0048" gestartet
    And der globale Pattern-Katalog enthält mindestens einen Eintrag außerhalb von SPEC-0048
    When Schritt 2 ("Kontext laden") ausgeführt wird
    Then enthält die Kontext-Zusammenfassung eine Zeile "Etablierte Patterns im Projekt: [...]"
```

## Begriffe

| Begriff               | Definition |
|------------------------|------------|
| Katalog                | `.sdd/patterns/_catalog.json` – projektweite Aggregation aller akzeptierten Patterns |
| Katalog-Zusammenfassung | Vom `PatternRegistry.catalog_summary()` erzeugter, LLM-tauglicher Text |
| eigene Spec/Contract   | Die Artefakt-ID, für die gerade `suggest()` bzw. der Implementierungsschritt läuft |
