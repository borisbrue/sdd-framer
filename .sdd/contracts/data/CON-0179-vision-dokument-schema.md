---
id: CON-0179
project: PRJ-0001
title: ".sdd/vision.md Dokumentstruktur und Schema"
type: data
format: markdown
spec: SPEC-0046
version: 0.1.0
status: approved
artifact: ""
tests: ["TST-0205"]
---

# Contract: .sdd/vision.md Dokumentstruktur und Schema

> **Spec:** SPEC-0046 · **Typ:** Data · **Status:** draft

## Zweck

Definiert die verbindliche Struktur von `.sdd/vision.md` — das einzige
Vision-Dokument pro Projekt. Alle Befehle der Vision Edition lesen und schreiben
dieses Dokument nach diesem Schema.

## Invarianten

- **INV-01:** Pro Projekt existiert genau eine Vision-Datei: `.sdd/vision.md`.
- **INV-02:** Die Abschnitt-Überschriften `## Vision`, `## Zielgruppe`,
  `## Tech Stack`, `## Competitive Landscape`, `## Kernprobleme`,
  `## Features` und `## Tasks` sind verpflichtend vorhanden (auch wenn leer).
- **INV-03:** Der Inhalt aller Abschnitte außer `## Features` und `## Tasks`
  ist Freitext (Markdown). Keine Pflichtstruktur innerhalb dieser Abschnitte.
- **INV-04:** `## Features` enthält ausschließlich nummerierte Listeneinträge
  im Format `N. **Titel** – Beschreibung` (Beschreibung optional).
  Challenge-Ergebnisse folgen direkt nach dem Eintrag als Blockquote-Zeilen.
- **INV-05:** `## Tasks` enthält ausschließlich Checkbox-Listeneinträge
  im Format `- [ ] Titel` bzw. `- [x] Titel` (für erledigte Tasks).
- **INV-06:** Das Dokument hat keinen YAML-Frontmatter-Block — es ist reines
  Markdown ohne Metadaten-Header.

## Dokumentstruktur

```markdown
# <Projektname> – Produktvision

## Vision

<Freitext: Vision Statement>

## Zielgruppe

<Freitext: Wer sind die Nutzer?>

## Tech Stack

<Freitext: Verwendete Technologien>

## Competitive Landscape

<Freitext: Mitbewerber und Abgrenzung>

## Kernprobleme

<Freitext: Welche Probleme löst das Produkt?>

## Features

1. **<Titel>** – <Beschreibung>
   > LLM Challenge: Aufwand: <low|medium|high|unknown> · <Begründung>
   > Fallstricke: <Text>
   > Code Challenge: <Dateiliste oder "Keine betroffenen Dateien gefunden.">

2. **<Titel>**

## Tasks

- [ ] <Task-Titel>
- [x] <Erledigter Task-Titel>
```

## Beispiel (minimal – Skelett-Dokument)

```markdown
# MeinProjekt – Produktvision

## Vision

## Zielgruppe

## Tech Stack

## Competitive Landscape

## Kernprobleme

## Features

## Tasks
```

## Beispiel (ausgefüllt)

```markdown
# SDD-Framer – Produktvision

## Vision

Ein CLI-Tool, das Entwickler durch strukturierte Spec-Driven Development führt.

## Zielgruppe

Solo-Entwickler und kleine Teams, die strukturiert bauen wollen.

## Tech Stack

Python 3.13, Typer, Rich, Anthropic API

## Competitive Landscape

GitHub Copilot (kein SDD-Prozess), Linear (kein Code-Kontext)

## Kernprobleme

Ideen werden direkt zu Code ohne Spec — führt zu technischen Schulden.

## Features

1. **Offline-Modus** – App ohne Internet nutzbar
   > LLM Challenge: Aufwand: high · Erfordert vollständigen State-Sync
   > Fallstricke: Konfliktauflösung bei gleichzeitiger Online-Bearbeitung
   > Code Challenge: sdd_cli/api/client.py, sdd_cli/cache/

2. **Dark Mode**

## Tasks

- [ ] README aktualisieren
- [x] CI-Pipeline einrichten
```
