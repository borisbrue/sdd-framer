---
id: CON-0222
title: "Bench-Record"
type: data
format: json-schema
spec: SPEC-0056
version: 0.1.0
status: approved
artifact: ".sdd/contracts/data/bench-record.schema.json"
tests: ["TST-0251"]
---

# Contract: Bench-Record

> **Spec:** SPEC-0056 · **Typ:** Daten (JSON Schema) · **Status:** approved

## Zweck

Beschreibt eine Zeile in `bench/results/<ts>/results.jsonl` (SPEC-0056 FR-06).

## Garantien

Das Schema im Artifact ist verbindlich; `report` und `compare` lesen nur gültige Records und melden ungültige Zeilen.

## Invarianten

- **INV-01:** Gemeinsame Pflichtfelder: Lauf-ID, Suite, Suite-Art, `q_kind`, Belegung (je Rolle Profil, Provider, Modell, Parameter, gemeldeter Modellname, Endpunkt, Rollenversion), Wiederholung, Ausgang, `Q`, Tokens je Rolle und Summen `T_in`, `T_out`, `T_reason`, `T_claude`, Dauer, sdd-Version, Zeitpunkt, Pfad der Laufartefakte.
- **INV-02:** `q_kind: eval` (Suite `roles`) verlangt Rolle, Profil, `pass_at_1`, `pass_all` und optional `holdout_Q` (Aggregat, nie Fall-IDs; die Laufartefakte enthalten nur Reports ohne Holdout-Details, CON-0219 INV-04/09). `q_kind: quality` (Suite `regen`) verlangt Aufgabe, `Q_req`, `Q_arch`, `Q_code`, `frs_total`, `frs_met`, Versuche, Fehlversuche und Git-SHA.
- **INV-03:** Tokens ohne Usage des Providers (`source: unavailable`) sind geschätzt (Zeichen/4 von Prompt und Antwort) und tragen `estimated: true` am Rollenwert und am Record; nicht gemeldete Reasoning-Tokens zählen 0. Die Records sind unabhängig von der Token-History (CON-0121/CON-0129); beide lesen dieselbe Usage-Erfassung nach SPEC-0060.
- **INV-04:** Ein Record enthält keine API-Keys, keine Prompts und keine Inhalte versteckter Tests oder Referenzlösungen.
- **INV-05:** Ein Lauf mit Ausgang `halted: budget` oder `error` hat trotzdem einen Record mit dem erreichten Stand; `error` trägt `error` mit Grund.
