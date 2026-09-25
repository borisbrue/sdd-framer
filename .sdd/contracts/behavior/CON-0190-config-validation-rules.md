---
id: CON-0190
title: Config-Validierungsregeln – Pflichtfelder, Provider-Enum, Provider-Konsistenz
type: behavior
format: gherkin
spec: SPEC-0052
version: 0.1.0
status: draft
artifact: contracts/behavior/con-0190-config-validation-rules.feature
tests:
- TST-0219
---

# Contract: Config-Validierungsregeln – Pflichtfelder, Provider-Enum, Provider-Konsistenz

> **Spec:** SPEC-0052 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Legt das beobachtbare Validierungsverhalten des `ConfigValidator` fest: welche Pflichtfelder
geprüft werden, welche Provider-Werte erlaubt sind und welche provider-spezifischen
Zusatzfelder benötigt werden.

## Garantien

Die im Artifact (`contracts/behavior/con-0190-config-validation-rules.feature`) hinterlegten
Szenarien sind **ausführbare Spezifikation**. Jedes Szenario MUSS durch einen automatisierten
pytest-behave-Test abgedeckt sein.

## Invarianten (über alle Szenarien hinweg)

- **INV-01:** Ein fehlender Pflichtfeldwert produziert immer Level `error`, nie `warning`.
- **INV-02:** Ein ungültiger Provider-Name produziert immer Level `error`.
- **INV-03:** Ein fehlender `api_key` bei `provider: anthropic` produziert Level `warning` (kein `error`) — keyfreier Betrieb via claude-cli ist erlaubt.
- **INV-04:** Der Validator bricht bei einem Fehler **nicht** ab — alle Checks werden durchgeführt.

## Begriffe

| Begriff         | Definition                                                              |
|-----------------|-------------------------------------------------------------------------|
| Pflichtfeld     | Konfigurationsschlüssel der vorhanden und nicht leer sein muss          |
| Provider-Block  | `llm.<component>`-Eintrag in config.yaml                               |
| error           | Validierungsergebnis das Exit-Code 1 erzwingt                           |
| warning         | Validierungsergebnis das nur als Hinweis erscheint (Exit-Code 0 möglich)|

## Erweiterung durch SPEC-0054

Neue Regelgruppe `quality` (Level `error`): ungültige `quality.gates`, negative Gewichte,
`quality.architecture.threshold ≤ 0`, unbekannter `quality.finalize`-Modus sowie Schemaverstöße
einer vorhandenen `.sdd/quality.yaml` (Pfad `quality.yaml:<feldpfad>`) – CON-0196 INV-07.
