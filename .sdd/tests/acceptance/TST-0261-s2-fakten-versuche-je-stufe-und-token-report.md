---
id: TST-0261
title: "S2-Fakten, Versuche je Stufe und Token-Report"
level: acceptance            # unit | integration | contract | acceptance | performance | property
spec: SPEC-0066
contract: CON-0232
status: implemented
framework: pytest
artifact: "tests/acceptance/test_con_0232.py"
tags: [pipeline, supervisor, usage]
---

# Test: S2-Fakten, Versuche je Stufe und Token-Report

> **Level:** acceptance · **Spec:** SPEC-0066 · **Contract:** CON-0232 · **Status:** implemented

## Was wird geprüft?

S2 nennt nach Review-Ablehnungen deren Befunde; Versuche zählen je Stufe, eine einzelne
Review-Ablehnung eskaliert nicht; `files: []` des Implementers ist ein gültiger Versuch ohne
Schreiben; der Report weist Cache-Tokens aus und rechnet sie in den Claude-Anteil ein.

## Vorbedingungen

- Für die Pipeline-Szenarien: `openai` installiert (FakeLLM), sonst übersprungen; im
  Dev-Container laufen sie.

## Ablauf

1. Adapter `review_facts` direkt (Übernahme, Kürzung, kein Review).
2. `build_report` gegen eine `token_usage`-Tabelle mit Cache-Werten und einer Rolle ohne Usage.
3. Pipeline-Läufe mit Fake-Rollen für die Szenarien 1–4 aus dem Feature.

## Erwartetes Ergebnis

- S2-Anfrage enthält `facts.review` mit Befund `src/start.sh` Zeile 4; schemagültig.
- GREEN-Gate dreimal rot: S2 ohne `facts.review`, `stage_attempts.implementation` 3.
- Eine Ablehnung: keine S2-Anfrage, `stage_attempts` test 1, implementation 1, review 2.
- `files: []`: Datei unverändert, keine Schreibablehnung, zweites Review sieht den Task-Diff.
- Report: Cache-Read 900, Cache-Write 300, Claude-Anteil 1300/2800, `supervisor` ohne Usage.

## Negativfälle / Edge Cases

- Mehr als 20 Befunde, Begründung über 600 Zeichen, unbekannte Felder, `line` 0.
- Run ohne `stage_attempts` (vor SPEC-0066) bleibt gültig.

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0232:

- [x] INV-01 `facts.review` nach Review-Ablehnung, sonst nicht
- [x] INV-02 Stufenzähler, neue Runde nach Ablehnung
- [x] INV-03 `files: []` ohne Schreiben, Review mit Task-Diff
- [x] INV-04 Cache-Spalten, Claude-Anteil, Rollen ohne Usage

## Hinweise zur Implementierung

Fake-Rollen über `tests/support/fake_llm.py` und `tests/support/pipeline_project.py`.
