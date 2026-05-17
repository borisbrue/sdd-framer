---
id: CON-0035
project: PRJ-0001
title: "Obsidian Import – Conflict-Erkennung und Rückschreiben"
type: behavior
format: gherkin
spec: SPEC-0009
version: 0.1.0
status: draft
artifact: "contracts/behavior/obsidian-import-conflict.feature"
tests: ["TST-0044", "TST-0045", "TST-0047"]
---

# Contract: Obsidian Import – Conflict-Erkennung und Rückschreiben

> **Spec:** SPEC-0009 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Definiert das Verhalten von `sdd obsidian import`: Wie werden Vault-Dateien
ins Projekt zurückgeschrieben, wann wird ein Conflict erkannt, und wie reagiert
der Watch-Modus auf Dateiänderungen.

## Garantien

- **G-01:** Import überschreibt nur Dateien, deren `id:`-Feld einem bekannten
  Muster entspricht (`SPEC-\d{4}`, `CON-\d{4}`, `TST-\d{4}`, `ADR-\d{4}`).
- **G-02:** Wenn Vault-Datei *und* Projekt-Datei seit dem letzten Export
  geändert wurden, wird **kein** Überschreiben vorgenommen; stattdessen
  wird ein Eintrag in `.sdd/obsidian-conflicts.yaml` geschrieben.
- **G-03:** Wiki-Links (`[[ID-slug]]`) werden beim Import zurück in reine IDs
  konvertiert (`SPEC-0001`, `CON-0001`, …).
- **G-04:** `sdd obsidian import` gibt Exit-Code 1 zurück wenn Conflicts
  vorhanden sind, Exit-Code 2 bei Konfigurationsfehler.
- **G-05:** `sdd obsidian watch` stoppt sauber auf SIGINT (Ctrl+C).

## Invarianten

- **INV-01:** `.sdd/obsidian-conflicts.yaml` enthält für jeden Conflict:
  `id`, `vault_path`, `project_path`, `detected_at`.
- **INV-02:** Dateien mit ungültigem YAML-Frontmatter werden übersprungen
  und in `.sdd/obsidian-warnings.log` vermerkt.
- **INV-03:** Dateien deren `id:` nicht mit dem Dateinamen übereinstimmt
  werden übersprungen (Eintrag in `.sdd/obsidian-warnings.log`).
- **INV-04:** Path-Traversal außerhalb `vault_path` → `ValueError`.
