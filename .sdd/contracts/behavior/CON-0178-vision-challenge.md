---
id: CON-0178
project: PRJ-0001
title: "sdd vision challenge – LLM- und Code-Challenge"
type: behavior
format: gherkin
spec: SPEC-0046
version: 0.1.0
status: approved
artifact: ""
tests: ["TST-0204"]
---

# Contract: sdd vision challenge – LLM- und Code-Challenge

> **Spec:** SPEC-0046 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Definiert das beobachtbare Verhalten von `sdd vision challenge <feature-index>`:
LLM-Challenge (via SPEC-0008 AIProvider, async per SPEC-0016), Code-Challenge
(synchron, Keyword-Matching), kombinierter Aufruf (Default), und
Ergebnis-Persistenz in `.sdd/vision.md`.

## Invarianten

- **INV-01:** Der LLM-Aufruf erfolgt ausschließlich über das `AIProvider`-Interface
  aus SPEC-0008 (`get_ai_provider(config)`) — kein direkter Provider-Zugriff.
- **INV-02:** Der LLM-Challenge-Job läuft async gemäß SPEC-0016
  (Fire-and-forget, persistenter Verlauf). Fortschritt wird auf stdout ausgegeben.
- **INV-03:** Die Code-Challenge läuft synchron — kein LLM-Aufruf, kein async.
- **INV-04:** `<feature-index>` ist 1-basiert und entspricht der Reihenfolge
  in `## Features`. Ein ungültiger Index bricht mit Fehler ab.
- **INV-05:** Challenge-Ergebnisse werden inline unter dem betreffenden
  Feature-Eintrag in `.sdd/vision.md` gespeichert:
  LLM-Ergebnis als `> LLM Challenge: …`, Code-Ergebnis als `> Code Challenge: …`.
- **INV-06:** Ein bestehendes Challenge-Ergebnis (LLM oder Code) wird beim
  erneuten Ausführen überschrieben.
- **INV-07:** Ist `--llm` angegeben, läuft nur die LLM-Challenge.
  Ist `--code` angegeben, läuft nur die Code-Challenge.
  Ohne Flag laufen beide (LLM async, Code synchron; Ergebnisse nach Abschluss
  beider zusammen ausgegeben).

## Gherkin-Szenarien

```gherkin
Feature: sdd vision challenge – LLM- und Code-Challenge

  Background:
    Given `.sdd/vision.md` existiert
    And enthält mindestens 1 Feature unter `## Features`

  Scenario: Kombinierter Challenge (kein Flag)
    When der Nutzer `sdd vision challenge 1` ausführt
    Then startet der LLM-Job async (SPEC-0016-Framework)
    And die Code-Challenge läuft synchron parallel
    And nach Abschluss beider werden beide Ergebnisse auf stdout ausgegeben
    And unter Feature 1 wird `> LLM Challenge:` mit Aufwand und Begründung gespeichert
    And unter Feature 1 wird `> Code Challenge:` mit Dateiliste gespeichert
    And der Exit-Code ist 0

  Scenario: Nur LLM-Challenge (--llm)
    When der Nutzer `sdd vision challenge 1 --llm` ausführt
    Then wird nur der LLM-Job gestartet
    And das Ergebnis enthält: Aufwand (low/medium/high/unknown), Begründung, Fallstricke
    And unter Feature 1 wird `> LLM Challenge:` in `.sdd/vision.md` gespeichert
    And `> Code Challenge:` bleibt unverändert (falls vorhanden)
    And der Exit-Code ist 0

  Scenario: Nur Code-Challenge (--code)
    When der Nutzer `sdd vision challenge 1 --code` ausführt
    Then wird Keyword-Matching auf den Projektcode angewendet
    And das Ergebnis enthält eine Liste betroffener Dateien/Module
    And unter Feature 1 wird `> Code Challenge:` in `.sdd/vision.md` gespeichert
    And `> LLM Challenge:` bleibt unverändert (falls vorhanden)
    And der Exit-Code ist 0

  Scenario: Ungültiger Feature-Index
    When der Nutzer `sdd vision challenge 99` ausführt
    And Feature 99 existiert nicht
    Then gibt der Befehl eine Fehlermeldung aus ("Feature-Index 99 nicht gefunden")
    And `.sdd/vision.md` ist unverändert
    And der Exit-Code ist nicht 0

  Scenario: LLM-Challenge überschreibt bestehendes Ergebnis
    Given Feature 1 enthält bereits `> LLM Challenge: Aufwand: low`
    When der Nutzer `sdd vision challenge 1 --llm` erneut ausführt
    Then wird das bestehende LLM-Challenge-Ergebnis durch das neue ersetzt
    And der Exit-Code ist 0

  Scenario: Vision fehlt
    Given kein `.sdd/vision.md` existiert
    When der Nutzer `sdd vision challenge 1` ausführt
    Then enthält die Ausgabe eine Fehlermeldung mit Hinweis auf `sdd vision init`
    And der Exit-Code ist nicht 0

  Scenario: Code-Challenge – keine betroffenen Dateien gefunden
    When der Nutzer `sdd vision challenge 1 --code` ausführt
    And kein Keyword aus Titel/Beschreibung des Features trifft auf Projektcode zu
    Then wird `> Code Challenge: Keine betroffenen Dateien gefunden.` gespeichert
    And der Exit-Code ist 0
```
