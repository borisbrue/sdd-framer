---
id: SPEC-0103
title: "Versionsfelder von Specs und Rollen erhöhen"
status: approved
---
# SPEC-0103: Versionsfelder von Specs und Rollen erhöhen

## 1. Kontext

Specs und Rollen-Definitionen tragen im Frontmatter ein Feld `version` im Format
`MAJOR.MINOR.PATCH`. `sdd spec revise` und `sdd role bump` erhöhen es.

## 4. Funktionale Anforderungen

- **FR-01:** `bump_version(version, part)` erhöht die Stelle `part` (`"major"`, `"minor"`
  oder `"patch"`) um 1 und setzt alle niederwertigeren Stellen auf 0:
  `1.4.2` → major `2.0.0`, minor `1.5.0`, patch `1.4.3`. Die Stellen sind ganze Zahlen,
  nicht Ziffern (`1.9.9` → minor `1.10.0`).
- **FR-02:** Ungültige Eingaben führen zu `ValueError`: eine Version, die nicht genau aus
  drei durch Punkte getrennten nicht-negativen Ganzzahlen besteht (z. B. `1.2`, `1.2.3.4`,
  `v1.2.3`, `1.2.3-rc1`, `1.x.0`), Stellen mit führender Null (`01.2.3`; `0` selbst ist
  erlaubt) sowie ein unbekannter Wert für `part`.

## 5. Nicht-Ziele

- Vorabversionen und Build-Metadaten nach SemVer 2.0.
