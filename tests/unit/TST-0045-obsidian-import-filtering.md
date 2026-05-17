---
id: TST-0045
project: PRJ-0001
title: "Obsidian Import: ID-Filterung und Path-Traversal-Schutz"
level: unit
spec: SPEC-0009
contract: CON-0035
status: draft
artifact: "tests/unit/test_obsidian.py::TestImportFiltering"
---

# Test: Obsidian Import-Filterung und Sicherheit

> **Spec:** SPEC-0009 · **Contract:** CON-0035 · **Level:** unit

## Vorbedingungen

- `sdd_cli.obsidian` Modul importierbar
- Temporäres Verzeichnis

## Testfälle

| Test-ID | Szenario | Erwartet |
|---------|----------|----------|
| T-01 | `id: UNKNOWN-9999` in Frontmatter | Datei wird übersprungen, Warnung ausgegeben |
| T-02 | Ungültiges YAML-Frontmatter | Datei wird übersprungen, Eintrag in warnings.log |
| T-03 | Dateiname `SPEC-0001-x.md` aber `id: SPEC-0002` | Datei übersprungen, Eintrag in warnings.log |
| T-04 | Vault-Datei referenziert Pfad außerhalb vault_path | ValueError ausgelöst |
| T-05 | Gültige SPEC-ID im Muster `SPEC-\d{4}` | Datei wird importiert |
| T-06 | Gültige CON-ID | Datei wird importiert |
| T-07 | ADR-ID im Muster `ADR-\d{4}` | Datei wird importiert |

## Erwartetes Ergebnis

Alle Sicherheits- und Filterregeln halten, ValueError bei Traversal.
