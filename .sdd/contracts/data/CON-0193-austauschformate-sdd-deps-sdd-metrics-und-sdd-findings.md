---
id: CON-0193
title: "Austauschformate sdd-deps, sdd-metrics und sdd-findings"
type: data
format: json-schema
spec: SPEC-0054
version: 0.2.0
status: approved
artifact: ".sdd/contracts/data/austauschformate-sdd-deps-sdd-metrics-und-sdd-findings.schema.json"
tests: ["TST-0222"]
---

# Contract: Austauschformate sdd-deps, sdd-metrics und sdd-findings

> **Spec:** SPEC-0054 · **Typ:** Daten (JSON Schema) · **Status:** approved

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
- **INV-05:** Jede Kante trägt `symbol` mit fester Bedeutung je Art:
  | `kind` | `symbol` | `to` | `args` |
  |--------|----------|------|--------|
  | `import` | importierter Name (Modul oder Symbol) | importierte Datei | nicht erlaubt |
  | `call` | voll qualifizierter Aufrufname, z. B. `subprocess.run` | Datei der Definition, falls auflösbar | Literal-Argumente, soweit statisch auflösbar |
  | `write` | schreibende Funktion, z. B. `pathlib.Path.write_text` | geschriebener Pfad | nicht erlaubt |
- **INV-06:** `sdd-metrics`-Namen sind `snake_case`. Derselbe Name mit `scope: project` darf je Datei
  nur einmal vorkommen. Mehrere dateibezogene Werte desselben Namens werden nicht aggregiert; das
  Projekt liefert die gewünschte Aggregation als `scope: project` (z. B. `complexity_max`).
- **INV-07:** `sdd-findings.severity` ist `error`, `warning` oder `note` (SARIF-Vokabular). Wie
  Befunde gezählt werden, regelt CON-0196, nicht dieses Format. Das Vokabular ist bewusst ein
  anderes als `low|medium|high` bei Konflikt-Befunden (CON-0029): Code-Befunde und
  Spec-Konflikte sind getrennte Domänen und werden nicht gemeinsam gewertet.
- **INV-09 (JUnit):** Der JUnit-Parser ist genau einer und wird von `sdd quality measure` und
  `sdd test run` gemeinsam genutzt (CON-0197 INV-04). Es gibt keine zweite Pass/Fail-Semantik.
- **INV-08 (Gleichwertigkeit mit SARIF):** Der SARIF-Parser bildet jedes `result` auf genau einen
  Befund dieses Formats ab. `sdd-findings` und SARIF sind damit für alle Verbraucher austauschbar:
  | `sdd-findings` | aus SARIF |
  |----------------|-----------|
  | `rule` | `ruleId`, sonst `rule.id`, sonst `unknown` |
  | `message` | `message.text` |
  | `file` | `locations[0].physicalLocation.artifactLocation.uri`, `uriBaseId` aufgelöst, `file://` entfernt, relativ zur Projektwurzel (INV-02); Befunde außerhalb der Wurzel werden verworfen und gezählt |
  | `line` / `column` | `region.startLine` (fehlt: 1) / `region.startColumn` |
  | `severity` | `level`: `error` → `error`, `warning` oder fehlend → `warning`, `note`/`none` → `note` |

## Versionierung

Jedes Format trägt sein eigenes `version`-Feld und wird unabhängig weiterentwickelt. Eine neue
Formatversion erhöht die Contract-Version. Parser akzeptieren alle Versionen, die im Schema stehen.

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
    { "from": "tool/sdd_cli/web/api/routes/x.py", "to": ".sdd/specs/SPEC-0001.md", "kind": "write",
      "symbol": "pathlib.Path.write_text", "file": "tool/sdd_cli/web/api/routes/x.py", "line": 42 },
    { "from": "tool/sdd_cli/local_agent.py", "to": null, "kind": "call", "symbol": "subprocess.run",
      "args": ["claude"], "file": "tool/sdd_cli/local_agent.py", "line": 126, "unresolved": true }
  ]
}
```

**Ungültig (und warum):**
```json
{ "format": "sdd-deps", "version": 1, "kinds_provided": ["import"],
  "edges": [{ "from": "../other/x.py", "to": null, "kind": "import", "symbol": "x",
              "args": ["a"], "file": "x.py", "line": 1 }] }
```
→ Verstößt gegen INV-02 (`..` im Pfad), INV-04 (`to: null` ohne `unresolved: true`) und INV-05
(`args` bei `import`).

## Validierung

- Schema: `.sdd/contracts/data/austauschformate-sdd-deps-sdd-metrics-und-sdd-findings.schema.json`
  (JSON Schema Draft 2020-12, `oneOf` über die drei Formate).
