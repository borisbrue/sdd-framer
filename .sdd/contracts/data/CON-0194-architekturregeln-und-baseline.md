---
id: CON-0194
title: "Architekturregeln und Baseline"
type: data
format: json-schema
spec: SPEC-0054
version: 0.1.0
status: draft
artifact: ".sdd/contracts/data/architekturregeln-und-baseline.schema.json"
tests: ["TST-0223"]
---

# Contract: Architekturregeln und Baseline

> **Spec:** SPEC-0054 · **Typ:** Daten (JSON Schema) · **Status:** draft

## Zweck

Beschreibt `.sdd/architecture.yaml` (Schichten und Regeln, SPEC-0054 FR-05, FR-06) und
`.sdd/quality/arch-baseline.json` (bekannte Verstöße, FR-07). Die Regeln sind die maschinell
prüfbare Folge von Architekturentscheidungen; das Warum steht im ADR, auf das jede Regel verweist.
Ausgewertet werden die Regeln von je einer Strategie pro `kind` auf den Kanten aus `sdd-deps`
(CON-0193).

## Invarianten

- **INV-01:** Jede Regel hat eine eindeutige `id` (`ARCH-NN`) und ein `adr` (`ADR-NNNN`).
  Eindeutigkeit und Existenz des ADR prüft `sdd validate` (Fehler), nicht das Schema.
- **INV-02:** Eine Datei gehört zur **ersten** Schicht in Deklarationsreihenfolge, deren Glob passt.
  Dateien ohne Schicht werden von Schichtregeln ignoriert und im Report nicht als Verstoß gezählt.
- **INV-03:** Jede Regel enthält genau die Felder ihrer Art, keine fremden:
  | `kind` | Pflichtfelder | benötigte Kantenart |
  |--------|---------------|---------------------|
  | `forbidden_dependency` | `from`, `to` | `import` |
  | `allowed_dependencies` | `graph` | `import` |
  | `forbidden_call` | `in`, `calls` (optional `args_match`, `except`) | `call` |
  | `write_ownership` | `paths`, `owners` | `write` |
- **INV-04:** `allowed_dependencies`: Eine Kante zwischen zwei verschiedenen Schichten ist ein
  Verstoß, wenn die Zielschicht nicht in `graph[quellschicht]` steht. Kanten innerhalb einer Schicht
  sind immer erlaubt. Eine Quellschicht, die im Graphen fehlt, darf nichts außer sich selbst.
- **INV-05:** `to` bei `forbidden_dependency` enthält Schichtnamen oder Globs. Ein Eintrag, der einem
  Schichtnamen entspricht, wird als Schicht gelesen, sonst als Glob.
- **INV-06:** `forbidden_call.calls` vergleicht mit `symbol` der Kante; `*` passt auf beliebige
  Zeichen außer `.`. `args_match` ist ein Regex, der auf mindestens ein Literal-Argument passen muss.
  Dateien in `except` sind ausgenommen.
- **INV-07:** Referenziert eine Regel eine Schicht, die in `layers` fehlt, ist die Regel `n/a`
  mit Grund „unbekannte Schicht“ und `sdd validate` meldet einen Fehler.
- **INV-08 (Baseline):** Ein Baseline-Eintrag passt auf einen Verstoß genau dann, wenn `rule`,
  `file` und `symbol` gleich sind. Passende Verstöße werden auf `warn` herabgestuft und im Report
  mit `baselined: true` markiert. Einträge ohne passenden Verstoß zählen als
  `stale_baseline_entries`.

## Beispiele

**Gültig (`architecture.yaml`):**
```yaml
version: 1
layers:
  web: ["tool/sdd_cli/web/**"]
  llm: ["tool/sdd_cli/llm/**"]
  cli: ["tool/sdd_cli/**"]          # nach web/llm, damit die erste passende Schicht gewinnt
rules:
  - { id: ARCH-02, adr: ADR-0008, kind: allowed_dependencies, graph: { web: [cli], cli: [llm], llm: [] } }
  - { id: ARCH-04, adr: ADR-0010, kind: forbidden_call, in: [cli, web], calls: ["subprocess.*"],
      args_match: "^claude$", except: ["tool/sdd_cli/llm/providers/claude_cli.py"] }
```

**Gültig (`arch-baseline.json`):**
```json
{ "version": 1, "entries": [
  { "rule": "ARCH-03", "file": "tool/sdd_cli/decompose.py", "symbol": "ClaudeCliCompletionProvider",
    "reason": "Decomposer hart auf Claude verdrahtet", "fixed_by": "SPEC-0053" } ] }
```

**Ungültig (und warum):**
```yaml
rules:
  - { id: ARCH-01, kind: forbidden_dependency, from: web, to: [cli], calls: ["x"] }
```
→ Verstößt gegen INV-01 (`adr` fehlt) und INV-03 (fremdes Feld `calls`).

## Validierung

- Schema: `.sdd/contracts/data/architekturregeln-und-baseline.schema.json`. Die Wurzel gilt für
  `architecture.yaml`, `$defs/baseline` für `arch-baseline.json`.
- INV-01 (Existenz/Eindeutigkeit) und INV-07 prüft `sdd validate`; INV-02, INV-04 bis INV-06 und
  INV-08 sind Auswertungssemantik und werden durch TST-0223 geprüft.
