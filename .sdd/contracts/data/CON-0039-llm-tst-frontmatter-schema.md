---
id: CON-0039
project: PRJ-0001
title: "Schema des LLM-generierten TST-Frontmatters"
type: data
format: json-schema
spec: SPEC-0010
version: 0.1.0
status: review
artifact: "contracts/data/llm-tst-frontmatter.schema.json"
tests:
- TST-0053
---

# Contract: Schema des LLM-generierten TST-Frontmatters

> **Spec:** SPEC-0010 · **Typ:** Daten · **Status:** review

## Zweck

Definiert die Pflichtfelder einer von `sdd review-contract` generierten
TST-Datei. Das Frontmatter muss gegen das Standard-Test-Schema valide sein
und zusätzlich `generated_by: llm` enthalten.

## Zusätzliche Pflichtfelder (über Standard-TST-Schema hinaus)

| Feld | Wert | Pflicht |
|---|---|---|
| `generated_by` | `"llm"` | ja |
| `status` | `"draft"` | ja (immer draft bei LLM-Generierung) |
| `contract` | CON-ID des reviewten Contracts | ja |
| `spec` | SPEC-ID des zugehörigen Specs | ja |

## Beispiel-Frontmatter

```yaml
---
id: TST-0048
project: PRJ-0001
title: "LLM-Review: Status-Transition behavior"
spec: SPEC-0010
contract: CON-0037
level: contract
status: draft
generated_by: llm
---
```

## Invarianten

- `generated_by: llm` darf **nicht** vom LLM in den Status `approved` gesetzt werden
- LLM-Ausgabe wird als Body nach der Standardstruktur des TST-Templates angehängt
- TST-Datei wird unter `tests/contract/` abgelegt
- Bei ungültigem LLM-Output (kein parsierbares Frontmatter) wird die Datei
  **nicht** gespeichert und eine Fehlermeldung ausgegeben (E-03 in SPEC-0010)
