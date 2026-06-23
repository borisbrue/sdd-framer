---
id: CON-0189
project: PRJ-0001
title: "Guardrail-Modul – Kommando-Semantik (sdd guard check)"
type: behavior
format: gherkin
spec: SPEC-0051
version: 0.1.0
status: approved
artifact: "contracts/behavior/guardrail-command-semantics.feature"
tests: [TST-0215]
---

# Contract: Guardrail-Modul – Kommando-Semantik

> **Spec:** SPEC-0051 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Schreibt die Entscheidungssemantik des Guardrail-Moduls (`sdd guard check`) fest (FR-04…FR-08):
segment-genaue Auswertung, präzise Force-Flag-Erkennung, unveränderte Gefahren-Menge und sichere
Degradierung.

## Garantien

Die Szenarien im Artifact (`contracts/behavior/guardrail-command-semantics.feature`) sind
ausführbare Spezifikation und MÜSSEN durch automatisierte Tests abgedeckt sein.

## Invarianten

- **INV-01:** Das Kommando wird an `;`, `&&`, `||`, `|` in Segmente zerlegt; jedes Segment wird über
  das führende Kommando-Token bewertet (Strategy-Regeln, Chain-of-Responsibility-Auswertung).
- **INV-02:** Ein Gefahrenmuster, das nur in einem Argument/String erwähnt wird (Commit-Message,
  `echo`, Doku), löst KEINEN Block aus.
- **INV-03:** Die Force-Push-Regel matcht nur echte Force-Flags (`--force`, `--force-with-lease`,
  isoliertes `-f`); `f`-haltige Flags wie `--body-file` lösen keinen Block aus.
- **INV-04:** Die geblockte Gefahren-Menge bleibt unverändert: force-push main/master,
  remote-main löschen, `rm -rf` auf Root/Home/Parent, Disk-Wipe, Net-Pipe-to-Shell, `chmod/chown -R /`.
- **INV-05:** Ist das Modul/`sdd` nicht erreichbar, erlaubt der Hook-Wrapper das Kommando und gibt
  eine sichtbare `[WARN] Guardrail inaktiv`-Meldung aus (sichere, sichtbare Degradierung).

## Geltungsbereich

- **In Scope:** Block/Allow-Entscheidung pro Kommando, Fail-Safe-Verhalten.
- **Out of Scope:** Installations-/Provisioning-Effekte von `sdd init` (→ CON-0188).
