---
id: CON-0221
title: "Bench-Matrix und Suite"
type: data
format: json-schema
spec: SPEC-0056
version: 0.2.0
status: approved
artifact: ".sdd/contracts/data/bench-matrix-und-suite.schema.json"
tests: ["TST-0250"]
---

# Contract: Bench-Matrix und Suite

> **Spec:** SPEC-0056 · **Typ:** Daten (JSON Schema) · **Status:** approved

## Zweck

Beschreibt `bench/matrix.yaml` (`$defs/matrix`) und `bench/suites/<name>.yaml` (`$defs/suite`) aus SPEC-0056 FR-01, FR-03 bis FR-05.

## Garantien

Das Schema im Artifact ist verbindlich; `sdd bench run` lehnt ungültige Dateien mit Exit 2 ab, bevor ein Aufruf erfolgt.

## Invarianten

- **INV-01:** Eine Belegung ordnet Rollen einen Profilnamen aus `llm.profiles` zu, optional mit Variante (`profil@variante`); `*` gilt für alle nicht genannten Rollen der Pipeline. Der Profilname `claude` ist kein Sonderfall, sondern ein normales Profil (z. B. `provider: claude-cli`).
- **INV-02:** Eine Variante ist ein Satz Profil-Parameter (CON-0212), der die Parameter des Profils überschreibt. Unbekannte Profile oder Varianten sind Fehler. Die Variante wirkt nur im Benchmark; in `config.yaml` entsteht daraus nie eine Rollenbelegung mit `profile` und eigenen Parametern zugleich (CON-0212 INV-01, siehe CON-0224 INV-07).
- **INV-03:** `sweep` erzeugt je Profil eine Belegung `sweep-<profil>` (Rolle aus `sweep.role` mit dem Profil, übrige Rollen aus der ersten Belegung bzw. der Config). Belegungen haben eindeutige Namen.
- **INV-04:** Eine Suite nennt `kind`; `sdd bench run` findet die Suite-Art über eine Registry (unbekannte Art: Exit 2). `kind: regen` verlangt `commit`, `test_command` und `tasks` mit Modul und Unit-Tests; `kind: roles` nennt optional `roles` (Default alle fünf Pipeline-Rollen) und `runs`.
- **INV-05:** `budget.max_tokens` und `budget.max_claude_tokens` gelten je Lauf; `T_claude` zählt die Tokens aller Rollen mit Provider `claude-cli` oder `anthropic`.

## Seit SPEC-0063 (0.2.0)

`kind: e2e` verlangt `fixture`, `specs` und `test_command`; optional `isolation` (Default `dir`) und `run_timeout_seconds` (CON-0226 INV-01).
