---
id: CON-0223
title: "Bench-Lauf, Isolation, Suiten roles und regen"
type: behavior
format: gherkin
spec: SPEC-0056
version: 0.1.0
status: draft
artifact: ".sdd/contracts/behavior/bench-lauf-isolation-suiten-roles-und-regen.feature"
tests: ["TST-0252"]
---

# Contract: Bench-Lauf, Isolation, Suiten roles und regen

> **Spec:** SPEC-0056 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Legt `sdd bench run` und `sdd bench init` fest: Matrix-Expansion, Stufenmodell, Isolation, die Suiten `roles` und `regen`, Provider-Hüllen, Budget und Resume (SPEC-0056 FR-01 bis FR-05, FR-09, FR-10).

## Garantien

Die Szenarien im Artifact (`.sdd/contracts/behavior/bench-lauf-isolation-suiten-roles-und-regen.feature`) sind **ausführbare Spezifikation**; Rollen laufen gegen den Fake-LLM-Server.

## Invarianten

- **INV-01:** Jeder Lauf folgt `prepare` → `run` → `measure` → `teardown` in einem frischen temporären Verzeichnis; das Projekt-Worktree und `.sdd/` sind danach byte-gleich, geschrieben wird nur unter `bench/results/<ts>/`.
- **INV-02:** Suite `regen`: Das Arbeitsverzeichnis entsteht aus dem Projekt am Commit der Suite (`git worktree` bzw. `git archive`); das Modul wird vor dem ersten Rollenaufruf entfernt. Der Implementer bekommt Task (Pfad, Zweck aus dem Modul-Docstring, `allowed_paths` = das Modul) und die Unit-Tests, nie das entfernte Modul. Zwischen Versuchen bekommt er die Testausgabe als Rückmeldung.
- **INV-03:** Suite `roles`: je Rolle × Profil ein Eval nach SPEC-0055 mit Holdout nur als Aggregat (Holdout-Fälle liest nur der Eval-Prozess, CON-0219 INV-09; nichts davon wird kopiert); `Q` ist der Gesamtscore (`q_kind: eval`).
- **INV-04:** Mit `top_k` gehen je Rolle nur die `top_k` besten Profile (nach `Q` aus `roles`) in `regen`; die übrigen Belegungen erscheinen im Report als „gefiltert“.
- **INV-05:** Provider-Hüllen zählen Tokens je Rolle, begrenzen Aufrufe je Endpunkt (`requests_per_minute`, `max_concurrent`) und brechen bei überschrittenem Budget mit Ausgang `halted: budget` ab (gezählt werden gemeldete, sonst geschätzte Tokens nach CON-0222 INV-03); `seed` aus dem Profil geht an `openai-compat`.
- **INV-06:** `--resume ORDNER` führt nur Läufe aus, für die kein Record mit Ausgang `completed` oder `halted: budget` existiert; ein `error`-Record wird ersetzt, nicht ergänzt. `--dry-run` ruft kein LLM auf.
- **INV-07:** `sdd bench init` legt `bench/matrix.yaml` und `bench/suites/roles.yaml` aus dem Blueprint an und überschreibt nichts; `bench/results/` steht in den lokalen Ignores.
