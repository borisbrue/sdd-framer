---
id: CON-0162
project: PRJ-0001
title: "Evaluation-Report JSON-Schema: tier_summary + priority-Feld"
type: data
format: markdown
spec: SPEC-0042
version: 0.1.0
status: approved
artifact: "contracts/data/evaluate-json-tier-summary.md"
tests: ["TST-0190"]
---

# Contract: Evaluation-Report JSON-Schema – tier_summary & priority

> **Spec:** SPEC-0042 · **Typ:** Daten · **Status:** draft

## Zweck

Definiert die Erweiterungen am JSON-Output von `sdd evaluate --output-json`:
das `priority`-Feld pro Szenario und den neuen `tier_summary`-Block.

## Schema-Erweiterung (JSON)

### Bestehendes Szenario-Objekt (Erweiterung)

```json
{
  "hol_id": "HOL-0016",
  "title": "...",
  "contract": "CON-0115",
  "passed": false,
  "priority": "critical",
  "task_delta": "Ändere lifecycle.py:expire_check() ...",
  "runs": [...]
}
```

Neues Pflichtfeld: `priority` (string, enum: `"critical"`, `"normal"`, `"edge-case"`).
Neues optionales Feld: `task_delta` (string | null) — enthält die LLM-generierte
Patch-Anweisung für den Agenten. Leer wenn kein Provider oder kein Evaluation Hint.

### Neuer Top-Level-Block: `tier_summary`

```json
{
  "timestamp": "...",
  "base_url": "...",
  "tier_summary": {
    "critical":  {"passed": 2, "failed": 0, "skipped": 0},
    "normal":    {"passed": 1, "failed": 1, "skipped": 0},
    "edge-case": {"passed": 0, "failed": 0, "skipped": 3}
  },
  "scenarios": [...]
}
```

`tier_summary` ist immer present wenn `--output-json` gesetzt ist.
Fehlende Tiers (keine Holdouts für diesen Tier) haben `{"passed": 0, "failed": 0, "skipped": 0}`.

## Invarianten

- `priority` ist immer aus dem Frontmatter des Holdout-Dokuments (`priority:`).
  Fehlt das Feld im Frontmatter: Fallback auf `"normal"`.
- `task_delta` ist `null` wenn kein LLM-Provider konfiguriert oder kein
  `## Evaluation Hint`-Block im Holdout vorhanden.
- `tier_summary.skipped` zählt Holdouts die per fail-fast übersprungen wurden.
- Die Summe `passed + failed + skipped` pro Tier entspricht der Anzahl aktiver
  Holdouts mit dieser Priorität.
