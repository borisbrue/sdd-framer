---
id: CON-0205
title: "Pipeline-Ablauf, Entscheidungsquelle und Fortsetzen"
type: behavior
format: gherkin
spec: SPEC-0053
version: 0.3.0
status: approved
artifact: ".sdd/contracts/behavior/pipeline-ablauf-entscheidungsquelle-und-fortsetzen.feature"
tests: ["TST-0234"]
---

# Contract: Pipeline-Ablauf, Entscheidungsquelle und Fortsetzen

> **Spec:** SPEC-0053 · **Typ:** Verhalten (Gherkin) · **Status:** approved

## Zweck

Legt das beobachtbare Verhalten von `sdd pipeline run|decide|status|report` fest (SPEC-0053
FR-04 bis FR-06, FR-08, FR-10 bis FR-16): Ablauf, Rollen-Checks vor S1, Eskalation, Abnahme,
Dialogmodus und Fortsetzen nach Abbruch.

## Garantien

Die Szenarien im Artifact (`.sdd/contracts/behavior/pipeline-ablauf-entscheidungsquelle-und-fortsetzen.feature`)
sind **ausführbare Spezifikation**. Jedes Szenario MUSS durch einen automatisierten Test mit
Fake-Providern abgedeckt sein.

## Befehle und Exit-Codes

| Befehl | 0 | 1 | 2 | 3 |
|--------|---|---|---|---|
| `pipeline run SPEC [--dry-run] [--resume RUN] [--max-tasks N]` | Run abgeschlossen (Dry-Run: nach S1) | Run angehalten (`halted`) oder Finalize gescheitert | Spec nicht `approved`, Konfiguration ungültig, Run unbekannt | wartet auf den Supervisor (`session`) |
| `pipeline decide RUN --json CMD` | angenommen, Run fortgesetzt bis zum nächsten Halt | – | keine offene Anfrage, Command ungültig oder nicht erlaubt | erneut wartend |
| `pipeline status RUN` | Status ausgegeben | – | Run unbekannt | – |
| `pipeline report RUN` | Report ausgegeben | – | Run unbekannt | – |

## Invarianten

- **INV-01:** Der Supervisor wird nur an S1, S2 und S3 gefragt; S1 erst, wenn alle Rollen-Checks
  der Zerlegung bestanden sind.
- **INV-02:** `max_revisions` (Default 2) begrenzt Neuzerlegungen in S1; `max_attempts` (Default 3)
  begrenzt Versuche je Task vor S2.
- **INV-03:** Eine ungültige Entscheidung wird einmal neu angefragt; die zweite ungültige führt zu
  `halt`. Beide stehen mit `valid: false` in `decisions.jsonl`.
- **INV-04:** `inline` und `session` unterscheiden sich nur darin, wann die Antwort eintrifft:
  Anfrage, Validierung, Ausführung und Protokoll sind identisch (CON-0201, CON-0202).
- **INV-05:** `--resume` setzt am Zustand aus `state.json` fort; Tasks im Zustand `done` werden
  nicht erneut bearbeitet, ein unterbrochener Task beginnt mit dem nächsten Versuch.
- **INV-06:** Ein Längenabbruch (`finish_reason: length` ohne verwertbaren Inhalt) wird im
  `RoleRunner` genau einmal mit dem 1,5-fachen Budget wiederholt; danach zählt er als Fehlversuch.
  Die Pipeline sieht nur das Ergebnis des Rollenaufrufs.
- **INV-08:** Jede Entscheidung lässt sich über `request_id` ihrer Anfrage zuordnen (CON-0202).
- **INV-09:** `pipeline run` verlangt Spec-Status `approved` **und** die Gate-Phase
  `execute-unlocked` (CON-0025); sonst Exit 2. S1 und S3 ändern keine Gate-Phasen; nach S3 mit
  vollständiger Abnahme läuft Finalize wie bisher und setzt `implemented`.
- **INV-10:** `--dry-run` bedeutet hier: Zerlegung und S1, keine Arbeitsrollen, kein Code. Run-
  Verzeichnis und `token_usage` werden trotzdem geschrieben. Das weicht bewusst von
  `orchestrate --dry-run` (CON-0012) ab; SPEC-0058 bildet `orchestrate` auf `pipeline run --auto`
  ab.
- **INV-07:** Ohne `llm.roles` verhält sich jeder bestehende Befehl wie vor SPEC-0053.

## Begriffe

| Begriff | Definition |
|---------|------------|
| Rollen-Check | Prüfung der Ausgabe einer Rolle (CON-0199 INV-03) |
| Gate | Prüfung des Projektzustands (SPEC-0054) |
| Entscheidungsquelle | liefert ein Command oder `Pending` (`inline`/`session`) |
