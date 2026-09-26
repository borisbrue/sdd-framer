---
id: CON-0012
project: ""
title: "Orchestrator – Lokale Pipeline (Spec → Code → PR → Eval → Retry)"
type: behavior
format: markdown
spec: SPEC-0004
version: 0.2.0
status: deprecated
artifact: ""
tests: ["TST-0012"]
deprecated_reason: "Orchestrator durch sdd pipeline run --auto abgelöst (SPEC-0062)"
---

# Contract: Orchestrator – Lokale Pipeline

> **Spec:** SPEC-0004 · **Typ:** Verhalten · **Status:** draft

## Zweck

Der Orchestrator ist ein lokaler Python-Prozess (`sdd orchestrate`), der
einen vollständigen Dark-Factory-Durchlauf ausführt: Spec lesen → Code generieren →
Branch/Commit anlegen → PR erstellen → Evaluator laufen → bei Erfolg mergen,
bei Fehler bis zu 3× wiederholen.

CI-Systeme (GitHub Actions, GitLab CI, lokal) rufen `sdd orchestrate` als
dünnen Wrapper auf. Die Pipeline-Logik lebt ausschließlich in Python.

## Garantien

### G-01: CLI-Schnittstelle

```
sdd orchestrate --spec SPEC-XXXX
                [--base-url <URL>]
                [--build-cmd <cmd>]
                [--max-retries 3]
                [--no-pr]
                [--dry-run]
```

| Option          | Beschreibung                                                        |
|-----------------|---------------------------------------------------------------------|
| `--spec`        | Pflicht. Spec-ID, z.B. SPEC-0004.                                   |
| `--base-url`    | URL des zu testenden Services für den Evaluator-Schritt.            |
| `--build-cmd`   | Shell-Befehl für Build + Tests. Überschreibt `config.yaml`.         |
| `--max-retries` | Max. Wiederholungen bei Evaluator-Fehlschlag. Default: 3.           |
| `--no-pr`       | Überspringt PR-Erstellung (nützlich für lokale Läufe).              |
| `--dry-run`     | Zeigt generierten Code, schreibt/committed/pushed nicht.            |
| Env-Vars        | `SDD_EVAL_BASE_URL`, `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`.           |

### G-02: Pipeline-Schritte

> **v0.2.0 (2026-09-10):** Schritt 5 war seit SPEC-0026 (`45b29e6`) nicht mehr
> umgesetzt: der Build wurde aus der Orchestrator-Schleife entfernt, ohne in der
> gemeinsamen Finalisierung wieder angebunden zu werden. `--build-cmd` und
> `orchestrator.build_command` wirkten nicht (#111). Er läuft jetzt dort, wo auch
> die Tests laufen — damit gilt er für alle Implementierungspfade, nicht nur hier.

```
1. Spec + AGENTS.md + Contracts laden
2. Code-Generierung (Claude): strukturierter JSON-Response
3. Dateien schreiben (außer .sdd/holdout/)
4. git: Branch anlegen, Commit erstellen
5. Build-Kommando ausführen (optional) — in der Finalisierung (SpecFinalizer),
   im Dev-Container unmittelbar vor den Tests. Schlägt er fehl, laufen keine
   Tests, und die Build-Ausgabe wird Fehlerkontext des nächsten Versuchs.
6. PR erstellen via gh CLI (optional, --no-pr überspringt)
7. Evaluator laufen lassen (optional, nur wenn --base-url gesetzt)
8a. Pass-Rate ≥ 90 %: PR labeln ("sdd-auto-merge") oder mergen
8b. Pass-Rate < 90 %: Retry mit angereichertem Fehlerkontext
```

### G-03: Code-Generierungs-Prompt

Der Prompt an Claude MUSS enthalten:
- Den vollständigen Inhalt der Spec-Datei
- Den Inhalt von `AGENTS.md` (falls vorhanden)
- Den Inhalt aller in der Spec referenzierten Contracts
- Bei Retries: Evaluator-Report des letzten Durchlaufs als Fehlerkontext

Der Prompt DARF NICHT enthalten:
- Inhalte aus `.sdd/holdout/`
- Inhalte aus `.sdd/evaluations/`

### G-04: Code-Generierungs-Response-Format

Claude MUSS folgendes JSON-Format zurückgeben (system-prompt enforced):

```json
{
  "files": [
    { "path": "src/...", "content": "..." },
    { "path": "tests/...", "content": "..." }
  ],
  "explanation": "<eine Zeile was geändert wurde>"
}
```

Dateipfade sind relativ zum Projekt-Root. Der Orchestrator schreibt
jede Datei mit dem gegebenen Inhalt. Bestehende Dateien werden überschrieben.

### G-05: Retry-Logik

```
Attempt 1: Code generieren + Evaluator
  → Pass: weiter mit G-06
  → Fail: Evaluator-Report in Kontext einbetten
Attempt 2: Code re-generieren mit Fehlerkontext
  → Pass: weiter mit G-06
  → Fail: Fehlerkontext akkumulieren
Attempt 3: Code re-generieren mit akkumuliertem Kontext
  → Pass: weiter mit G-06
  → Fail: Pipeline-Status = "failed", Exit-Code 1
```

Hard-Cap: Maximal `--max-retries` Versuche. Danach bricht die Pipeline ab.

### G-06: PR-Labeling / Auto-Merge

Nach bestandenem Evaluator-Lauf:
- Setzt Label `sdd-auto-merge` auf den PR (via `gh pr edit`)
- Falls `auto_merge: true` in `.sdd/config.yaml`: führt `gh pr merge --squash` aus

### G-07: Pipeline-Report

Der Orchestrator persistiert einen Report in `.sdd/pipeline/YYYY-MM-DD-HHMMSS.json`:

```json
{
  "timestamp": "<ISO-8601>",
  "spec_id": "SPEC-XXXX",
  "branch": "sdd/SPEC-XXXX-attempt-1",
  "final_status": "merged | labeled | failed | dry_run",
  "attempts": [
    {
      "attempt": 1,
      "build_passed": true,
      "eval_pass_rate": 0.85,
      "pr_url": "https://github.com/...",
      "error": null
    }
  ]
}
```

### G-08: Sourcecode-Isolation (wie Evaluator)

Der Orchestrator DARF `.sdd/holdout/` nicht in den Code-Generierungs-Prompt einbetten.
Holdout-Szenarien bleiben dem Code-Agenten strukturell verborgen.

## Invarianten

- **INV-01:** Branch-Name hat immer das Format `sdd/<spec-id>-attempt-<n>`.
- **INV-02:** `--dry-run` verändert kein Dateisystem, keine Git-Objekte, keine GitHub-Ressourcen.
- **INV-03:** Bei fehlendem `gh` CLI und ohne `--no-pr` gibt der Orchestrator eine klare Warnung aus und überspringt den PR-Schritt (kein Abbruch).
- **INV-04:** `ANTHROPIC_API_KEY` ist Pflicht — fehlt er, bricht die Pipeline mit Exit-Code 1 ab.

## Begriffe

| Begriff          | Definition                                                             |
|------------------|------------------------------------------------------------------------|
| Attempt          | Ein vollständiger Pipeline-Lauf (Code-Gen → Build → Eval)             |
| Fehlerkontext    | Evaluator-Report + Build-Output des vorherigen Attempts               |
| Auto-Merge       | Automatisches Mergen eines PRs nach bestandenem Evaluator-Lauf        |
| dry-run          | Modus ohne Schreibzugriff — zeigt nur was getan würde                 |
