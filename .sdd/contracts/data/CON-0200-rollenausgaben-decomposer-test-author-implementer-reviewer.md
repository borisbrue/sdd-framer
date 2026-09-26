---
id: CON-0200
title: "Rollenausgaben: decomposer, test_author, implementer, reviewer"
type: data
format: json-schema
spec: SPEC-0053
version: 0.3.0
status: approved
artifact: ".sdd/contracts/data/rollenausgaben-decomposer-test-author-implementer-reviewer.schema.json"
tests: ["TST-0229"]
---

# Contract: Rollenausgaben: decomposer, test_author, implementer, reviewer

> **Spec:** SPEC-0053 · **Typ:** Daten (JSON Schema) · **Status:** approved

## Zweck

Legt die Ausgabe jeder Arbeitsrolle fest (SPEC-0053 FR-05, FR-06, FR-10, FR-11). Der `RoleRunner`
validiert jede Antwort gegen `$defs/<rolle>`; eine ungültige Antwort ist `outcome: invalid_output`
und ein gezählter Fehlversuch.

## Invarianten

- **INV-01 (decomposer):** Jeder Task hat `fr_ids`, `dependencies` (Titel anderer Tasks derselben
  Zerlegung) und `allowed_paths`. Tasks vom Typ `code` und `test` haben mindestens eine FR;
  `code`-Tasks zusätzlich `test_file` und `test_command`.
- **INV-02 (decomposer):** `allowed_paths` sind die Globs, die der Task schreiben darf; sie sind
  die Grundlage der PathPolicy (CON-0204).
- **INV-03 (test_author):** Genau eine Testdatei je Antwort mit mindestens einer FR.
- **INV-04 (implementer):** Mindestens eine Datei; alle Pfade relativ ohne `..`. Ob der Pfad
  erlaubt ist, entscheidet die PathPolicy, nicht dieses Schema.
- **INV-05 (reviewer):** `verdict: fail` verlangt mindestens einen Befund mit Kategorie
  `requirement|architecture|quality|test`, Datei und Begründung.
- **INV-06 (Übernahme in das Task-Modell):** Der Mediator macht aus jeder decomposer-Task genau
  eine Task nach CON-0096 (+ CON-0203):
  | CON-0096-Feld | Herkunft |
  |---------------|----------|
  | `id` | neue UUID4 |
  | `dependencies` | IDs der Tasks, deren Titel in `dependencies` steht; Titel müssen innerhalb der Zerlegung eindeutig sein (Rollen-Check `unique_titles`), jeder Verweis muss existieren (`deps_resolvable`), der Graph ist zyklenfrei (`acyclic`) |
  | `context_size` | aus `complexity`: low → S, medium → M, high → L |
  | `estimated_tokens` | aus `complexity`: low 2000, medium 6000, high 15000 (überschreibbar über `pipeline.estimates`) |
  | `test_ids` | TST-IDs der Spec, deren `artifact` gleich `test_file` ist; leer, wenn es keine gibt |
  | `status`, `retry_count`, `llm_id`, … | Startwerte aus CON-0096 |

  Die Tasks laufen danach durch den Task-Lebenszyklus aus CON-0095; `test_ids` erfüllt die
  Bedingung des Completion-Gates aus CON-0124.

## Beispiele

**Gültig (reviewer):**
```json
{ "verdict": "fail", "findings": [
  { "category": "architecture", "file": "tool/sdd_cli/web/x.py", "line": 12,
    "reason": "Schreibt direkt nach .sdd/specs (ARCH-01)" } ] }
```

**Ungültig (und warum):**
```json
{ "tasks": [ { "title": "Modell", "description": "d", "type": "code", "complexity": "low",
               "fr_ids": [], "dependencies": [], "allowed_paths": ["tool/**"] } ] }
```
→ Verstößt gegen INV-01 (`code`-Task ohne FR, ohne `test_file`/`test_command`).

## Validierung

- Schema: `.sdd/contracts/data/rollenausgaben-decomposer-test-author-implementer-reviewer.schema.json`
  (`$defs` je Rolle).

## Seit SPEC-0055 (0.3.0)

`$defs/judge`: Ausgabe der Rolle `judge` (`scores` je Kriterium 1–5, optional `begruendung`), CON-0219 INV-07.
