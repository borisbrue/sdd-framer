---
id: CON-0202
title: "Run-Verzeichnis: run.json, state.json, events, decisions, pending-decision"
type: data
format: json-schema
spec: SPEC-0053
version: 0.4.0
status: approved
artifact: ".sdd/contracts/data/run-verzeichnis-run-json-state-json-events-decisions-pending-decision.schema.json"
tests: ["TST-0231"]
---

# Contract: Run-Verzeichnis: run.json, state.json, events, decisions, pending-decision

> **Spec:** SPEC-0053 · **Typ:** Daten (JSON Schema) · **Status:** approved

## Zweck

Legt die Dateien eines Pipeline-Runs unter `.sdd/runs/<SPEC>/<run_id>/` fest (SPEC-0053 FR-12,
FR-14, FR-15). Sie sind zugleich Protokoll (Nachvollziehbarkeit), Zustand (fortsetzbarer Automat)
und Schnittstelle für den Dialogmodus.

| Datei | Schema | Inhalt |
|-------|--------|--------|
| `run.json` | `$defs/run` | Konfiguration: Rollen mit Provider, Modell, Modus, Rollenversion; Warnungen |
| `state.json` | `$defs/state` | aktueller Zustand des Automaten und aller Tasks |
| `events.jsonl` | `$defs/event` je Zeile | jeder Übergang, Rollenaufruf, Gate, abgelehnte Schreibvorgang |
| `decisions.jsonl` | `$defs/decision` je Zeile | jede Entscheidung mit Quelle und Gültigkeit |
| `pending-decision.json` | `$defs/pending_decision` | offene Anfrage mit `request_id` |
| `requests/<request_id>.json` | `$defs/pending_decision` | beantwortete Anfragen (Archiv) |

## Invarianten

- **INV-01:** `state.json` wird nach jedem Übergang atomar geschrieben (temporäre Datei +
  Umbenennen). Nach einem Abbruch ist sie immer lesbar und konsistent.
- **INV-02:** Vor jeder Entscheidung wird die Anfrage mit eindeutiger `request_id` als
  `pending-decision.json` geschrieben und `state.pending_request_id` gesetzt; erst danach wird die
  Entscheidungsquelle gefragt. Nach einer gültigen Entscheidung wird die Anfrage nach
  `requests/<request_id>.json` verschoben und `pending_request_id` geleert. Jede Zeile in
  `decisions.jsonl` nennt ihre `request_id`; die Zuordnung Anfrage ↔ Entscheidung bleibt so
  vollständig erhalten.
- **INV-03:** Ob eine Anfrage offen ist, bestimmt `state.pending_request_id`, nicht die Existenz
  einer Datei. `status: awaiting_supervisor` tritt genau dann auf, wenn eine Anfrage offen ist und
  die Entscheidungsquelle `Pending` gemeldet hat.
- **INV-04:** `events.jsonl` und `decisions.jsonl` werden nur angehängt, nie umgeschrieben.
- **INV-05:** Keine Datei enthält API-Keys, Prompts oder Modellantworten im Klartext; Prompts
  erscheinen nur als `prompt_hash`.
- **INV-07:** `run_id` hat die Form `<SPEC-ID>-<YYYYMMDDTHHMMSS>-<suffix>` und ist damit
  projektweit eindeutig.
- **INV-08:** Die Phasen der Spec (CON-0025/CON-0030) bleiben in `.sdd/pipeline/<SPEC>-gate.json`.
  Das Run-Verzeichnis hält nur den Zustand eines Runs; `state.tasks[].task_id` verweist auf Tasks
  nach CON-0096 in `.sdd/tasks/<SPEC>.json`, deren Status weiter nach CON-0095 gepflegt wird.
- **INV-09:** `events.jsonl` enthält keine Tokenzahlen; der Verbrauch steht ausschließlich in
  `token_usage` (SPEC-0060). Jedes Ereignis `role_call` nennt `role`, `attempt`, `outcome` und eine
  `call_id`; dieselbe `call_id` steht im `context_json` der Usage-Zeile.
- **INV-06:** `run.json` nennt je Rolle `role_version`; `warnings` enthält u. a. die Warnung bei
  gleichem Modell für Reviewer und Implementierer (SPEC-0053 FR-04).

## Beispiele

**Gültig (`state.json`):**
```json
{ "run_id": "SPEC-0900-20260925T101500-a1", "status": "awaiting_supervisor", "phase": "decompose",
  "revisions": 0, "tasks": [], "updated_at": "2026-09-25T10:15:03Z" }
```

**Ungültig (und warum):**
```json
{ "run_id": "r", "status": "waiting", "phase": "decompose", "tasks": [] }
```
→ Unbekannter `status`, `updated_at` fehlt.

## Validierung

- Schema: `.sdd/contracts/data/run-verzeichnis-run-json-state-json-events-decisions-pending-decision.schema.json`
  (`$defs` je Datei).
