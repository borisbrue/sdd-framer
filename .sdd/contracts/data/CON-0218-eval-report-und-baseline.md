---
id: CON-0218
title: "Eval-Report und Baseline"
type: data
format: json-schema
spec: SPEC-0055
version: 0.1.0
status: approved
artifact: ".sdd/contracts/data/eval-report-und-baseline.schema.json"
tests: ["TST-0247"]
---

# Contract: Eval-Report und Baseline

> **Spec:** SPEC-0055 · **Typ:** Daten (JSON Schema) · **Status:** approved

## Zweck

Beschreibt den Report eines `sdd role eval`-Laufs (SPEC-0055 FR-04, FR-06) und `baseline.json`, den übernommenen Stand einer Rolle (Memento, FR-08).

## Garantien

Das Schema im Artifact ist verbindlich; `compare` und `accept` lesen nur Dateien, die es erfüllen.

## Invarianten

- **INV-01:** Ein Report nennt Rolle, Rollenversion, Prompt-Hash (`sha256:` über den Prompt-Text der Rolle), `output_schema`, Profil (Name, Provider, Modell), Judge (Provider, Modell, Rubrikversion oder `null`), Zahl der Läufe, sdd-Version und Zeitpunkt. Er enthält keine API-Keys und keine Prompt- oder Antworttexte.
- **INV-02:** Je sichtbarem Fall: Score (Mittel der Läufe), Standardabweichung, `passed` (Mehrheit der Läufe), `pass_at_1` (erster Lauf), `pass_all` (alle Läufe, `pass^k`) und je Lauf Checks, Rubrikwerte, Tokens (`input_tokens`, `output_tokens`, `reasoning_tokens`, `null` wenn nicht gemeldet) und Dauer.
- **INV-03:** Ohne `--include-holdout` ist `holdout` ein Aggregat (Anzahl, Mittel, Streuung, `pass_at_1`- und `pass_all`-Quote) ohne IDs; mit `--include-holdout` eine Liste wie `visible` und `include_holdout: true`. Ein solcher Report wird nie unter `.sdd/role-evals/` abgelegt, sondern unter `.sdd/holdout/roles/<rolle>/reports/` (Isolation nach CON-0064).
- **INV-04:** `total` aggregiert sichtbare und Holdout-Fälle. Entwurfsfälle erscheinen nicht.
- **INV-05:** `baseline.json` enthält Rollenversion, Prompt-Hash, `output_schema`, Profil, Zeitpunkt, Score und `passed` je sichtbarem Fall sowie die Aggregate `holdout` und `total`; bei `accept --force` zusätzlich `forced.reason`.
- **INV-06:** Reports ohne Holdout-Details liegen unter `.sdd/role-evals/` (gitignored); `baseline.json` und der Rollen-CHANGELOG sind versioniert.
