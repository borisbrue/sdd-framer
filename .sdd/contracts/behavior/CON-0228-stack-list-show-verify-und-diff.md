---
id: CON-0228
title: "stack list, show, verify und diff"
type: behavior
format: gherkin
spec: SPEC-0057
version: 0.1.0
status: approved
artifact: ".sdd/contracts/behavior/stack-list-show-verify-und-diff.feature"
tests: ["TST-0257"]
---

# Contract: stack list, show, verify und diff

> **Spec:** SPEC-0057 · **Typ:** Verhalten (Gherkin) · **Status:** approved

## Zweck

Legt die lesenden und prüfenden Befehle fest (SPEC-0057 FR-02, FR-05, FR-06). Keiner verändert Dateien.

## Garantien

Die Szenarien im Artifact (`.sdd/contracts/behavior/stack-list-show-verify-und-diff.feature`) sind **ausführbare Spezifikation**.

## Invarianten

- **INV-01:** Quellenkette: Projekt (`.sdd/stacks/`), Nutzer (`~/.config/sdd/stacks/`, über `SDD_STACKS_HOME` überschreibbar), Blueprint. Die erste Quelle mit dem Namen gewinnt; `list` zeigt verdeckte Vorlagen mit Hinweis.
- **INV-02:** `show NAME` zeigt Version, Quelle, Sprachen, Werkzeuge, Platzhalter, Prüfpunkte und die Dateiliste; unbekannter Name: Exit 2.
- **INV-03:** `verify` prüft alle angewendeten Vorlagen: Werkzeuge (`requires`, Mindestversion), `sdd quality doctor` ohne Fehler, mindestens ein FR-markierter Test im JUnit der Test-Sonde, `sdd arch check` läuft, Prüfpunkte aus `verify`. Pflichtpunkte scheitern mit Installationshinweis und Exit 1, optionale nur als Warnung. Es werden nur deklarierte Befehle und Sonden ausgeführt.
- **INV-04:** `diff [NAME]` ordnet jede Datei einer angewendeten Vorlage ein: `unverändert`, `vom Projekt geändert` (Hash ≠ Memento), `in der Vorlage neu oder geändert` (Vorlage ≠ Memento) oder `beides`; fehlende Projektdateien erscheinen als `im Projekt entfernt`. Ohne angewendete Vorlage: Hinweis, Exit 0.
