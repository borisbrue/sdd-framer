---
id: CON-0229
title: "stack apply, extract, init --stack und Preset-Verweis"
type: behavior
format: gherkin
spec: SPEC-0057
version: 0.1.0
status: draft
artifact: ".sdd/contracts/behavior/stack-apply-extract-init-stack-und-preset-verweis.feature"
tests: ["TST-0258"]
---

# Contract: stack apply, extract, init --stack und Preset-Verweis

> **Spec:** SPEC-0057 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Legt die schreibenden Befehle fest (SPEC-0057 FR-03, FR-04, FR-07 bis FR-09).

## Garantien

Die Szenarien im Artifact (`.sdd/contracts/behavior/stack-apply-extract-init-stack-und-preset-verweis.feature`) sind **ausführbare Spezifikation**.

## Invarianten

- **INV-01:** `apply` schreibt neue Dateien, lässt gleiche unberührt und legt für abweichende `<datei>.new` an (mit Diff in der Ausgabe); nichts wird überschrieben. Danach steht ein Eintrag nach CON-0227 in `stack:` (bestehender Eintrag derselben Vorlage wird ersetzt). Ein zweites `apply` derselben Version ändert keine Datei.
- **INV-02:** AGENTS.md-Abschnitte stehen zwischen `<!-- sdd-stack:NAME:ABSCHNITT -->` und `<!-- /sdd-stack:NAME:ABSCHNITT -->`; vorhandene Abschnitte werden ersetzt, neue angehängt, der übrige Text bleibt byte-gleich; Pflichtabschnitte nach CON-0011 werden nie verändert. Fehlt AGENTS.md, wird sie mit den Abschnitten angelegt, und `sdd validate` meldet fehlende Pflichtabschnitte wie bisher.
- **INV-03:** Platzhalterwerte: `--set` vor gespeicherten Werten vor Default; `project_name` ist ohne Angabe der Projekttitel. Fehlt ein Wert im nicht interaktiven Modus: Exit 2 vor dem Schreiben.
- **INV-04:** Vorlagen aus Projekt- oder Nutzerquelle zeigen vor dem Schreiben die Dateiliste mit Diff und schreiben nur nach Bestätigung oder mit `--yes`; `--dry-run` zeigt dasselbe und schreibt nie. Beim Anwenden wird kein Befehl der Vorlage ausgeführt; fehlende Werkzeuge ergeben eine Warnung.
- **INV-05:** `--only quality` wendet nur `.sdd/quality.yaml` und `.sdd/quality/**` an.
- **INV-06:** `sdd init --stack NAME` wendet die Vorlage nach der Initialisierung an; eine unbekannte Vorlage ergibt Exit 2 vor dem Anlegen des Projekts.
- **INV-07:** `extract NAME [--to user|project]` legt eine Vorlage aus dem Projekt an (Dateien nach SPEC-0057 FR-07, AGENTS.md-Abschnitte, Platzhalter für Projekt- und Paketname, Version 0.1.0); sie erfüllt CON-0227 und lässt sich anwenden. Existiert die Vorlage schon, Exit 2.
- **INV-08:** `sdd quality init --preset X` führt nichts aus, nennt `sdd stack apply <vorlage> --only quality` (`python` → `python-cli`) und endet mit Exit 1. `blueprint/presets/quality/` gibt es nicht mehr.
- **INV-09:** Der Blueprint liefert `python-cli` und `python-fastapi`; beide erfüllen CON-0227, und ein frisch damit initialisiertes Projekt hat einen FR-markierten Skeleton-Test, der mit der Referenz-Toolchain grün ist.
