---
id: CON-0177
project: PRJ-0001
title: "sdd vision add-feature und sdd vision add-task"
type: behavior
format: gherkin
spec: SPEC-0046
version: 0.1.0
status: approved
artifact: ""
tests: ["TST-0203"]
---

# Contract: sdd vision add-feature und sdd vision add-task

> **Spec:** SPEC-0046 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Definiert das beobachtbare Verhalten von `sdd vision add-feature` (Feature-Idee
zur Vision hinzufügen) und `sdd vision add-task` (einfachen Task notieren).

## Invarianten

- **INV-01:** Features werden als nummerierte Liste unter `## Features` in
  `.sdd/vision.md` gespeichert. Der Index ist fortlaufend (1-basiert) und
  entspricht der Reihenfolge der Einträge.
- **INV-02:** Tasks werden als Markdown-Checkbox-Liste unter `## Tasks` in
  `.sdd/vision.md` gespeichert (`- [ ] Titel`).
- **INV-03:** Beide Befehle brechen mit Fehler ab wenn `.sdd/vision.md`
  nicht existiert.
- **INV-04:** Titel ist Pflichtfeld bei beiden Befehlen — ein leerer Titel
  wird abgelehnt.
- **INV-05:** Features haben keinen Status-Lifecycle und keine Contract-Bindung.
  Tasks haben keinen Lifecycle und keine Contract-Bindung.
- **INV-06:** Bestehende Einträge (Features, Tasks, LLM/Code-Challenge-Ergebnisse)
  werden durch `add-feature` bzw. `add-task` nicht verändert.

## Gherkin-Szenarien

```gherkin
Feature: sdd vision add-feature und sdd vision add-task

  Scenario: Feature-Idee hinzufügen
    Given `.sdd/vision.md` existiert
    And der `## Features`-Abschnitt ist leer
    When der Nutzer `sdd vision add-feature` ausführt
    And Titel "Offline-Modus" und Beschreibung "App ohne Internet nutzbar" eingibt
    Then wird in `.sdd/vision.md` unter `## Features` ein Eintrag ergänzt:
      """
      1. **Offline-Modus** – App ohne Internet nutzbar
      """
    And der Exit-Code ist 0

  Scenario: Zweites Feature erhält nächsten Index
    Given `.sdd/vision.md` enthält bereits 1 Feature
    When der Nutzer `sdd vision add-feature` mit Titel "Dark Mode" ausführt
    Then wird das neue Feature mit Index 2 ergänzt
    And das bestehende Feature mit Index 1 ist unverändert

  Scenario: Feature ohne Beschreibung (nur Titel)
    Given `.sdd/vision.md` existiert
    When der Nutzer `sdd vision add-feature` ausführt
    And nur den Titel "Export als PDF" eingibt, Beschreibung leer lässt
    Then wird ein Eintrag nur mit Titel angelegt: `1. **Export als PDF**`
    And der Exit-Code ist 0

  Scenario: Task hinzufügen
    Given `.sdd/vision.md` existiert
    And der `## Tasks`-Abschnitt ist leer
    When der Nutzer `sdd vision add-task` mit Titel "README aktualisieren" ausführt
    Then wird in `.sdd/vision.md` unter `## Tasks` ergänzt:
      """
      - [ ] README aktualisieren
      """
    And der Exit-Code ist 0

  Scenario: add-feature – Vision fehlt
    Given kein `.sdd/vision.md` existiert
    When der Nutzer `sdd vision add-feature` ausführt
    Then enthält die Ausgabe eine Fehlermeldung mit Hinweis auf `sdd vision init`
    And der Exit-Code ist nicht 0

  Scenario: add-feature – leerer Titel wird abgelehnt
    Given `.sdd/vision.md` existiert
    When der Nutzer `sdd vision add-feature` ausführt
    And den Titel leer lässt
    Then gibt der Befehl eine Validierungsfehlermeldung aus
    And `.sdd/vision.md` ist unverändert
    And der Exit-Code ist nicht 0
```
