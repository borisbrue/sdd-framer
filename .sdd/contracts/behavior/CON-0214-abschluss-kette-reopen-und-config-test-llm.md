---
id: CON-0214
title: "Abschluss-Kette, reopen und config test-llm"
type: behavior
format: gherkin
spec: SPEC-0061
version: 0.2.0
status: approved
artifact: ".sdd/contracts/behavior/abschluss-kette-reopen-und-config-test-llm.feature"
tests: ["TST-0243"]
---

# Contract: Abschluss-Kette, reopen und config test-llm

> **Spec:** SPEC-0061 · **Typ:** Verhalten (Gherkin) · **Status:** approved

## Zweck

Legt die Abschluss-Kette von `sdd pipeline run --auto` fest (`holdout`, `finalize`,
`automerge`), das S3-Command `reopen` und das Verhalten von `sdd config test-llm` (SPEC-0061 FR-08
bis FR-10).

## Garantien

Die Szenarien im Artifact (`.sdd/contracts/behavior/abschluss-kette-reopen-und-config-test-llm.feature`) sind **ausführbare Spezifikation**. Jedes Szenario MUSS durch
einen automatisierten Test (pytest) abgedeckt sein; LLM-Rollen laufen gegen den Fake-LLM-Server,
Session-Rollen werden im Test durch Dateischreiben und `sdd pipeline done` gespielt.

## Invarianten

- **INV-01:** Die Kette kommt aus `pipeline.auto_steps` (Default `[holdout, finalize, automerge]`)
  und gilt nur mit `--auto`; ohne `--auto` läuft nach S3 nur `finalize`. Jeder Schritt meldet
  `ok`, `failed` oder `n/a` mit Grund als Ereignis `gate` in `events.jsonl`.
- **INV-02:** `holdout` läuft vor S3 über die bestehende Holdout-Evaluation (unverändert) und
  schreibt ihr Ergebnis (Szenarien bestanden/fehlgeschlagen, Quote) in die Fakten der S3-Anfrage.
  Holdout-Inhalte gelangen nie in den Kontext einer Rolle, nur IDs, Titel und Ergebnis in die
  S3-Fakten; die Isolation aus CON-0064/CON-0009 gilt unverändert.
- **INV-03:** `reopen` (CON-0212) setzt die genannten Tasks auf `red`, gibt den Hinweis als
  `history` an die nächsten Aufrufe und fragt danach S3 erneut an; mehr als `pipeline.max_reopen`
  Wiedereröffnungen führen zu `halted`. Unbekannte Task-IDs machen das Command ungültig.
- **INV-04:** `finalize` nutzt den bestehenden `SpecFinalizer`; `automerge` entscheidet mit der
  bestehenden Autonomie-Logik (`auto_merge_allowed`) und schreibt das Ergebnis in die
  Autonomie-Statistik. Ohne Git-Repository oder PR ist `automerge` `n/a`.
- **INV-05:** `sdd config test-llm` prüft jeden unterschiedlichen Endpunkt aus `llm.profiles` und
  `llm.roles` genau einmal mit einem kurzen Aufruf über die Provider-Factory; `session` wird
  übersprungen. Exit 1, wenn ein geprüfter Endpunkt nicht antwortet, sonst 0.
- **INV-06:** Der Zustand der Kette steht nicht in neuen Feldern von `state.json`: Schritte melden
  sich als Ereignis `gate`, Wiedereröffnungen stehen in `decisions.jsonl`. `reopen` ändert nur den
  Zustand des Runs, nie die Gate-Phasen der Spec (CON-0025/CON-0030).
- **INV-07:** `finalize` ruft `SpecFinalizer` mit derselben Container-Behandlung wie `sdd finalize`
  (CON-0065); die Kette fügt keinen eigenen Container-Lebenszyklus hinzu.
- **INV-08:** `sdd config test-llm` gehört zur Befehlsfamilie `sdd config` (CON-0104). Meldet ein
  Provider keine Usage (z. B. `claude-cli` ohne Usage-Block), gibt die Ausgabe „Reasoning:
  unbekannt“ aus; das ist kein Fehler.
