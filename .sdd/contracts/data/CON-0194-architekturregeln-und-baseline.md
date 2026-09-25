---
id: CON-0194
title: "Architekturregeln"
type: data
format: json-schema
spec: SPEC-0054
version: 0.2.0
status: approved
artifact: ".sdd/contracts/data/architekturregeln-und-baseline.schema.json"
tests: ["TST-0223"]
---

# Contract: Architekturregeln

> **Spec:** SPEC-0054 · **Typ:** Daten (JSON Schema) · **Status:** approved

## Zweck

Beschreibt `.sdd/architecture.yaml` (Schichten und Regeln, SPEC-0054 FR-05, FR-06). Die Baseline
bekannter Verstöße (FR-07) regelt CON-0198; sie nutzt den Verstoß-Schlüssel aus INV-09. Die Regeln sind die maschinell
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
  | `forbidden_dependency` | `from` und `to_layers` und/oder `to_paths` | `import` |
  | `allowed_dependencies` | `graph` | `import` |
  | `forbidden_call` | `in`, `calls` (optional `args_match`, `except`) | `call` |
  | `write_ownership` | `paths`, `owners` | `write` |
- **INV-04:** `allowed_dependencies`: Eine Kante zwischen zwei verschiedenen Schichten ist ein
  Verstoß, wenn die Zielschicht nicht in `graph[quellschicht]` steht. Kanten innerhalb einer Schicht
  sind immer erlaubt. Eine Quellschicht, die im Graphen fehlt, darf nichts außer sich selbst.
- **INV-05:** Bei `forbidden_dependency` stehen Zielschichten in `to_layers` und Zielpfade (Globs)
  in `to_paths`. Beide Felder werden nie gegenseitig umgedeutet; eine neue Schicht ändert die
  Bedeutung bestehender Regeln nicht.
- **INV-06:** `forbidden_call.calls` vergleicht mit `symbol` der Kante; `*` passt auf beliebige
  Zeichen außer `.`. `args_match` ist ein Regex, der auf mindestens ein Literal-Argument passen muss.
  Dateien in `except` sind ausgenommen.
- **INV-07:** Referenziert eine Regel eine Schicht, die in `layers` fehlt, ist die Regel `n/a`
  mit Grund „unbekannte Schicht“ und `sdd validate` meldet einen Fehler.
- **INV-08:** Jeder Verstoß entsteht aus genau einer Kante und übernimmt deren `file`, `line` und
  `symbol` (CON-0193 INV-05).
- **INV-09 (Verstoß-Schlüssel):** Ein Verstoß ist über `(rule, file, symbol)` identifiziert, mit
  derselben Bedeutung von `symbol` für jede Regelart:
  | Regelart | `symbol` des Verstoßes |
  |----------|------------------------|
  | `forbidden_dependency`, `allowed_dependencies` | importierter Name der verletzenden `import`-Kante |
  | `forbidden_call` | Aufrufname der `call`-Kante |
  | `write_ownership` | schreibende Funktion der `write`-Kante |

  `symbol` ist nie leer (Schema CON-0193). Der Schlüssel ist stabil gegenüber Zeilenverschiebungen.

## Beispiele

**Gültig (`architecture.yaml`):**
```yaml
version: 1
layers:
  web: ["tool/sdd_cli/web/**"]
  llm: ["tool/sdd_cli/llm/**"]
  cli: ["tool/sdd_cli/**"]          # nach web/llm, damit die erste passende Schicht gewinnt
rules:
  - { id: ARCH-01, adr: ADR-0007, kind: forbidden_dependency, from: web, to_paths: ["tool/sdd_cli/templates.py"] }
  - { id: ARCH-02, adr: ADR-0008, kind: allowed_dependencies, graph: { web: [cli], cli: [llm], llm: [] } }
  - { id: ARCH-04, adr: ADR-0010, kind: forbidden_call, in: [cli, web], calls: ["subprocess.*"],
      args_match: "^claude$", except: ["tool/sdd_cli/llm/providers/claude_cli.py"] }
```

**Ungültig (und warum):**
```yaml
rules:
  - { id: ARCH-01, kind: forbidden_dependency, from: web, to: [cli], calls: ["x"] }
```
→ Verstößt gegen INV-01 (`adr` fehlt), INV-03 (fremdes Feld `calls`) und INV-05 (`to` statt
`to_layers`/`to_paths`).

## Validierung

- Schema: `.sdd/contracts/data/architekturregeln-und-baseline.schema.json` für `architecture.yaml`.
- INV-01 (Existenz/Eindeutigkeit) und INV-07 prüft `sdd validate`; INV-02, INV-04 bis INV-06,
  INV-08 und INV-09 sind Auswertungssemantik und werden durch TST-0223 geprüft.
