---
id: CON-0210
title: "Verweise, Config-Aufräumen und sdd spec deprecate"
type: behavior
format: gherkin
spec: SPEC-0058
version: 0.1.0
status: approved
artifact: ".sdd/contracts/behavior/verweise-config-aufraeumen-und-sdd-spec-deprecate.feature"
tests: ["TST-0239"]
---

# Contract: Verweise, Config-Aufräumen und sdd spec deprecate

> **Spec:** SPEC-0058 · **Typ:** Verhalten (Gherkin) · **Status:** approved

## Zweck

Legt fest, wie sich abgelöste Befehle verhalten, wie `sdd upgrade` nicht mehr gelesene
Config-Blöcke aufräumt und wie `sdd spec deprecate` eine Spec ablöst (SPEC-0058 FR-01 bis FR-04,
FR-09).

## Garantien

Die Szenarien im Artifact (`.sdd/contracts/behavior/verweise-config-aufraeumen-und-sdd-spec-deprecate.feature`) sind **ausführbare Spezifikation**. Jedes Szenario MUSS durch
einen automatisierten Test (pytest) abgedeckt sein.

## Invarianten

- **INV-01:** Ein Verweis führt nichts aus: kein LLM-Aufruf, kein Git-Befehl, keine Datei wird
  geschrieben. Er akzeptiert die bisherigen Argumente und Optionen, damit alte Aufrufe parsen, nennt
  den Ersatz und endet mit Exit 1. In `sdd --help` erscheint er nicht (`hidden=True`).
- **INV-02:** `sdd upgrade` kommentiert nur die Top-Level-Blöcke `llm_pool`, `local_agent` und
  `autopilot` aus; jede Zeile bleibt als Kommentar mit Präfix `# [SPEC-0058] ` erhalten. Alle
  anderen Zeilen von `config.yaml` bleiben byte-gleich.
- **INV-03:** `sdd spec deprecate` ist der einzige Weg, eine Spec auf `deprecated` zu setzen. Er
  schreibt `status: deprecated`, `deprecated_reason` und optional `replaced_by` ins Frontmatter und
  einen Eintrag ins Audit-Log. Abhängige, nicht deprecated Specs (`depends_on`) erzeugen eine
  Warnung, keine Blockade. Eine unbekannte Spec-ID endet mit Exit 2.
- **INV-04:** Nach dem Rückbau setzt kein Modul unter `tool/` die Variablen `ANTHROPIC_API_KEY`
  oder `ANTHROPIC_BASE_URL`.
