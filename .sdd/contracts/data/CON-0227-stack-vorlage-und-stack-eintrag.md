---
id: CON-0227
title: "Stack-Vorlage und stack-Eintrag"
type: data
format: json-schema
spec: SPEC-0057
version: 0.1.0
status: draft
artifact: ".sdd/contracts/data/stack-vorlage-und-stack-eintrag.schema.json"
tests: ["TST-0256"]
---

# Contract: Stack-Vorlage und stack-Eintrag

> **Spec:** SPEC-0057 · **Typ:** Daten (JSON Schema) · **Status:** draft

## Zweck

Beschreibt `stack.yaml` einer Vorlage (`$defs/stack`) und einen Eintrag der Liste `stack:` in `config.yaml` (`$defs/entry`), SPEC-0057 FR-01, FR-03, FR-06.

## Garantien

Das Schema ist verbindlich; `sdd stack list|apply` lehnen ungültige Vorlagen mit Exit 2 ab, `sdd config validate` meldet ungültige Einträge.

## Invarianten

- **INV-01:** Eine Vorlage ist ein Verzeichnis `<name>/` mit `stack.yaml` (Name gleich Verzeichnisname), `files/` und optional `agents-md/*.md`. Der Kern kennt keine Vorlage mit Namen.
- **INV-02:** Platzhalter stehen als `{{name}}` in Dateiinhalten und Pfaden unter `files/`; jeder verwendete Platzhalter ist in `placeholders` deklariert, sonst ist die Vorlage ungültig.
- **INV-03:** `requires` nennt Werkzeuge mit einem Befehl, der die Version ausgibt; `min` wird mit der ersten Zahlenfolge der Ausgabe verglichen. `verify` nennt zusätzliche Prüfbefehle mit Platzhaltern.
- **INV-04:** `stack:` in `config.yaml` ist immer eine Liste. Ein Eintrag hält Name, Version, Quelle, die verwendeten Platzhalterwerte und je angewendeter Datei (Pfad relativ zum Projekt) den Hash `sha256:` des angewendeten Inhalts.
