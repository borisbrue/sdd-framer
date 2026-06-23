---
id: CON-0185
project: PRJ-0001
title: "Pattern-Usage-Aggregation – Code-Scan, Normalisierung, Merge"
type: behavior
format: gherkin
spec: SPEC-0049
version: 0.1.0
status: approved
artifact: "contracts/behavior/pattern-usage-scan.feature"
tests: [TST-0217]
---

# Contract: Pattern-Usage-Aggregation – Code-Scan, Normalisierung, Merge

> **Spec:** SPEC-0049 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Schreibt das beobachtbare Verhalten der Aggregation fest: wie der Code-Annotation-Scanner
Fundstellen findet, wie Pattern-Namen zwischen Code und Katalog normalisiert abgeglichen werden
und wie Katalog und Fundstellen gemerged werden (FR-03, FR-04, FR-05).

## Garantien

Die im Artifact (`contracts/behavior/pattern-usage-scan.feature`) hinterlegten Szenarien sind
**ausführbare Spezifikation**. Jedes Szenario MUSS durch einen automatisierten Test abgedeckt sein.

## Invarianten (über alle Szenarien hinweg)

- **INV-01:** Es werden ausschließlich `accepted`-Patterns in das Ergebnis aufgenommen.
- **INV-02:** Der Abgleich Code-Annotation ↔ Katalog-Pattern erfolgt normalisiert
  (Leerzeichen entfernt + lowercase); eine Alias-Tabelle wird nicht verwendet (v0.1.0).
- **INV-03:** Ein akzeptiertes Pattern ohne Fundstelle bleibt im Ergebnis (mit leerer
  `code_locations`-Liste); eine Fundstelle ohne Katalogeintrag wird verworfen.
- **INV-04:** Fundstellen liefern repo-relativen `file`-Pfad, 1-basierte `line` und die
  getrimmte `annotation`.
- **INV-05:** Gescannt werden die konfigurierten Source-Roots (Default `tool/sdd_cli/`, `web/`;
  optional über `patterns.scan_roots` in `config.yaml` überschreibbar).

## Geltungsbereich

- **In Scope:** Scanner-Matching, Normalisierung, Merge-Verhalten, Leerfälle.
- **Out of Scope:** HTTP-Shape des Endpunkts (→ CON-0184); AST-/semantische Erkennung.
