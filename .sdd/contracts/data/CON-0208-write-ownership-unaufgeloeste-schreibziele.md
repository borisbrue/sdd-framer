---
id: CON-0208
title: "write_ownership: unaufgelöste Schreibziele"
type: data
format: json-schema
spec: SPEC-0059
version: 0.2.0
status: approved
artifact: ".sdd/contracts/data/write-ownership-unaufgeloeste-schreibziele.schema.json"
tests: ["TST-0237"]
---

# Contract: write_ownership: unaufgelöste Schreibziele

> **Spec:** SPEC-0059 · **Typ:** Daten (JSON Schema) · **Status:** approved

## Zweck

Erweitert Regeln der Art `write_ownership` aus CON-0194 (`.sdd/architecture.yaml`) um das optionale
Feld `unresolved`. Es legt fest, wie Schreibzugriffe behandelt werden, deren Ziel der Extraktor
nicht auflösen kann (variable Pfade, CON-0193 `unresolved: true`). Ohne diese Option ist eine Regel
„nur Schicht X schreibt Artefakte“ in Codebasen mit variablen Pfaden blind (SPEC-0059 Abschnitt 1).

## Invarianten

- **INV-01:** `unresolved` ist optional und nur bei `kind: write_ownership` erlaubt. Werte: `skip`
  (Default) oder `violation`.
- **INV-02:** Bei `skip` (oder ohne Feld) verhält sich die Regel exakt wie in CON-0194: Kanten mit
  unaufgelöstem Ziel werden ignoriert. Bestehende `architecture.yaml` ändern ihr Ergebnis nicht.
- **INV-03:** Bei `violation` ist jede `write`-Kante mit unaufgelöstem Ziel ein Verstoß, wenn ihre
  Quelldatei zu einer Schicht außerhalb von `owners` gehört. Dateien ohne Schicht bleiben
  ausgenommen (CON-0194 INV-02). Aufgelöste Ziele prüft die Regel unverändert gegen `paths`.
- **INV-04:** Der Verstoß-Schlüssel folgt CON-0194 INV-09: `symbol` ist die schreibende Funktion der
  Kante (z. B. `pathlib.Path.write_text`); damit lassen sich die Verstöße in der Baseline
  (CON-0198) festhalten.
- **INV-05:** Dieses Schema beschreibt nur die Differenz. Die Umsetzung nimmt `unresolved` additiv in
  das Artefakt von CON-0194 (`architekturregeln-und-baseline.schema.json`) und dessen Paketkopie
  auf; eine Regel ist gültig, wenn sie beiden Schemas genügt. CON-0194 INV-03 („keine fremden
  Felder“) gilt damit mit `unresolved` als zusätzlichem optionalem Feld von `write_ownership`.
- **INV-06:** CON-0193 INV-04 („unaufgelöste Kanten sind nie ein Verstoß“) gilt weiter, außer eine
  Regel mit `unresolved: violation` verlangt es. Solche Kanten zählen zusätzlich wie bisher in
  `architecture.unresolved_edges` (Messgröße des Extraktors, keine Doppelzählung von Verstößen).
- **INV-07 (bewusste Grenze):** Weil `symbol` nur die Schreibfunktion ist, teilen sich mehrere
  unaufgelöste Schreibzugriffe derselben Funktion in einer Datei einen Verstoß-Schlüssel. Ein
  weiterer solcher Zugriff in einer bereits eingetragenen Datei fällt deshalb nicht als neuer Verstoß
  auf; die Baseline ist für diesen Fall dateigenau, nicht zeilengenau.

## Beispiele

**Gültig:**
```yaml
- id: ARCH-01
  adr: ADR-0002
  kind: write_ownership
  paths: [".sdd/**", "docs/adr/**"]
  owners: [cli, entry]
  unresolved: violation
```

**Ungültig (und warum):**
```yaml
- id: ARCH-03
  adr: ADR-0004
  kind: forbidden_dependency
  from: [web]
  to_paths: ["tool/sdd_cli/llm/providers/**"]
  unresolved: violation
```
→ `unresolved` ist nur bei `write_ownership` erlaubt (INV-01).

## Validierung

- Schema: `.sdd/contracts/data/write-ownership-unaufgeloeste-schreibziele.schema.json`.
- INV-02 und INV-03 prüft TST-0237 an der Strategie `write_ownership` mit synthetischen Kanten.
