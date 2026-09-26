---
id: CON-0220
title: "Ratchet, Übernahme und Skill sdd-role-tune"
type: behavior
format: gherkin
spec: SPEC-0055
version: 0.1.0
status: approved
artifact: ".sdd/contracts/behavior/ratchet-uebernahme-und-skill-sdd-role-tune.feature"
tests: ["TST-0249"]
---

# Contract: Ratchet, Übernahme und Skill sdd-role-tune

> **Spec:** SPEC-0055 · **Typ:** Verhalten (Gherkin) · **Status:** approved

## Zweck

Legt `sdd role compare`, `sdd role accept` und den Skill `/sdd-role-tune` fest (SPEC-0055 FR-07, FR-08, FR-10).

## Garantien

Die Szenarien im Artifact (`.sdd/contracts/behavior/ratchet-uebernahme-und-skill-sdd-role-tune.feature`) sind **ausführbare Spezifikation**. Jedes Szenario MUSS durch einen automatisierten Test (pytest) abgedeckt sein; der Skill wird als Text geprüft.

## Invarianten

- **INV-01:** `compare A B` ergibt `accept` genau dann, wenn gilt: `total.mean(B) ≥ total.mean(A)`, `holdout.mean(B) ≥ holdout.mean(A)`, kein sichtbarer Fall ist in A `passed` und in B nicht, und `output_schema` ist gleich. Sonst `reject` mit jeder verletzten Bedingung und den betroffenen sichtbaren Fällen. Exit 0 bei `accept`, 1 bei `reject`, 2 bei ungültigen Reports oder verschiedenen Rollen.
- **INV-02:** `accept ROLLE --report R` vergleicht R mit `baseline.json` (ohne Baseline: `accept`) und bricht bei `reject` mit Exit 1 ab, außer mit `--force --reason`. Danach, in dieser Reihenfolge: neue Version (Minor bei geändertem Prompt-Hash, sonst Patch), Rollendatei schreiben, `baseline.json` aus R ersetzen, Eintrag an `.sdd/roles/<rolle>/CHANGELOG.md` (Datum, Version alt → neu, Score vorher → nachher, `--reason` falls erzwungen).
- **INV-03:** Die übernommene Rollendatei ist die aus R (`--version DATEI` des Eval-Laufs) bzw. die geladene; Ziel ist die geladene Rollendatei, wenn sie im Projektverzeichnis liegt, sonst `.sdd/roles/<rolle>.md`. Stimmt der Prompt-Hash der Datei nicht mit R überein, bricht `accept` mit Exit 2 ab.
- **INV-04:** Skill `/sdd-role-tune` (Repo und Blueprint, gleicher Text bis auf `scope:`-Frontmatter): Baseline-Eval, Fehlschläge gruppieren, eine Änderung mit Hypothese als Kandidatendatei, Eval des Kandidaten, `compare`, bei `accept` Diff und Zahlen dem Nutzer vorlegen und erst dann `accept`; höchstens `n` Iterationen (Default 3). Der Skill verbietet, Fälle oder Checks zu ändern, `--include-holdout` zu nutzen und Pfade mit dem Segment `holdout` zu lesen.
