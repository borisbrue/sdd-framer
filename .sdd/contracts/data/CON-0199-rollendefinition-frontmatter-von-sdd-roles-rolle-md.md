---
id: CON-0199
title: "Rollendefinition: Frontmatter von .sdd/roles/<rolle>.md"
type: data
format: json-schema
spec: SPEC-0053
version: 0.2.0
status: draft
artifact: ".sdd/contracts/data/rollendefinition-frontmatter-von-sdd-roles-rolle-md.schema.json"
tests: ["TST-0228"]
---

# Contract: Rollendefinition (Frontmatter von .sdd/roles/<rolle>.md)

> **Spec:** SPEC-0053 · **Typ:** Daten (JSON Schema) · **Status:** draft

## Zweck

Legt den Vertrag einer Rolle fest (SPEC-0053 FR-01 bis FR-04). Die Frontmatter beschreibt Eingaben,
Ausgabeschema, Rollen-Checks, Defaults und den Fallback-Komponentenblock; der Body der Datei ist der
System-Prompt. Die Modellwahl steht nicht hier, sondern in `llm.roles.<rolle>`.

## Invarianten

- **INV-01:** `inputs` stammt aus der geschlossenen Liste `spec`, `contracts`, `agents_md`,
  `repo_map`, `task`, `test_file`, `test_output`, `diff`, `gate_results`, `review`, `history`.
  `.sdd/holdout/` ist nie eine Quelle.
- **INV-02:** `output_schema` zeigt für jede Rolle auf ein Schema: Arbeitsrollen auf CON-0200
  (`…#/$defs/<rolle>`), `supervisor` auf das Command-Schema aus CON-0201. Es gibt keinen Sonderfall;
  der Check `json_schema` gilt für alle Rollen gleich.
- **INV-03:** `checks` nennt nur Rollen-Checks, die die **Ausgabe** der Rolle prüfen (Schema,
  Struktur, Vollständigkeit gegenüber der Eingabe). Prüfungen des Projektzustands sind Gates
  (SPEC-0054) und stehen hier nicht.
- **INV-04:** `legacy_component` ist der Komponentenblock, auf den die Provider-Auflösung
  zurückfällt, wenn `llm.roles.<rolle>` fehlt (SPEC-0053 FR-04).
- **INV-05:** `version` folgt SemVer. Eine Änderung des Prompts erhöht mindestens Minor, eine
  Änderung nur der Defaults Patch (SPEC-0055 FR-07).
- **INV-06:** Unbekannte Felder sind nicht erlaubt; ein Rollen-Check, der der Registry unbekannt ist,
  ist ein Validierungsfehler von `sdd validate` (Laufzeitprüfung).

## Beispiele

**Gültig:**
```yaml
role: decomposer
version: 1.2.0
purpose: "Zerlegt eine freigegebene Spec in testbare, abhängigkeitsgeordnete Tasks."
inputs: [spec, contracts, agents_md, repo_map]
input_budgets: { spec: 12000, repo_map: 4000 }
output_schema: "contracts/data/role-outputs.schema.json#/$defs/decomposer"
defaults: { thinking: true, max_output_tokens: 16000, temperature: 0.6 }
checks: [json_schema, fr_coverage, acyclic, deps_resolvable, test_file_per_code_task]
legacy_component: completion
```

**Ungültig (und warum):**
```yaml
role: decomposer
version: "1"
inputs: [spec, holdout]
checks: []
```
→ Verstößt gegen INV-01 (`holdout`), INV-05 (keine SemVer) und das Schema (`purpose`,
`output_schema`, `legacy_component` fehlen).

## Validierung

- Schema: `.sdd/contracts/data/rollendefinition-frontmatter-von-sdd-roles-rolle-md.schema.json`.
