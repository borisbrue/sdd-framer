---
id: SPEC-0057
title: "Stack-Vorlagen: Projekte für Testbarkeit und Qualitätsmessung aufsetzen"
type: feature
status: implemented
owner: "Boris"
created: 2026-09-25
updated: 2026-09-27
version: 0.2.1
priority: low
tags: [stack, templates, language-agnostic, quality, init]
depends_on: [SPEC-0054]
contracts:
- CON-0227
- CON-0228
- CON-0229
tests:
- TST-0256
- TST-0257
- TST-0258
fr_test_map:
  FR-01: [TST-0256]
  FR-02: [TST-0257]
  FR-03: [TST-0258]
  FR-04: [TST-0258]
  FR-05: [TST-0257]
  FR-06: [TST-0257]
  FR-07: [TST-0258]
  FR-08: [TST-0256, TST-0258]
  FR-09: [TST-0258]
  FR-10: [TST-0258]
---

# Stack-Vorlagen: Projekte für Testbarkeit und Qualitätsmessung aufsetzen

> **Status:** approved · **Owner:** Boris · **Version:** 0.2.0

## 1. Kontext & Motivation

sdd-framer soll unabhängig von der Programmiersprache sein. Seit SPEC-0054 misst sdd über Sonden und
Austauschformate: Das Projekt entscheidet, welche Werkzeuge es nutzt, sdd rechnet nur. Damit muss
jedes Projekt seine Testbarkeit so aufsetzen, dass Tests FR-markiert als JUnit berichten, Linter
SARIF ausgeben und ein Extraktor Abhängigkeitskanten liefert. Diese Einrichtung ist je Stack immer
ähnlich und schwer richtig hinzubekommen.

Stack-Vorlagen bündeln dieses Wissen als Daten, ohne es in den Kern zu ziehen. Nach dem Anwenden
gehören die Dateien dem Projekt; sdd hilft beim Einrichten, Prüfen und beim Vergleich mit neueren
Vorlagenversionen.

Bestand (Review 2026-09-27):

| Baustein | Stand | In dieser Spec |
|----------|-------|----------------|
| Quality-Presets (`sdd quality init --preset python`, `blueprint/presets/quality/python/`) | vorhanden (SPEC-0054), nur Qualitätssonden | gehen in der Vorlage `python-cli` auf; `quality init` wird Verweis |
| `sdd quality doctor`, `sdd arch check` | vorhanden | Bausteine von `sdd stack verify` |
| Fixture `todo-service` (Standardbibliothek, Schichten, JUnit-Runner) | vorhanden (SPEC-0063) | Vorbild für `python-cli` |
| Sprachwissen im Kern (`test_languages.py`, `test_generator.py`) | vorhanden | unverändert, Migration ist eine eigene Spec |

## 2. Zielsetzung

**Primärziel:** Ein Projekt bekommt mit einem Befehl eine bewährte Einrichtung für seinen Stack
(Sonden, Architektur-Gerüst, Test-Konventionen, Dev-Container, AGENTS.md-Abschnitte) und kann
jederzeit prüfen, ob seine Toolchain für sdd messbar ist.

**Erfolgskriterien (messbar):**
- [ ] `sdd init --stack python-cli` erzeugt ein Projekt, in dem `sdd stack verify` ohne weitere
      Handgriffe grün ist, sofern die Werkzeuge installiert sind.
- [ ] Ein funktionierendes Projekt lässt sich mit `sdd stack extract` in eine Vorlage überführen, die
      das Schema erfüllt und sich wieder anwenden lässt.
- [ ] Eine Vorlage für einen neuen Stack entsteht ohne Änderung am sdd-Kern.

**Nicht-Ziele (explizit):**
- Kein Installieren von Sprachen, Paketen oder Werkzeugen; sdd zeigt nur Installationshinweise.
- Kein App-Generator; außer einem „Walking Skeleton“ mit einem FR-markierten Test kein
  Geschäftscode.
- Keine Git-URLs als Quelle und keine Zusammenführung mehrerer Stacks mit Präfixen (später möglich).

## 3. Architektur & Design Patterns

Angenommen (Review 2026-09-27): **Prototype** (Vorlage als Daten), **Chain of Responsibility**
(Quellen), **Memento** (angewendete Version mit Datei-Hashes), **Proxy** (Vorschau vor dem Anwenden
fremder Quellen).

### Vorlage
```
<quelle>/stacks/python-cli/
├── stack.yaml               # Name, Version, Beschreibung, Sprachen, Werkzeuge, Platzhalter, Prüfpunkte
├── files/                   # wird ins Projekt kopiert, Platzhalter {{name}}
│   ├── .sdd/quality.yaml    # Sonden nach SPEC-0054 (Test-Sonde JUnit mit FR-Markern)
│   ├── .sdd/quality/…       # Konverter und Extraktoren
│   ├── .sdd/architecture.yaml, docs/adr/…
│   └── tests/…              # ein FR-markierter Skeleton-Test
└── agents-md/<abschnitt>.md # Abschnitte für AGENTS.md
```

`stack.yaml`:
```yaml
name: python-cli
version: 1.0.0
description: "Python-Kommandozeilenwerkzeug mit Schichten domain/service/persistence/cli"
languages: [python]
requires:
  - {tool: python3, version_command: "python3 --version", min: "3.11"}
  - {tool: ruff, version_command: "ruff --version", install_hint: "uv tool install ruff", optional: true}
placeholders:
  - {name: project_name, description: "Projektname"}
  - {name: package_name, default: "app", description: "Python-Paket"}
verify:
  - {name: "Typprüfung", command: "mypy {{package_name}}", optional: true}
```

### Quellen (Chain of Responsibility)
Projekt (`.sdd/stacks/<name>/`) → Nutzer (`~/.config/sdd/stacks/<name>/`) → Blueprint
(`blueprint/stacks/<name>/`). Die erste Quelle mit dem Namen gewinnt.

### Sprachneutrale Prüfung
`verify` führt nur Befehle aus, die Vorlage oder Projekt deklarieren (`requires`, `verify`, Sonden
in `quality.yaml`). Den Skeleton-Test findet es über die Test-Sonde (JUnit mit FR-Marker), nicht über
Wissen zur Sprache (DIP-Befund).

## 4. Funktionale Anforderungen

- **FR-01:** **Vorlage als Daten.** Eine Vorlage ist ein Verzeichnis mit `stack.yaml` nach
  `stack.schema.json`, `files/` und optional `agents-md/`. Platzhalter stehen als `{{name}}` in
  Dateiinhalten und Pfaden.
- **FR-02:** **Quellen.** `sdd stack list` zeigt alle Vorlagen aller Quellen mit Quelle, Version,
  Sprachen und Werkzeugen; `sdd stack show NAME` zusätzlich Dateiliste, Platzhalter und Prüfpunkte.
  Verdeckte Vorlagen (gleicher Name in späterer Quelle) sind als solche gekennzeichnet.
- **FR-03:** **`sdd stack apply NAME [--dry-run] [--yes] [--set k=v …] [--only quality]`.**
  - Kopiert `files/` mit ersetzten Platzhaltern. Gleiche Dateien bleiben unberührt. Neue Dateien
    werden angelegt. Abweichende Dateien werden nicht überschrieben; stattdessen entsteht
    `<datei>.new` und ein Diff wird angezeigt.
  - Fügt `agents-md/`-Abschnitte zwischen Markierungen
    `<!-- sdd-stack:NAME:ABSCHNITT -->` … `<!-- /sdd-stack:NAME:ABSCHNITT -->` in AGENTS.md ein bzw.
    ersetzt sie dort.
  - Hält in `config.yaml` unter `stack:` (immer eine Liste) Name, Version, Quelle und je Datei den
    Hash des angewendeten Inhalts fest (Memento).
  - Zweimaliges Anwenden derselben Version ändert nichts.
  - Fehlende Platzhalter kommen aus dem Default, `--set` oder einer Rückfrage; ohne Wert Exit 2.
  - Vorlagen aus Projekt- oder Nutzerquellen zeigen vor dem Schreiben Dateiliste und Diff
    (Vorschau) und verlangen eine Bestätigung oder `--yes`.
  - `--only quality` beschränkt auf `.sdd/quality.yaml` und `.sdd/quality/**`.
  - Fehlende Werkzeuge ergeben eine Warnung, keinen Abbruch.
  - Beim Anwenden werden keine Befehle der Vorlage ausgeführt.
- **FR-04:** **`sdd init --stack NAME`** wendet die Vorlage direkt nach der Initialisierung an;
  `project_name` ist der Projekttitel.
- **FR-05:** **`sdd stack verify`** gibt eine Checkliste mit Installationshinweisen aus, Exit 1,
  wenn ein Pflichtpunkt fehlschlägt:
  - Werkzeuge aus `requires` vorhanden und mindestens in Version `min`;
  - `sdd quality doctor` ohne Fehler;
  - die Test-Sonde liefert mindestens einen FR-markierten Test im JUnit-Ergebnis;
  - `sdd arch check` läuft;
  - die Prüfpunkte aus `verify` der Vorlagen laufen (optionale nur als Warnung).
- **FR-06:** **`sdd stack diff [NAME]`** vergleicht je Datei drei Stände: angewendet (Hash im
  Memento), Projekt und aktuelle Vorlage. Die Ausgabe zeigt je Datei „vom Projekt geändert“, „in
  der Vorlage neu oder geändert“ oder „beides“. Übernommen wird nur über `sdd stack apply` mit
  `.new`-Dateien.
- **FR-07:** **`sdd stack extract NAME [--to user|project]`** erzeugt aus dem Projekt eine Vorlage:
  - Dateien: `.sdd/quality.yaml`, `.sdd/quality/**`, `.sdd/architecture.yaml`, `.sdd/Dockerfile`,
    `docs/adr/**` und die Dateien einer angewendeten Vorlage;
  - die markierten AGENTS.md-Abschnitte;
  - Projektname und, soweit erkennbar, Paketname werden durch Platzhalter ersetzt;
  - `stack.yaml` mit Version `0.1.0`.

  Die Vorlage muss das Schema erfüllen. Der Befehl nennt den Pfad zur Nachbearbeitung;
  vorhandene Vorlagen werden nicht überschrieben.
- **FR-08:** **Blueprint-Vorlagen:**
  - `python-cli`: Standardbibliothek, Schichten `domain`/`service`/`persistence`/`cli`,
    pytest mit FR-Marker-Plugin, ruff, Abhängigkeitsextraktor; übernimmt das bisherige
    Preset `python`.
  - `python-fastapi`: Schichten `domain`/`service`/`api`/`persistence`.

  Beide enthalten einen FR-markierten Skeleton-Test, `architecture.yaml` mit ADR und
  AGENTS.md-Abschnitte. Ein Dockerfile liefern sie nicht: `sdd init` legt `.sdd/Dockerfile` bereits
  an, eine Kopie aus der Vorlage ergäbe nur eine `.new`-Datei.
- **FR-09:** **Presets abgelöst.** `blueprint/presets/quality/` entfällt. `sdd quality init
  --preset X` verweist auf `sdd stack apply X --only quality` (Hinweis, Exit 1, Konvention SPEC-0058).
  Bekannte Preset-Namen werden auf ihre Vorlage abgebildet (`python` → `python-cli`).
- **FR-10:** **Kein neues Sprachwissen im Kern.** Neue Stacks kommen ausschließlich als Vorlage;
  `test_languages.py` und `test_generator.py` bleiben unverändert.

## 5. Nicht-funktionale Anforderungen

| Kategorie        | Anforderung |
|------------------|-------------|
| Sicherheit       | Vorlagen führen beim Anwenden keine Befehle aus; Nicht-Blueprint-Quellen nur nach Vorschau und Bestätigung. |
| Idempotenz       | Zweimaliges `apply` derselben Version ändert nichts. |
| Sprachneutralität | Der Kern kennt keine Vorlage mit Namen (außer der Abbildung alter Preset-Namen in FR-09). |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Stack-Vorlagen

  Scenario: Neues Projekt mit Vorlage
    Given ein leeres Verzeichnis
    When ich "sdd init --name Demo --stack python-cli" ausführe
    And danach "sdd stack verify"
    Then meldet verify für jede Pflichtprüfung "ok" oder einen Installationshinweis

  Scenario: Projekt hat die Vorlage weiterentwickelt
    Given das Projekt hat in .sdd/quality.yaml eine zusätzliche Sonde "coverage"
    And die Vorlage python-cli erscheint in einer neuen Version
    When ich "sdd stack apply python-cli" ausführe
    Then wird .sdd/quality.yaml nicht überschrieben
    And es entsteht .sdd/quality.yaml.new mit Diff-Ausgabe
```

## 7. Edge Cases & Fehlerfälle

- Zwei angewendete Vorlagen liefern dieselbe Datei: die zweite erzeugt `.new`, der Konflikt wird
  gemeldet.
- Platzhalter fehlt: Default, `--set` oder Rückfrage; im nicht interaktiven Modus Exit 2.
- Werkzeug fehlt: `apply` warnt, `verify` schlägt fehl (bei Pflichtwerkzeugen).

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert? |
|-------------|----------|----------------------|
| CON-0227    | data     | `stack.schema.json` und `stack:` in `config.yaml` |
| CON-0228    | behavior | `sdd stack list|show|verify|diff` (lesend und prüfend) |
| CON-0229    | behavior | `sdd stack apply|extract`, `sdd init --stack`, Verweis `quality init --preset` |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level       | Was prüft der Test? |
|----------|-------------|---------------------|
| TST-0256 | unit        | Schema, Quellenkette, Platzhalter, AGENTS.md-Markierungen |
| TST-0257 | acceptance  | list/show/verify/diff |
| TST-0258 | acceptance  | apply/extract/init --stack/Verweis, Idempotenz, `.new`, Blueprint-Vorlagen grün |

## 10. Offene Fragen

- [x] Vorlagen im Haupt-Repo unter `blueprint/stacks/` (2026-09-25).
- [x] Presets gehen in Vorlagen auf (2026-09-27).
- [x] Erste Vorlagen: `python-cli`, `python-fastapi` (2026-09-27).
- [x] Umfang ohne Git-URLs und Präfix-Zusammenführung (2026-09-27).
- [ ] Soll das Sprachwissen in `test_languages.py`/`test_generator.py` langfristig in Vorlagen
      wandern? Eigene Migrations-Spec.
- [ ] Rust-Vorlage (`rust-cargo`, z. B. für sddit) als erste Vorlage außerhalb von Python.

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung |
|------------|---------|---------------|----------|
| 2026-09-25 | 0.1.0   | Boris, Claude | Initiale Erstellung |
| 2026-09-27 | 0.2.0   | Boris, Claude | Review: Presets abgelöst, sprachneutrales verify, Memento mit Hashes, schlanker Umfang, Patterns |
| 2026-09-27 | 0.2.1   | Boris, Claude | Umsetzung: Blueprint-Vorlagen ohne Dockerfile (kommt aus `sdd init`) |
