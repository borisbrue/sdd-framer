---
id: TST-0263
title: "Aufteilung von System-Prompt und Prompt im RoleRunner"
level: acceptance            # unit | integration | contract | acceptance | performance | property
spec: SPEC-0068
contract: CON-0234
status: implemented        # planned | implemented | passing | failing | skipped
framework: pytest
artifact: "tests/acceptance/test_con_0234.py"
tags: [pipeline, llm, cache]
---

# Test: Aufteilung von System-Prompt und Prompt im RoleRunner

> **Level:** acceptance · **Spec:** SPEC-0068 · **Contract:** CON-0234 · **Status:** implemented

## Was wird geprüft?

Pipeline-Läufe über die echte CLI gegen den OpenAI-kompatiblen Fake-Server
(`tests/support/fake_llm.py`). Er zeichnet die echten `messages` auf; geprüft wird, was als
System- und was als Nutzer-Nachricht ankommt.

## Vorbedingungen

- `openai` installiert (sonst übersprungen), Testprojekt aus `tests/support/pipeline_project.py`.

## Ablauf

1. Projekt mit einer Task anlegen, Rollen-Antworten vorbereiten.
2. `sdd pipeline run` ausführen.
3. Aufgezeichnete Anfragen je Rolle auswerten.

## Erwartetes Ergebnis

- Drei rote Implementer-Versuche: System-Nachrichten byte-gleich, mit Spec, Contracts,
  AGENTS.md, Task, Testdatei, aktuellem Dateiinhalt; ohne Nonce und Testausgabe.
- Zweiter Versuch: Nutzer-Nachricht mit Testausgabe und history, Nonce am Ende, ohne Spec.
- Reviewer: Diff im Prompt, Spec im System-Prompt.
- Supervisor: Entscheidungsanfrage am Anfang der Nutzer-Nachricht.
- Decomposer ohne history: Nutzer-Nachricht = purpose + Nonce.
- Gleicher `prompt_hash` bei gleichen Quellen (RoleRunner direkt).

Mutationsnachweis (2026-10-06): alles im Prompt, `current_files` als `volatile`, Hash ohne
System-Prompt, Leerzeilen ohne stabile Quellen lassen jeweils mindestens einen Test rot werden;
für TST-0262 ebenso Datei nicht gelöscht und Modus 0644.

## Negativfälle / Edge Cases

- Rolle ohne wechselnde Quellen (Decomposer, erster Versuch).

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0234:

- [x] INV-01 Einteilung der Quellen
- [x] INV-02 Aufbau des System-Prompts
- [x] INV-03 Aufbau des Prompts
- [x] INV-04 byte-gleich bei gleichen Quellen
- [x] INV-05 prompt_hash

Lokal braucht der Lauf `openai`: `uv run --extra ai pytest tests/acceptance/test_con_0234.py`.

## Hinweise zur Implementierung

Muster wie `tests/acceptance/test_con_0232.py` (`make_pipeline_project`, `FakeLLM`).
