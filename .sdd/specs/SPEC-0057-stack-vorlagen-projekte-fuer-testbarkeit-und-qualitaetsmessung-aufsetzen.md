---
id: SPEC-0057
title: "Stack-Vorlagen: Projekte für Testbarkeit und Qualitätsmessung aufsetzen"
type: feature
status: draft
owner: "Boris"
created: 2026-09-25
updated: 2026-09-25
version: 0.1.0
priority: low
tags: [stack, templates, language-agnostic, quality, init]
depends_on: [SPEC-0054]
contracts: []
tests: []
---

# Stack-Vorlagen: Projekte für Testbarkeit und Qualitätsmessung aufsetzen

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

sdd-framer soll unabhängig von der Programmiersprache sein. Mit SPEC-0054 ist die Messung von
Anforderungserfüllung, Architekturtreue und Codequalität auf Sonden und Austauschformate umgestellt:
Das Projekt entscheidet, welche Werkzeuge es nutzt, und sdd rechnet nur. Damit verschiebt sich die
Arbeit in jedes Projekt. Es muss seine Testbarkeit so aufsetzen, dass Tests FR-markiert als JUnit
berichten, Linter SARIF ausgeben und ein Extraktor Abhängigkeitskanten liefert.

Diese Einrichtung ist pro Tech-Stack immer ähnlich und schwer richtig hinzubekommen. Heute steckt
Sprachwissen verstreut im Kern (`test_languages.py`, `test_generator.py`, Blueprint-Dockerfile).
Stack-Vorlagen bündeln das Wissen „so setzt man Stack X auf, damit das Projekt gut testbar und messbar
ist“, ohne es in den Kern zu ziehen. Nach dem Anwenden gehören die Dateien dem Projekt und
entwickeln sich dort weiter. sdd hilft nur beim Einrichten, Prüfen und beim Vergleich mit neueren
Vorlagenversionen.

## 2. Zielsetzung

**Primärziel:** Ein Projekt bekommt mit einem Befehl eine bewährte Einrichtung für seinen Stack
(Sonden, Architektur-Gerüst, Test-Konventionen, Dev-Container, AGENTS.md-Abschnitte) und kann
jederzeit prüfen, ob seine Toolchain für sdd messbar ist.

**Erfolgskriterien (messbar):**
- [ ] `sdd init --stack python-fastapi` erzeugt ein Projekt, in dem `sdd stack verify` ohne
      weitere Handgriffe grün ist (sofern die Werkzeuge installiert sind).
- [ ] Ein funktionierendes Projekt lässt sich mit `sdd stack extract` in eine neue Vorlage
      überführen, sodass die Erfahrungen aus dem Projekt zurück in die Vorlage fließen.
- [ ] Eine Vorlage für einen neuen Stack entsteht ohne Änderung am sdd-Kern.

**Nicht-Ziele (explizit):**
- Kein Installieren von Sprachen, Paketen oder Werkzeugen; sdd zeigt nur Installationshinweise.
- Kein App-Generator. Außer einem minimalen „Walking Skeleton“ mit einem FR-markierten Test enthält
  eine Vorlage keinen Geschäftscode.
- Keine laufende Pflege der Werkzeugketten fremder Stacks durch sdd-framer.

## 3. Architektur & Design Patterns

### Vorlage als Daten (Prototype)
```
stacks/python-fastapi/
├── stack.yaml               # Name, Version, Beschreibung, Sprachen, benötigte Werkzeuge
├── files/                   # wird ins Projekt kopiert (mit Platzhaltern)
│   ├── .sdd/quality.yaml    # Sonden nach SPEC-0054
│   ├── .sdd/architecture.yaml   # typische Schichten des Stacks + Basisregeln
│   ├── .sdd/quality/…       # Konverter (z. B. lizard → sdd-metrics)
│   ├── .sdd/Dockerfile      # Dev-Container mit Toolchain
│   ├── tests/test_skeleton.py   # ein FR-markierter Beispieltest
│   └── …                    # Test-Konfiguration (pytest.ini, FR-Marker-Plugin)
└── agents-md/               # Abschnitte für AGENTS.md: Build-/Test-/Lint-Befehle, Taste Invariants mit [ARCH-xx]
```

`stack.yaml`:
```yaml
name: python-fastapi
version: 1.0.0
description: "FastAPI-Service mit Schichten domain/service/api/persistence"
languages: [python]
requires:
  - { tool: python, version_command: "python --version", min: "3.11" }
  - { tool: ruff,   version_command: "ruff --version", install_hint: "uv tool install ruff" }
  - { tool: lizard, version_command: "lizard --version", install_hint: "uv tool install lizard", optional: true }
placeholders: [project_name, package_name]
```

### Quellen (Chain of Responsibility)
Gesucht wird in dieser Reihenfolge: Projekt (`.sdd/stacks/`), Nutzer (`~/.config/sdd/stacks/`),
Git-URL (`--from git+https://…`) und Blueprint.

## 4. Funktionale Anforderungen

- **FR-01:** Eine Stack-Vorlage ist ein Verzeichnis mit `stack.yaml` nach
  `contracts/data/stack.schema.json`, einem Verzeichnis `files/` und optional `agents-md/`.
- **FR-02:** `sdd stack list` und `sdd stack show NAME` zeigen die verfügbaren Vorlagen aus allen
  Quellen mit Version, Sprachen und benötigten Werkzeugen.
- **FR-03:** `sdd stack apply NAME [--dry-run] [--yes]` kopiert `files/` ins Projekt, ersetzt die
  Platzhalter und fügt die `agents-md/`-Abschnitte zwischen Markierungen in AGENTS.md ein.
  Vorhandene, abweichende Dateien werden nicht überschrieben. Stattdessen entsteht `<datei>.new`,
  und ein Diff wird angezeigt (Verhalten wie `sdd upgrade`). Angewendete Vorlage und Version werden
  in `config.yaml` unter `stack:` festgehalten.
- **FR-04:** `sdd init --stack NAME` wendet die Vorlage direkt nach der Initialisierung an.
- **FR-05:** `sdd stack verify` prüft die Einrichtung:
  - benötigte Werkzeuge vorhanden, mit Versionen;
  - `sdd quality doctor` (SPEC-0054) ohne Fehler;
  - der Skeleton-Test läuft und erscheint FR-markiert im JUnit-Ergebnis;
  - `sdd arch check` läuft.

  Die Ausgabe ist eine Checkliste mit Installationshinweisen. Exit-Code 1, wenn ein Pflichtpunkt
  fehlschlägt.
- **FR-06:** `sdd stack diff` vergleicht die Projektdateien mit der angewendeten und der neuesten
  Vorlagenversion und zeigt, was das Projekt selbst weiterentwickelt hat und was die Vorlage Neues
  bietet. Übernommen wird nur über `sdd stack apply` (mit `.new`-Dateien).
- **FR-07:** `sdd stack extract NAME [--to user|project]` erzeugt aus dem aktuellen Projekt eine
  Vorlage: `quality.yaml`, `architecture.yaml` (Schichten ohne projektspezifische Pfade, soweit
  generalisierbar), Konverter, Dockerfile, Test-Konfiguration und die markierten AGENTS.md-
  Abschnitte. Die Vorlage wird zur Nachbearbeitung geöffnet.
- **FR-08:** Der Blueprint liefert zunächst die Vorlagen `python-cli` (aus sdd-framer abgeleitet)
  und `python-fastapi` (Grundlage des Benchmark-Fixtures `todo-service` aus SPEC-0056).
- **FR-09:** Sprachwissen im Kern, das nur der Projekteinrichtung dient, wird nicht erweitert. Neue
  Stacks kommen ausschließlich als Vorlage.

## 5. Nicht-funktionale Anforderungen

| Kategorie        | Anforderung                                                            |
|------------------|------------------------------------------------------------------------|
| Sicherheit       | Vorlagen aus Git-URLs werden vor dem Anwenden mit Dateiliste und Diff angezeigt; `--yes` ist nötig, um ohne Rückfrage anzuwenden. Vorlagen führen beim Anwenden keine Befehle aus. |
| Idempotenz       | Zweimaliges `apply` derselben Version ändert nichts.                    |
| Sprachneutralität | Kern kennt keine Vorlage mit Namen; alle Vorlagen sind Daten.         |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Stack-Vorlagen

  Scenario: Neues Projekt mit Vorlage
    Given ein leeres Verzeichnis
    When ich "sdd init --name Demo --stack python-fastapi" ausführe
    And danach "sdd stack verify"
    Then meldet verify für jede Pflichtprüfung "ok" oder einen Installationshinweis

  Scenario: Projekt hat die Vorlage weiterentwickelt
    Given das Projekt hat in .sdd/quality.yaml eine zusätzliche Sonde "coverage"
    And die Vorlage python-fastapi erscheint in Version 1.1.0
    When ich "sdd stack apply python-fastapi" ausführe
    Then wird .sdd/quality.yaml nicht überschrieben
    And es entsteht .sdd/quality.yaml.new mit Diff-Ausgabe
```

## 7. Edge Cases & Fehlerfälle

- Projekt nutzt mehrere Stacks (z. B. Backend Python, Frontend TypeScript): `stack:` in
  `config.yaml` ist eine Liste. Sonden und Schichten werden mit Präfix des Stacks zusammengeführt.
  Bei Namenskonflikten bricht der Befehl ab und zeigt den Konflikt an.
- Platzhalter fehlt beim Anwenden: nachfragen bzw. mit `--set key=value` setzen.
- Vorlage verlangt ein Werkzeug, das fehlt: `apply` warnt, bricht aber nicht ab; `verify` schlägt
  fehl.

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert?                                  |
|-------------|----------|-------------------------------------------------------|
| CON-XXXX    | data     | `stack.schema.json`                                   |
| CON-XXXX    | behavior | `sdd stack list|show|apply|verify|diff|extract`, `sdd init --stack` |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level       | Was prüft der Test?                                          |
|----------|-------------|--------------------------------------------------------------|
| TST-XXXX | unit        | Quellenauflösung, Platzhalter, AGENTS.md-Merge mit Markierungen |
| TST-XXXX | integration | apply/diff/extract auf tmp-Projekten, Idempotenz, `.new`-Verhalten |
| TST-XXXX | acceptance  | Gherkin-Szenarien aus Abschnitt 6                            |

## 10. Offene Fragen

- [ ] Soll das vorhandene Sprachwissen in `test_languages.py` und `test_generator.py` langfristig in
      die Vorlagen wandern, sodass der Kern ganz ohne Sprachwissen auskommt? Das wäre eine eigene
      Migrations-Spec.
- [x] Eigenes Repo für Vorlagen → nein, die Vorlagen liegen im Haupt-Repo unter
      `tool/sdd_cli/blueprint/stacks/` und werden mit sdd-framer versioniert (entschieden
      2026-09-25). Git-URLs bleiben als Quelle für projekt- oder nutzereigene Vorlagen erhalten.
- [ ] Wird eine Rust-Vorlage (`rust-cargo`, z. B. aus sddit extrahiert) die erste Vorlage außerhalb
      von Python?

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung            |
|------------|---------|---------------|---------------------|
| 2026-09-25 | 0.1.0   | Boris, Claude | Initiale Erstellung |
