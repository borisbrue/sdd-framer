---
id: CON-0011
project: ""
title: "AGENTS.md – Struktur und Vollständigkeit"
type: data
format: markdown
spec: SPEC-0004
version: 0.1.0
status: draft
artifact: ""
tests: ["TST-0011"]
---

# Contract: AGENTS.md – Struktur und Vollständigkeit

> **Spec:** SPEC-0004 · **Typ:** Daten/Schema · **Status:** draft

## Zweck

Dieser Contract definiert die Pflichtstruktur einer `AGENTS.md`-Datei im
Projekt-Root. AGENTS.md ist das Kontextdokument für Code-generierende Agenten
und MUSS alle Pflicht-Sektionen enthalten, damit ein Agent korrekt arbeiten kann.

## Garantien

### G-01: Datei-Ort

`AGENTS.md` MUSS im Projekt-Root (gleiches Verzeichnis wie `.sdd/`) liegen.

### G-02: Pflicht-Sektionen

Eine valide `AGENTS.md` MUSS alle folgenden H2-Überschriften enthalten:

| Sektion                    | Pflicht | Beschreibung                                     |
|----------------------------|---------|--------------------------------------------------|
| `## Service-Zweck`         | ja      | Was tut der Service?                             |
| `## Architektur`           | ja      | Architektur-Pattern und Schichten                |
| `## Verzeichnisstruktur`   | ja      | Wichtigste Verzeichnisse und Zweck               |
| `## Externe Abhängigkeiten`| ja      | Externe Services/APIs mit Env-Variablen          |
| `## Build- und Start-Befehle` | ja   | Install, Dev, Test, Build-Befehle                |
| `## Linting- und Formatierungsregeln` | ja | Linter, Formatter, kritische Regeln      |
| `## Konventionen`          | ja      | Naming, Commit-Format, Fehlerbehandlung          |
| `## SDD-Kontext`           | ja      | Verweis auf Specs, Contracts, Holdout            |

### G-03: Keine Placeholder

Sektionen die nur Kommentare oder `<!-- ... -->` enthalten, gelten als
**unvollständig** und lösen in `sdd validate` eine Warnung aus.

### G-04: SDD-Kontext-Sektion

Die Sektion `## SDD-Kontext` MUSS einen expliziten Hinweis enthalten, dass
`.sdd/holdout/` vom Agenten **nicht gelesen werden darf**.

### G-05: CLI-Erzeugung

`sdd new agents-md` erzeugt ein AGENTS.md-Skeleton im Projekt-Root basierend
auf dem Template unter `.sdd/templates/agents-md/default.md`.
Der Befehl DARF eine bestehende `AGENTS.md` NICHT ohne Warnung überschreiben.

## Invarianten

- **INV-01:** Pro Projekt gibt es genau eine `AGENTS.md` im Root.
- **INV-02:** `AGENTS.md` ist nicht Teil des HOL-Isolation-Konzepts – der Code-Agent darf sie lesen.
- **INV-03:** `sdd validate` prüft nur die Anwesenheit der Pflicht-Sektionen, nicht den Inhalt.

## Begriffe

| Begriff      | Definition                                                               |
|--------------|--------------------------------------------------------------------------|
| AGENTS.md    | Markdown-Dokument mit Repository-Kontext für Code-generierende Agenten  |
| Sektion      | H2-Überschrift (`## ...`) plus dazugehöriger Inhalt in AGENTS.md        |
| Placeholder  | Leerer Sektionsinhalt oder reiner HTML-Kommentar ohne realen Inhalt      |
