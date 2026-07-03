---
id: CON-0191
title: sdd config validate – CLI-Interface, Exit-Code, JSON-Output
type: behavior
format: gherkin
spec: SPEC-0052
version: 0.1.0
status: draft
artifact: contracts/behavior/con-0191-config-validate-cli.feature
tests:
- TST-0220
---

# Contract: sdd config validate – CLI-Interface, Exit-Code, JSON-Output

> **Spec:** SPEC-0052 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Legt das CLI-Verhalten von `sdd config validate` fest: Subcommand-Struktur,
Exit-Codes und das maschinenlesbare `--json`-Ausgabeformat.

## Garantien

Die im Artifact (`contracts/behavior/con-0191-config-validate-cli.feature`) hinterlegten
Szenarien sind **ausführbare Spezifikation**.

## Invarianten (über alle Szenarien hinweg)

- **INV-01:** Exit-Code ist immer 0 oder 1 — keine anderen Codes.
- **INV-02:** `--json`-Output ist immer ein valides JSON-Array, auch wenn das Array leer ist.
- **INV-03:** `sdd validate` (bestehender Befehl) wird durch diesen Subcommand nicht verändert.

## Begriffe

| Begriff       | Definition                                                        |
|---------------|-------------------------------------------------------------------|
| Exit-Code 0   | Keine Fehler — Config ist valide (Warnings sind erlaubt)          |
| Exit-Code 1   | Mindestens ein Eintrag mit level "error" im Ergebnis              |
| Issue-Objekt  | JSON-Objekt `{level, path, message}` im `--json`-Array            |

