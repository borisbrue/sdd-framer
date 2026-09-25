---
id: CON-0193
title: "Austauschformate sdd-deps, sdd-metrics und sdd-findings"
type: data
format: json-schema
spec: SPEC-0054
version: 0.1.0
status: draft
artifact: ".sdd/contracts/data/austauschformate-sdd-deps-sdd-metrics-und-sdd-findings.schema.json"
tests: ["TST-0222"]
---

# Contract: Austauschformate sdd-deps, sdd-metrics und sdd-findings

> **Spec:** SPEC-0054 · **Typ:** Daten (JSON Schema) · **Status:** draft

## Zweck

Legt die drei Ausgabeformate fest, die sdd-framer selbst definiert, weil es dafür keinen
verbreiteten Standard gibt (SPEC-0054 FR-02). Sie sind die universellen Auffangformate: Jedes
Werkzeug, das kein Standardformat (JUnit, SARIF, Cobertura, LCOV) liefert, erreicht den Kern über
einen Konverter im Projekt. Die Parser im Kern (Adapter) akzeptieren ausschließlich Dateien, die
diesem Schema genügen.

| Format         | Inhalt | Verbraucher |
|----------------|--------|-------------|
| `sdd-deps`     | Abhängigkeitskanten `import`/`call`/`write` | Regel-Strategien (CON-0194) |
| `sdd-metrics`  | benannte Zahlenwerte je Projekt oder Datei | Codequalitäts-Teilscore (CON-0196) |
| `sdd-findings` | Befunde mit Regel, Datei, Zeile, Schwere | `lint_per_kloc`, `type_errors` wie SARIF |

## Invarianten

- **INV-01:** Jede Datei trägt `format` und `version: 1`. Eine Datei, die dem Schema nicht genügt,
  macht die Sonde `n/a` (Grund „Ausgabe nicht parsebar“), sie wird nicht teilweise übernommen.
- **INV-02:** Alle Pfade sind relativ zur Projektwurzel, mit `/` getrennt, ohne `..` und ohne
  führenden `/`.
- **INV-03:** `sdd-deps.kinds_provided` nennt die Kantenarten, die der Extraktor **vollständig**
  liefert. Eine Regel, deren Kantenart fehlt, ist `n/a`, nicht erfüllt.
- **INV-04:** Eine Kante mit `to: null` hat `unresolved: true`. Unaufgelöste Kanten sind nie ein
  Verstoß, werden aber gezählt (`architecture.unresolved_edges` im Report).
- **INV-05:** Kanten der Art `call` tragen `symbol` (voll qualifizierter Name, z. B.
  `subprocess.run`) und, soweit statisch auflösbar, Literal-Argumente in `args`.
- **INV-06:** `sdd-metrics`-Namen sind `snake_case`. Derselbe Name mit `scope: project` darf je Datei
  nur einmal vorkommen. Mehrere dateibezogene Werte desselben Namens werden nicht aggregiert; das
  Projekt liefert die gewünschte Aggregation als `scope: project` (z. B. `complexity_max`).
- **INV-07:** `sdd-findings.severity` ist `error`, `warning` oder `note`. Für `lint_per_kloc` und
  `type_errors` zählen alle Schweregrade außer `note`.

## Beispiele

**Gültig (`sdd-deps`):**
```json
{
  "format": "sdd-deps", "version": 1,
  "tool": { "name": "extract_deps.py", "version": "1.0.0" },
  "kinds_provided": ["import", "call"],
  "edges": [
    { "from": "tool/sdd_cli/decompose.py", "to": "tool/sdd_cli/llm/providers/claude_cli.py",
      "kind": "import", "symbol": "ClaudeCliCompletionProvider", "file": "tool/sdd_cli/decompose.py", "line": 110 },
    { "from": "tool/sdd_cli/local_agent.py", "to": null, "kind": "call", "symbol": "subprocess.run",
      "args": ["claude"], "file": "tool/sdd_cli/local_agent.py", "line": 126, "unresolved": true }
  ]
}
```

**Ungültig (und warum):**
```json
{ "format": "sdd-deps", "version": 1, "kinds_provided": ["import"],
  "edges": [{ "from": "../other/x.py", "to": null, "kind": "import", "file": "x.py", "line": 1 }] }
```
→ Verstößt gegen INV-02 (`..` im Pfad) und INV-04 (`to: null` ohne `unresolved: true`).

## Validierung

- Schema: `.sdd/contracts/data/austauschformate-sdd-deps-sdd-metrics-und-sdd-findings.schema.json`
  (JSON Schema Draft 2020-12, `oneOf` über die drei Formate).
