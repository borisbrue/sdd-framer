---
id: TST-0047
project: PRJ-0001
title: "Obsidian Integration Acceptance: Gherkin-Szenarien aus SPEC-0009 §6"
level: acceptance
spec: SPEC-0009
contract: CON-0034
status: draft
artifact: "tests/unit/test_obsidian.py::TestAcceptance"
---

# Test: Obsidian Acceptance (Gherkin §6)

> **Spec:** SPEC-0009 · **Contract:** CON-0034, CON-0035 · **Level:** acceptance

## Vorbedingungen

- `sdd_cli.obsidian` Modul vollständig implementiert
- Vollständiges SDD-Projekt mit SPEC-0001, CON-0001
- Temporäres Vault-Verzeichnis

## Szenarien (aus SPEC-0009 §6)

### Szenario 1: Export aller Artefakte
- Export produziert `SDD/specs/SPEC-0001-user-login.md`
- Export produziert `SDD/index.md` mit Links auf alle Artefakte

### Szenario 2: Import nach manuellem Edit ohne Conflict
- Vault-Datei editiert, Projekt unverändert
- Import überschreibt korrekt, `updated:` aktualisiert

### Szenario 3: Conflict-Erkennung bei beidseitiger Änderung
- Beide Seiten geändert → kein Überschreiben
- `.sdd/obsidian-conflicts.yaml` enthält SPEC-0001
- Exit-Code 1

### Szenario 4: CLI-Fehler bei fehlendem vault_path
- Kein `obsidian.vault_path` und kein `--vault`
- Output: "obsidian.vault_path nicht konfiguriert"
- Exit-Code 2

## Erwartetes Ergebnis

Alle 4 Szenarien bestehen im End-to-End-Test mit echtem Dateisystem.
