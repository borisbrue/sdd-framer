---
id: CON-0188
project: PRJ-0001
title: "sdd init Autonomie-Provisioning (Guardrail + opt-in Bypass)"
type: behavior
format: gherkin
spec: SPEC-0051
version: 0.1.0
status: approved
artifact: "contracts/behavior/init-autonomy-provisioning.feature"
tests: [TST-0214]
---

# Contract: sdd init Autonomie-Provisioning

> **Spec:** SPEC-0051 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Schreibt fest, was `sdd init` für das Autonomie-Setup tut (FR-01, FR-02, FR-03): Guardrail-Hook
installieren, idempotent in `settings.json` mergen, und Bypass ausschließlich opt-in/lokal.

## Garantien

Die Szenarien im Artifact (`contracts/behavior/init-autonomy-provisioning.feature`) sind
ausführbare Spezifikation und MÜSSEN durch automatisierte Tests abgedeckt sein.

## Invarianten

- **INV-01:** `sdd init` legt `.claude/hooks/autonomous-guardrail.sh` (ausführbar) an und verdrahtet
  den PreToolUse/Bash-Hook in `.claude/settings.json`.
- **INV-02:** Der Hook-Merge ist idempotent (kein Duplikat bei erneutem init) und lässt die
  bestehende `permissions.allow`-Liste unangetastet.
- **INV-03:** Ohne `--autonomous` wird KEIN `defaultMode` gesetzt und keine committed-Datei mit
  Bypass verändert.
- **INV-04:** `--autonomous` schreibt `permissions.defaultMode: bypassPermissions` ausschließlich in
  `.claude/settings.local.json` und ergänzt `settings.local.json` in `.gitignore`.

## Geltungsbereich

- **In Scope:** Datei-/Settings-Effekte von `sdd init` und `sdd init --autonomous`.
- **Out of Scope:** Guardrail-interne Kommando-Semantik (→ CON-0189).
