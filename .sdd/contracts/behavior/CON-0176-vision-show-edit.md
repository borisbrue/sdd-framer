---
id: CON-0176
project: PRJ-0001
title: "sdd vision show und sdd vision edit"
type: behavior
format: gherkin
spec: SPEC-0046
version: 0.1.0
status: approved
artifact: ""
tests: ["TST-0202"]
---

# Contract: sdd vision show und sdd vision edit

> **Spec:** SPEC-0046 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Definiert das beobachtbare Verhalten von `sdd vision show` (formatierte Ausgabe
des Vision-Dokuments) und `sdd vision edit` (Öffnen im Editor).

## Invarianten

- **INV-01:** Beide Befehle geben einen lesbaren Fehler aus wenn `.sdd/vision.md`
  nicht existiert — kein Absturz, Exit-Code != 0.
- **INV-02:** `sdd vision show` verändert `.sdd/vision.md` nicht.
- **INV-03:** `sdd vision edit` öffnet den Editor aus `$EDITOR`; ist `$EDITOR`
  nicht gesetzt, gibt der Befehl den absoluten Pfad zu `.sdd/vision.md` aus
  und beendet sich mit Exit-Code 0.
- **INV-04:** `sdd vision edit` wartet nicht auf den Editor-Prozess — es öffnet
  und gibt die Kontrolle sofort zurück.

## Gherkin-Szenarien

```gherkin
Feature: sdd vision show und sdd vision edit

  Scenario: Vision anzeigen
    Given `.sdd/vision.md` existiert mit Inhalt
    When der Nutzer `sdd vision show` ausführt
    Then wird der vollständige Inhalt des Dokuments auf stdout ausgegeben
    And der Exit-Code ist 0
    And `.sdd/vision.md` ist unverändert

  Scenario: Vision anzeigen – Datei fehlt
    Given kein `.sdd/vision.md` existiert
    When der Nutzer `sdd vision show` ausführt
    Then enthält die Ausgabe eine Fehlermeldung mit Hinweis auf `sdd vision init`
    And der Exit-Code ist nicht 0

  Scenario: Vision im Editor öffnen ($EDITOR gesetzt)
    Given `.sdd/vision.md` existiert
    And die Umgebungsvariable $EDITOR ist gesetzt (z.B. "vim")
    When der Nutzer `sdd vision edit` ausführt
    Then wird der Editor mit `.sdd/vision.md` als Argument gestartet
    And der Exit-Code ist 0

  Scenario: Vision im Editor öffnen ($EDITOR nicht gesetzt)
    Given `.sdd/vision.md` existiert
    And die Umgebungsvariable $EDITOR ist nicht gesetzt
    When der Nutzer `sdd vision edit` ausführt
    Then gibt der Befehl den absoluten Pfad zu `.sdd/vision.md` auf stdout aus
    And der Exit-Code ist 0

  Scenario: Vision editieren – Datei fehlt
    Given kein `.sdd/vision.md` existiert
    When der Nutzer `sdd vision edit` ausführt
    Then enthält die Ausgabe eine Fehlermeldung mit Hinweis auf `sdd vision init`
    And der Exit-Code ist nicht 0
```
