---
id: CON-0010
project: ""
title: "Evaluator – Standalone Python-Prozess"
type: behavior
format: markdown
spec: SPEC-0004
version: 0.1.0
status: draft
artifact: ""
tests: ["TST-0010"]
---

# Contract: Evaluator – Standalone Python-Prozess

> **Spec:** SPEC-0004 · **Typ:** Verhalten · **Status:** draft

## Zweck

Der Evaluator ist ein eigenständiger Python-Prozess (`sdd evaluate`), der
Holdout-Szenarien (HOL-XXXX) gegen einen laufenden Service ausführt und
ein aggregiertes Pass/Fail-Urteil zurückgibt – ohne Zugriff auf den Sourcecode.

## Garantien

### G-01: Sourcecode-Isolation

Der Evaluator-Prozess DARF zur Laufzeit KEINEN Zugriff auf den Sourcecode des
zu testenden Services haben. Er kommuniziert ausschließlich über HTTP.

### G-02: CLI-Schnittstelle

```
sdd evaluate --base-url <URL> [--hol HOL-XXXX ...] [--json] [--no-save]
```

| Option       | Beschreibung                                          |
|--------------|-------------------------------------------------------|
| `--base-url` | Pflicht. Basis-URL des laufenden Services.            |
| `--hol`      | Optional. Schränkt auf bestimmte HOL-IDs ein.         |
| `--json`     | JSON-Ausgabe statt Rich-Tabelle.                      |
| `--no-save`  | Unterdrückt Persistenz des Reports.                   |
| Env-Var      | `SDD_EVAL_BASE_URL` als Alternative zu `--base-url`.  |

### G-03: 3-Runs-Protokoll

Pro Holdout-Szenario führt der Evaluator **genau 3 Läufe** durch.
Ein Szenario gilt als **bestanden**, wenn mindestens **2 von 3** Läufen `passed: true` liefern.

### G-04: LLM-basierte Auswertung

**Schritt 1 – Planung:** Ein LLM (`claude-haiku-4-5-20251001`) leitet aus dem
Plain-English-Szenario einen HTTP-Request ab (Methode, Pfad, Header, Body).

**Schritt 2 – Ausführung:** Der abgeleitete HTTP-Request wird gegen `--base-url` gesendet.

**Schritt 3 – Bewertung:** Ein LLM bewertet Response und Szenario-Erwartung
und gibt `{"passed": bool, "reasoning": str}` zurück.

### G-05: Pass-Rate-Reporting

Der Evaluator gibt nach Abschluss aus:
- Pass-Rate (bestanden/gesamt) als Prozentsatz
- Ob die 90%-Auto-Merge-Schwelle erreicht ist
- Exit-Code 0 bei ≥ 90 %, Exit-Code 1 sonst

### G-06: Report-Persistenz

Sofern nicht mit `--no-save` deaktiviert, persistiert der Evaluator den Report als JSON
unter `.sdd/evaluations/YYYY-MM-DD-HHMMSS.json` mit folgendem Aufbau:

```json
{
  "timestamp": "<ISO-8601>",
  "base_url": "<URL>",
  "summary": { "total": N, "passed": N, "failed": N, "pass_rate": 0.95 },
  "scenarios": [
    {
      "hol_id": "HOL-0001",
      "title": "...",
      "contract": "CON-XXXX",
      "passed": true,
      "pass_count": 2,
      "runs": [...]
    }
  ]
}
```

### G-07: Hard-Cap

Der Evaluator bricht ab und gibt einen Fehler-Report zurück, wenn:
- `ANTHROPIC_API_KEY` nicht gesetzt ist
- Die Dependencies (`anthropic`, `httpx`) fehlen (klare Fehlermeldung mit Install-Befehl)

## Invarianten

- **INV-01:** Der Evaluator liest ausschließlich aus `.sdd/holdout/` – keine anderen Verzeichnisse.
- **INV-02:** Szenarien mit `status: disabled` oder `status: wip` werden übersprungen.
- **INV-03:** Ein einzelner HTTP-Timeout ≤ 10s bricht nur diesen Run ab, nicht den gesamten Lauf.

## Begriffe

| Begriff     | Definition                                                        |
|-------------|-------------------------------------------------------------------|
| Run         | Ein einzelner Durchlauf eines Holdout-Szenarios (max. 3 pro Szenario) |
| Pass-Rate   | Anteil bestandener Szenarien an der Gesamtanzahl                  |
| base_url    | Konfigurierbare Basis-URL des zu testenden Services               |

## Erweiterung durch SPEC-0054

Im `--auto`-Modus verlangt der Auto-Merge zusätzlich zur Schwelle aus G-05, dass alle
`quality.gates` bestanden sind (CON-0196). Für `holdout_pass_rate` im Quality-Report zählen
Szenarien mit `llm_verdict: "skip"` oder nur `error`-Läufen nicht (CON-0196, Formeltabelle).
