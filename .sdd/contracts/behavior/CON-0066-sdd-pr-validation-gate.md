---
id: CON-0066
title: "sdd-dev-pr-validation-gate"
type: behavior
format: gherkin
spec: SPEC-0021
version: 0.2.0
status: draft
artifact: "contracts/behavior/sdd-dev-pr-validation-gate.feature"
tests: [TST-0075]
---

# Contract: sdd-dev-pr-validation-gate

> **Spec:** SPEC-0021 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Beschreibt das beobachtbare Verhalten von `sdd dev pr SPEC-XXXX`:
Validierungsgatter vor PR-Erstellung im interaktiven Entwicklungspfad.

**Verhältnis zu CON-0025 (Execution Gate Phase State Machine):**
`sdd dev pr` ist ein Werkzeug für den interaktiven Level-2/3-Pfad und setzt
voraus, dass CON-0025 bereits `execute-unlocked` gesetzt hat (Spec ist approved).
CON-0025 bleibt die Authority für Pipeline-Phasen. CON-0066 definiert zusätzliche
Laufzeit-Prüfungen (Test-Ergebnis, validate-Output) spezifisch für `sdd dev pr` —
kein Ersatz, sondern Ergänzung auf Laufzeitebene.

## Garantien

- **G-01:** `sdd dev pr` blockiert wenn die letzte Test-Ausführung im Container
  fehlgeschlagen ist oder keine Test-Ausführung protokolliert wurde.
- **G-02:** `sdd dev pr` blockiert wenn `sdd validate` Fehler meldet.
- **G-03:** `sdd dev pr` warnt (blockiert nicht) bei uncommitted changes im
  Working Tree des Containers.
- **G-04:** Bei erfolgreichem Gate wird ein PR-Dokument unter
  `.sdd/prs/PR-SPEC-XXXX.md` erstellt und eine Merge-Anleitung ausgegeben.
- **G-05:** Der Regression-Check (`git diff main..dev/SPEC-XXXX --stat`) ist
  Teil des PR-Dokuments.

## Invarianten

- **INV-01:** `sdd dev pr` nimmt keinen automatischen `git commit` vor.
- **INV-02:** Das PR-Dokument wird nur erstellt wenn alle Prüfungen bestanden sind.
- **INV-03:** Die Merge-Anleitung enthält immer den konkreten Branch-Namen
  (`dev/SPEC-XXXX`).
- **INV-04:** `sdd dev pr` erfordert keinen aktiven Container — es liest den
  zuletzt protokollierten Test-Ergebnisstatus aus `.sdd/test-results/`.

## Szenarien

```gherkin
Feature: sdd dev pr – Validierungsgatter vor PR-Erstellung

  Background:
    Given ein SDD-Projekt mit .sdd/config.yaml
    And Branch "dev/SPEC-0021" ist ausgecheckt

  Scenario: Erfolgreiches Gate – PR-Dokument wird erstellt
    Given der letzte Test-Lauf im Container hat Exit-Code 0 protokolliert
    And "sdd validate" meldet keine Fehler
    And keine uncommitted changes im Working Tree
    When der Nutzer "sdd dev pr SPEC-0021" ausführt
    Then wird git diff main..dev/SPEC-0021 --stat ausgeführt
    And wird .sdd/prs/PR-SPEC-0021.md erstellt
    And die Merge-Anleitung wird ausgegeben:
      "git checkout main && git merge dev/SPEC-0021"
    And der Exit-Code ist 0

  Scenario: Gate blockiert – letzter Test-Lauf fehlgeschlagen
    Given der letzte protokollierte Test-Lauf hat Exit-Code != 0
    When der Nutzer "sdd dev pr SPEC-0021" ausführt
    Then wird kein PR-Dokument erstellt
    And erscheint Fehler: "Tests nicht grün – führe 'sdd dev exec SPEC-0021 pytest' aus."
    And der Exit-Code ist ungleich 0

  Scenario: Gate blockiert – sdd validate meldet Fehler
    Given letzter Test-Lauf ist grün
    And "sdd validate" meldet 1 oder mehr Fehler
    When der Nutzer "sdd dev pr SPEC-0021" ausführt
    Then wird kein PR-Dokument erstellt
    And die Validierungsfehler werden ausgegeben
    And der Exit-Code ist ungleich 0

  Scenario: Warnung bei uncommitted changes
    Given letzter Test-Lauf ist grün
    And "sdd validate" ist sauber
    And es gibt uncommitted changes im Working Tree
    When der Nutzer "sdd dev pr SPEC-0021" ausführt
    Then erscheint eine Warnung: "Uncommitted changes vorhanden – bitte committen"
    And das Gate fährt fort (kein Abbruch)
    And PR-Dokument wird erstellt

  Scenario: Gate blockiert – kein Test-Ergebnis protokolliert
    Given keine Test-Ausführung wurde für SPEC-0021 protokolliert
    When der Nutzer "sdd dev pr SPEC-0021" ausführt
    Then erscheint Fehler: "Kein Test-Ergebnis für SPEC-0021 – führe 'sdd dev exec SPEC-0021 pytest' aus."
    And kein PR-Dokument wird erstellt
    And der Exit-Code ist ungleich 0
```

## Begriffe

| Begriff | Definition |
|---|---|
| Gate | Laufzeit-Validierungsprüfung ergänzend zu CON-0025 (Phase State Machine) |
| PR-Dokument | Markdown-Datei unter `.sdd/prs/` mit Diff-Zusammenfassung und Merge-Anleitung |
| Regression-Check | `git diff main..dev/SPEC-XXXX --stat` |
