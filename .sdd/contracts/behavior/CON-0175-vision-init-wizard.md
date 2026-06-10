---
id: CON-0175
project: PRJ-0001
title: "sdd vision init – Wizard und Idempotenz-Guard"
type: behavior
format: gherkin
spec: SPEC-0046
version: 0.1.0
status: approved
artifact: ""
tests: ["TST-0201"]
---

# Contract: sdd vision init – Wizard und Idempotenz-Guard

> **Spec:** SPEC-0046 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Definiert das beobachtbare Verhalten von `sdd vision init`: den interaktiven
Wizard zur Erstellung von `.sdd/vision.md`, den Idempotenz-Guard (Abbruch wenn
Vision bereits existiert), und den optionalen Vision-Schritt in `sdd init`.

## Invarianten

- **INV-01:** `sdd vision init` erzeugt genau eine Datei: `.sdd/vision.md`.
  Weitere Dateien werden nicht angelegt.
- **INV-02:** Existiert `.sdd/vision.md` bereits, bricht der Befehl mit einer
  lesbaren Fehlermeldung ab — keine Überschreibung, kein stiller Abbruch.
- **INV-03:** Alle Wizard-Felder sind optional. Ein Skelett-Dokument
  (nur Überschriften, keine Inhalte) ist ein gültiges Ergebnis.
- **INV-04:** `sdd init` integriert den Vision-Schritt als optional —
  der Nutzer kann ihn überspringen; das Projekt ist ohne Vision vollständig
  funktionsfähig.
- **INV-05:** Das erzeugte Dokument entspricht dem Schema aus CON-0179.

## Gherkin-Szenarien

```gherkin
Feature: sdd vision init – Wizard und Idempotenz-Guard

  Scenario: Erstmalige Vision anlegen (alle Felder ausgefüllt)
    Given kein `.sdd/vision.md` existiert
    When der Nutzer `sdd vision init` ausführt
    And im Wizard Vision Statement, Zielgruppe, Tech Stack,
        Competitive Landscape und Kernprobleme eingibt
    Then wird `.sdd/vision.md` mit den eingegebenen Inhalten erstellt
    And der Exit-Code ist 0
    And das Dokument entspricht dem Schema aus CON-0179

  Scenario: Vision anlegen mit leeren Feldern (Skelett-Dokument)
    Given kein `.sdd/vision.md` existiert
    When der Nutzer `sdd vision init` ausführt
    And alle Wizard-Felder leer lässt (Enter ohne Eingabe)
    Then wird `.sdd/vision.md` als Skelett-Dokument erstellt
    And alle Abschnitt-Überschriften sind vorhanden
    And der Inhalt der Abschnitte ist leer
    And der Exit-Code ist 0

  Scenario: Idempotenz-Guard – Vision existiert bereits
    Given `.sdd/vision.md` existiert bereits
    When der Nutzer `sdd vision init` ausführt
    Then bricht der Befehl mit einer Fehlermeldung ab
    And die Meldung enthält den Pfad `.sdd/vision.md`
    And die bestehende Datei bleibt unverändert
    And der Exit-Code ist nicht 0

  Scenario: Vision-Schritt in sdd init überspringen
    Given ein neues Projekt ohne `.sdd/vision.md`
    When der Nutzer `sdd init` ausführt
    And beim optionalen Vision-Schritt "Nein" / Enter wählt
    Then wird kein `.sdd/vision.md` erstellt
    And `sdd init` schließt erfolgreich ab
    And der Exit-Code ist 0

  Scenario: Vision-Schritt in sdd init annehmen
    Given ein neues Projekt ohne `.sdd/vision.md`
    When der Nutzer `sdd init` ausführt
    And beim optionalen Vision-Schritt "Ja" wählt
    Then startet der Vision-Wizard (identisch zu `sdd vision init`)
    And `.sdd/vision.md` wird erstellt
```
