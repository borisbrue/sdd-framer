---
id: CON-0034
project: PRJ-0001
title: "Obsidian Export – Dateistruktur und Wiki-Link-Format"
type: behavior
format: gherkin
spec: SPEC-0009
version: 0.1.0
status: draft
artifact: "contracts/behavior/obsidian-export-verhalten.feature"
tests: ["TST-0043", "TST-0047"]
---

# Contract: Obsidian Export – Dateistruktur und Wiki-Link-Format

> **Spec:** SPEC-0009 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Definiert das beobachtbare Verhalten von `sdd obsidian export`:
Welche Dateien werden wohin geschrieben, wie sehen Wiki-Links aus,
wann wird eine Datei übersprungen, und wie verhält sich `--dry-run`.

## Garantien

- **G-01:** Export schreibt nur innerhalb des konfigurierten `vault_path/subfolder`.
- **G-02:** ID-Referenzen im Body (`SPEC-XXXX`, `CON-XXXX`, `TST-XXXX`, `ADR-XXXX`)
  werden in Wiki-Links umgewandelt: `[[ID-slug]]` (Dateiname ohne `.md`).
- **G-03:** `SDD/index.md` enthält alle exportierten Artefakte als Wiki-Link-Liste.
- **G-04:** `--dry-run` schreibt keine Datei, meldet aber alle geplanten Aktionen.
- **G-05:** Eine Vault-Datei wird nur überschrieben, wenn `updated:` im Projekt
  neuer ist als in der bestehenden Vault-Datei (Vergleich ISO-Datum-String).

## Invarianten

- **INV-01:** Unterordner im Vault: `SDD/specs/`, `SDD/contracts/`, `SDD/tests/`, `SDD/adrs/`.
- **INV-02:** Dateiname = `{ID}-{slug}.md` (identisch zum Projektnamen).
- **INV-03:** Mehrfach-Export ohne Änderungen erzeugt identische Dateien (Idempotenz).
- **INV-04:** Kein Sync von `.sdd/`-Konfiguration oder Python-Quellcode.
- **INV-05:** Vault-Pfad darf kein Unterverzeichnis des SDD-Projekts sein (Cycle-Prevention).
