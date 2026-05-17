---
id: TST-0044
project: PRJ-0001
title: "Obsidian Import Conflict-Erkennung: beidseitige Änderung"
level: unit
spec: SPEC-0009
contract: CON-0035
status: draft
artifact: "tests/unit/test_obsidian.py::TestConflictDetection"
---

# Test: Obsidian Conflict-Erkennung

> **Spec:** SPEC-0009 · **Contract:** CON-0035 · **Level:** unit

## Vorbedingungen

- `sdd_cli.obsidian` Modul importierbar
- Temporäres Verzeichnis für Dateisystem-Operationen

## Testfälle

| Test-ID | Szenario | Erwartet |
|---------|----------|----------|
| T-01 | Beide Seiten geändert (vault_mtime > export_mtime, project_mtime > export_mtime) | Conflict erkannt, kein Überschreiben |
| T-02 | Nur Vault geändert | Kein Conflict, Datei wird importiert |
| T-03 | Nur Projekt geändert | Kein Conflict (Vault älter), Datei wird nicht überschrieben |
| T-04 | Conflict-Eintrag in conflicts.yaml enthält: id, vault_path, project_path, detected_at | Pflichtfelder vorhanden |
| T-05 | Kein Export-Zeitstempel bekannt (erster Import) | Kein Conflict (frischer Import) |

## Erwartetes Ergebnis

Conflict-Logik funktioniert korrekt in allen 5 Szenarien.
