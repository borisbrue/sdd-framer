---
id: SPEC-0007
title: "Web UI Execute Flow – Spec-zu-Code Automatisierung"
status: implemented
owner: "Boris"
created: 2026-05-12
updated: 2026-05-14
version: 0.4.0
priority: high
tags: ["orchestration", "web-ui", "dark-factory", "automation", "execute"]
depends_on: ["SPEC-0003", "SPEC-0004"]
contracts: ["CON-0020", "CON-0021"]
tests: ["TST-0025", "TST-0026", "TST-0027"]
adrs: []
---

# Web UI Execute Flow – Spec-zu-Code Automatisierung

> **Status:** implemented · **Owner:** Boris · **Version:** 0.4.0

> **Hinweis (SPEC-0062):** Die Routen bleiben, dahinter läuft `sdd pipeline run --auto` (CON-0021 0.4.0). Die `run_id` ist die Run-ID der Pipeline unter `.sdd/runs/`.

## 1. Kontext & Motivation

Der Orchestrator (`sdd orchestrate`) ist voll implementiert (SPEC-0004, CON-0012),
aber ausschließlich als CLI-Werkzeug erreichbar. Ein Entwickler, der eine Spec
in der Web UI erstellt, analysiert und als `approved` markiert, muss die
Entwicklungsmaschine verlassen, ein Terminal öffnen und den Befehl manuell
eingeben — das unterbricht den Flow.

Ziel: **Ein "Execute"-Button in der Web UI** löst den vollständigen
Orchestrator-Zyklus aus. Agenten implementieren den Code, testen ihn und
melden zurück — ohne dass der Autor das Browser-Fenster verlässt.

## 2. Zielsetzung

**Primärziel:**
Ein Spec-Autor klickt in der Web UI auf "Execute", nachdem die Spec `approved`
ist. Der Orchestrator läuft autonom. Das Ergebnis — PR-URL, Pass-Rate oder
Fehlerbericht — erscheint direkt in der SpecDetail-Ansicht.

**Erfolgskriterien (messbar):**
- [ ] "Execute"-Button erscheint genau dann in SpecDetail, wenn `status == approved`
- [ ] `POST /api/orchestrate` startet den Orchestrator-Lauf als Background-Task
      und antwortet in < 500 ms mit einer `run_id`
- [ ] Polling `GET /api/pipeline/{run_id}` liefert den aktuellen Pipeline-Status
      (running | labeled | merged | failed) und Fortschritts-Text
- [ ] Nach erfolgreichem Lauf wird `status` in der Spec-Datei automatisch
      von `approved` auf `implemented` gesetzt
- [ ] Nach fehlgeschlagenem Lauf (alle Retries aufgebraucht) zeigt das UI
      den Evaluator-Report und die PR-URL an
- [ ] Während der Pipeline läuft, ist der "Execute"-Button deaktiviert und
      zeigt einen Lade-Indikator
- [ ] Execute-Modal zeigt Warnung wenn `claude` CLI nicht verfügbar ist
- [ ] Nach Seiten-Reload wird ein laufender Pipeline-Run via
      `GET /api/pipeline/active?spec_id=X` wiederhergestellt

**Nicht-Ziele (explizit):**
- Kein eigener Code-Generierungs-Prompt — der Orchestrator bleibt die einzige
  Implementierungsquelle (kein Parallelweg)
- Kein Multi-Spec-Execute (immer eine Spec pro Lauf)
- Kein eigener `ANTHROPIC_API_KEY` — der Orchestrator nutzt Claude Code CLI
  (gleicher Ansatz wie Analyzer in SPEC-0005)

**Implementiert über ursprüngliche Planung hinaus (v0.4.0):**
- Live-Log-Streaming via SSE (`GET /api/pipeline/{run_id}/log`) — war als Non-Goal klassifiziert,
  wurde implementiert, da der UX-Gewinn den Komplexitäts-Overhead überwiegt (§3.5)
- Abort-Funktion (`POST /api/pipeline/{run_id}/abort`) — war als Non-Goal klassifiziert,
  wurde implementiert, da ein hängender Orchestrator-Lauf sonst nur durch Prozess-Kill beendbar wäre (§3.6)

## 3. Architektur

```
Web UI (Browser)
  ↓ POST /api/orchestrate   { spec_id, project_id?, dry_run?, no_pr?, base_url? }
FastAPI (BackgroundTasks)
  → startet run_pipeline() als Background-Task
  ← HTTP 202: { run_id: "SPEC-0007-1747..."}

Web UI pollt alle 5 s:
  ↓ GET /api/pipeline/{run_id}
  ← { status: "running", current_step: "code_generation", attempts: [...] }
  ← { status: "labeled", pr_url: "https://...", pass_rate: 0.95 }
  ← { status: "failed",  attempts: [...], issue_url: "https://..." }

Nach Seiten-Reload:
  ↓ GET /api/pipeline/active?spec_id=SPEC-0007
  ← { run_id: "...", status: "running" }  oder  HTTP 404

Nach status == "labeled" | "merged":
  FastAPI patcht Spec-Frontmatter: status: approved → implemented
```

### 3.1 Orchestrator: Claude Code CLI statt Anthropic SDK

**Vorbedingung (Refactor):** `orchestrator._call_code_gen()` wird von der
direkten Anthropic-SDK-Nutzung (`anthropic.Anthropic()`) auf den
Claude Code CLI Subprocess umgestellt — identisch zur Implementierung in
`web/api/analyzer.py`:

```bash
claude --print --output-format json -p "<CODE_GEN_PROMPT>"
```

Der Outer-Wrapper `{"type":"result","result":"...","total_cost_usd":...}`
wird geparst, `result` enthält das bisherige JSON-Format
`{"files":[...],"explanation":"..."}`. Kein `ANTHROPIC_API_KEY` nötig.

**Graceful Degradation:** Fehlt `claude` im PATH, gibt
`POST /api/orchestrate` HTTP 503 zurück
(identisch zu SPEC-0005, CON-0013 G-04).

Dieser Refactor ist Teil von Phase A (Backend) und betrifft
`tool/sdd_cli/orchestrator.py`.

### 3.2 Pipeline-State-Store

Laufende und abgeschlossene Pipeline-Läufe werden in einem In-Memory-Dict
`_runs: dict[str, PipelineRunState]` gehalten (TTL 1 Stunde).
`PipelineRunState` enthält:
- `run_id`: `{spec_id}-{unix_timestamp_ms}`
- `status`: `running | labeled | merged | failed | dry_run`
- `current_step`: Freitext für den Polling-Client (z.B. "Code wird generiert…")
- `attempts`: Liste der bisherigen Versuche (jeweils `attempt_number`, `status`, `current_step`)
- `max_attempts`: `int` — maximale Wiederholungszahl; hartkodiert `3` in `orchestrator.py` (v1,
  kein Config-Parameter); als Feld in `PipelineRunState` exponiert, damit das Frontend
  "Attempt 1/3" ohne Kenntnis des Orchestrator-Defaults anzeigen kann
- `report`: `PipelineReport`-Objekt nach Abschluss (bei `status == running` ist `report: null`)
- `error`: Fehlermeldung bei unerwarteten Ausnahmen im Background-Task

**`PipelineReport`-Schema** (Pydantic-Modell in `web/api/routes/orchestrate.py`):
```python
class PipelineReport(BaseModel):
    pass_rate: float              # 0.0–1.0; 0.0 wenn kein Evaluator-Lauf erfolgte
    pr_url: str | None            # GitHub PR URL; None bei dry_run oder vor PR-Erstellung
    issue_url: str | None         # GitHub Issue URL (nur bei status=failed mit --create-issue)
    failed_scenarios: list[str]   # HOL-IDs z.B. ["HOL-0003", "HOL-0005"]; leer bei Erfolg
    reason: str | None            # Freitext-Fehlerursache (letzter Evaluator-Fehler); None bei Erfolg
    explanation: str | None       # Dry-run: generierter Erklärungstext aus code-gen; None sonst
```

**TTL-Ablauf:** Nach 1 Stunde wird der Eintrag aus `_runs` entfernt.
`GET /api/pipeline/{run_id}` gibt danach `HTTP 404` mit Body `{"detail": "run_not_found"}` zurück.
Das Frontend reagiert darauf — unabhängig davon, ob die `run_id` aus `sessionStorage` oder aus
einem laufenden Poll stammt — mit einem "Ergebnis nicht mehr verfügbar"-Banner (kein Hard-Fehler,
kein automatischer Retry) und löscht den `sessionStorage`-Key.

Ein zusätzlicher Index `_active: dict[str, str]` bildet `spec_id → run_id`
ab, solange `status == running`. Ermöglicht `GET /api/pipeline/active`.

### 3.3 Status-Auto-Transition

Nach beendetem Lauf mit `final_status in ("labeled", "merged")` patcht
das API-Backend die Spec-Datei via `frontmatter.patch_status()`:

```python
# tool/sdd_cli/frontmatter.py
def patch_status(path: Path, new_status: str) -> None:
    doc = parse(path)
    doc.frontmatter["status"] = new_status
    doc.write()
```

- Schreibt zurück — kein Git-Commit, kein Reload nötig
- Falls die Datei nicht schreibbar ist: Warnung im Pipeline-Report, kein Abbruch

**Explizites Nicht-Ziel:** `final_status == "dry_run"` löst **kein** `patch_status()` aus.
Dry-runs schreiben keine Dateien und erzeugen keinen PR; die Spec bleibt auf `approved`.
Implementierende sollen `dry_run` nicht versehentlich in den Trigger einschließen.

### 3.4 Execute-Gate

`POST /api/orchestrate` gibt folgende Fehlercodes zurück:

| HTTP | Bedingung                                              |
|------|--------------------------------------------------------|
| 404  | Spec nicht gefunden                                    |
| 422  | `status != approved`                                   |
| 409  | Lauf für diese Spec-ID bereits aktiv                   |
| 503  | `claude` CLI nicht im PATH / nicht eingeloggt          |

### 3.5 Live-Log-Streaming (SSE)

```
GET /api/pipeline/{run_id}/log
← text/event-stream
   data: [10:23:01] Code wird generiert…
   data: [10:23:45] ✓ Build erfolgreich
   event: done
   data:
```

Liefert alle bisher gepufferten Log-Zeilen aus `RunState.log` und streamt neue
Zeilen alle 500 ms nach, bis `status != running`. Nach Abschluss sendet der
Server ein abschließendes `event: done`-Frame und schließt den Stream.

TTL: Stream läuft maximal 1 Stunde (identisch zu `_TTL`). Fällt der Run-State
weg (TTL-Cleanup), sendet der Server sofort `event: done`.

Das Frontend öffnet den SSE-Stream parallel zum Polling. Polling bleibt die
autoritative Quelle für `status` und `attempts`; der SSE-Stream liefert nur
den Live-Log.

### 3.6 Pipeline-Abort

```
POST /api/pipeline/{run_id}/abort
← 200: { "aborted": true, "run_id": "…" }
← 404: run_id unbekannt
← 409: Run ist nicht mehr aktiv (bereits in terminalem Status)
```

Setzt `RunState.abort_requested = True` und ruft `proc.terminate()` auf dem
aktiven Subprocess auf. Der Orchestrator prüft `is_aborted()` zwischen den
Retry-Schritten und bricht sauber ab. Nach dem Abort setzt `_run_pipeline_bg`
`state.status = "aborted"` und schreibt das `report`-Feld.

Der Abort-Button erscheint im Status-Panel neben dem Titel, solange
`status == running`. Ein bestätigter Abort kann nicht rückgängig gemacht werden.

## 4. Feature-Details

### 4.1 Execute-Button (Web UI)

In `SpecDetail`:
- Sichtbar + aktiv: `status == approved` und kein laufender Pipeline-Run
- Sichtbar + deaktiviert (Spinner): laufender Pipeline-Run für diese Spec
- Ausgeblendet: alle anderen Status

Klick öffnet ein Bestätigungs-Modal. Das Modal ruft zuerst `GET /api/status` ab.
`GET /api/status` wird um folgende Felder erweitert (Phase A):
- `has_claude_cli: bool` — prüft ob `claude` im PATH verfügbar ist
- `evaluator_base_url: str | null` — liest `evaluator.base_url` aus `.sdd/config.yaml`;
  `null` wenn der Schlüssel fehlt oder keine `config.yaml` vorhanden ist

**Kein separater Config-Endpoint** — `GET /api/status` ist der einzige Weg, den
Config-Wert ans Frontend zu übermitteln. Begründung: Status-Abfrage und Config-Lesen
laufen ohnehin zusammen beim Modal-Öffnen; ein zweiter Roundtrip wäre unnötig.

- `has_claude_cli: false` → roter Warn-Banner: "Claude Code CLI nicht gefunden.
  Stelle sicher, dass `claude` im PATH installiert und eingeloggt ist."
  Der "Execute"-Button im Modal bleibt trotzdem aktiv (User kann es versuchen).

Modal-Inhalt:
- Spec-Titel und ID
- Eingabefeld: "Base-URL für Evaluator" — vorbelegt aus `evaluator_base_url` (aus
  `GET /api/status`), leer wenn `null`; überschreibbar
- Eingabefeld: "Project ID" — optional, vorbelegt aus Spec-Frontmatter (`project`)
- Checkbox: "Dry-run (kein Git-Commit, kein PR)" — default: aus
- Checkbox: "Ohne PR erstellen (--no-pr)" — default: aus
- Buttons: "Abbrechen" / "Execute"

### 4.2 Pipeline-Status-Panel

Nach dem Start: `run_id` wird in `sessionStorage` unter Key `sdd-pipeline-{spec_id}`
gespeichert. Bei Seiten-Reload prüft `SpecDetail`: `sessionStorage` → falls
vorhanden, Polling sofort fortsetzen. Zusätzlich `GET /api/pipeline/active?spec_id=X`
als Fallback wenn sessionStorage leer (z.B. nach Tab-Neustart).

**`sessionStorage`-Bereinigung** — der Key `sdd-pipeline-{spec_id}` wird in folgenden
Fällen gelöscht:
1. Polling empfängt einen terminalen Status (`labeled | merged | failed | dry_run`) und
   das Panel hat den Endzustand gerendert → Key sofort löschen.
2. User klickt erneut auf "Execute" → Key löschen *bevor* die neue `run_id` gespeichert wird.
3. `GET /api/pipeline/{run_id}` gibt `HTTP 404` zurück (TTL abgelaufen oder Server-Neustart)
   → Key löschen, "Ergebnis nicht mehr verfügbar"-Banner anzeigen.

**Attempt-Anzeige:** "Attempt 1/3" liest `max_attempts` direkt aus dem `PipelineRunState`-
Response-Feld (siehe §3.2); das Frontend trägt keinen Hartwert ein.

Panel-Zustände in SpecDetail:

```
⚙  Pipeline läuft — SPEC-0007 · Attempt 1/3
   Code wird generiert…

✓  Implementiert — PR: https://github.com/org/repo/pull/42
   Pass-Rate: 95 % · 1 Attempt · Status: implemented

✗  Pipeline fehlgeschlagen — 3 Attempts
   Fehlgeschlagene Szenarien: HOL-0003, HOL-0005
   PR: https://... (sdd:failed) · Issue: https://...

🔍 Dry-run abgeschlossen — Dateien wurden NICHT geschrieben
   Explanation: implement guided spec creation analyze endpoint
```

### 4.4 Live-Log und Abort (Web UI)

**Live-Log-Terminal:**
Das Status-Panel öffnet beim Start eines Pipeline-Runs einen SSE-Stream
(`GET /api/pipeline/{run_id}/log`). Jede Log-Zeile wird farbkodiert im
Terminal-Bereich dargestellt (grün = Erfolg, rot = Fehler, gelb = Fortschritt).
Das Terminal auto-scrollt auf neue Zeilen. Höhe: 220 px, overflow-y: auto.

**Abort-Button:**
Solange `status == running`, erscheint neben dem Panel-Titel ein roter
"⊘ Abbrechen"-Button. Ein Klick sendet `POST /api/pipeline/{run_id}/abort`.
Nach erfolgreichem Abort wechselt das Panel in den Zustand `aborted` (gelb):

```
⊘  Pipeline abgebrochen — 1 Attempt(s)
   Manuell abgebrochen
```

`sessionStorage`-Bereinigung gilt gleichermaßen für `aborted` wie für alle
anderen terminalen Status.

### 4.5 Lifecycle-Bereinigung (ehemals §4.3)

Der Status `active` wird aus dem `spec_lifecycle` in `.sdd/config.yaml`
entfernt. Bestehende Specs mit `status: active` geben bei `sdd validate`
eine `unknown_status`-**Warnung** aus (kein Hard-Fehler, Migration manuell).
Neuer empfohlener Übergang:

```
draft → review → approved ──[Execute]──→ implemented → deprecated
```

Migration: `status: active` ist semantisch unklar und wird nicht automatisch
auf `approved` gesetzt — jede Spec muss manuell bewertet werden.

## 5. User Stories

| ID    | Als ...    | möchte ich ...                                          | um ...                                         | Akzeptanzbedingung |
|-------|------------|---------------------------------------------------------|------------------------------------------------|--------------------|
| US-01 | Entwickler | auf "Execute" klicken wenn die Spec approved ist        | den Implementierungs-Zyklus zu starten         | Button nur bei status=approved sichtbar und aktiv |
| US-02 | Entwickler | den Fortschritt der Pipeline im Browser sehen           | zu wissen was der Agent gerade tut             | Status-Panel zeigt current_step und Attempt-Nummer |
| US-03 | Entwickler | nach erfolgreichem Lauf die PR-URL direkt sehen         | den PR sofort reviewen zu können               | PR-URL im Status-Panel als klickbarer Link |
| US-04 | Entwickler | dass der Spec-Status automatisch auf implemented wechselt | keine manuelle Nacharbeit zu haben             | Spec-Datei hat status=implemented nach erfolgreicher Pipeline |
| US-05 | Entwickler | bei Fehlschlag den Evaluator-Report sehen               | zu verstehen was nicht gepasst hat             | Status-Panel listet fehlgeschlagene HOL-IDs + Reason |
| US-06 | Entwickler | einen Dry-Run starten                                   | zu sehen was der Agent erzeugen würde          | Dry-run schreibt keine Dateien, erzeugt keinen Git-Commit; Panel zeigt Dry-run-Banner |
| US-07 | Entwickler | nach Seiten-Reload den Pipeline-Status sehen            | keine laufende Pipeline zu verpassen           | sessionStorage + GET /api/pipeline/active stellt Panel wieder her |
| US-08 | Entwickler | gewarnt werden wenn Claude CLI fehlt                    | zu wissen warum Execute scheitert              | Modal zeigt Warn-Banner wenn has_claude_cli: false |
| US-09 | Entwickler | Live-Log der Pipeline im Browser sehen                  | den Fortschritt detailliert zu verfolgen       | SSE-Stream zeigt jede Log-Zeile mit Timestamp im Terminal-Bereich |
| US-10 | Entwickler | einen laufenden Pipeline-Run abbrechen                  | kein Warten auf hoffnungslose Runs             | Abort-Button im Panel; nach Abort zeigt Panel status=aborted |

## 6. Nicht-funktionale Anforderungen

| Kategorie      | Anforderung                                                                            |
|----------------|----------------------------------------------------------------------------------------|
| Latenz         | POST /api/orchestrate antwortet in < 500 ms (Background-Task-Start)                   |
| Polling        | GET /api/pipeline/{run_id} antwortet in < 100 ms (In-Memory-Lookup)                   |
| Polling-Intervall | Client pollt alle 5 s; nach Abschluss stoppt Polling automatisch                  |
| State-TTL      | Abgeschlossene Run-States werden nach 1 Stunde aus dem In-Memory-Dict entfernt        |
| Parallelität   | Maximal 1 laufender Pipeline-Lauf pro Spec-ID gleichzeitig (409 sonst)               |
| Sicherheit     | Nur localhost-Betrieb (kein Auth nötig, identisch zu SPEC-0003)                       |
| Fehlertoleranz | Bei Absturz des FastAPI-Prozesses gehen laufende Runs verloren — kein Persistenz-Fallback in v1; `GET /api/pipeline/active` gibt dann 404 zurück |
| Crash + stale sessionStorage | Enthält `sessionStorage` noch eine `run_id` und liefert `GET /api/pipeline/{run_id}` nach Neustart 404, gilt dieselbe Regel wie TTL-Ablauf: "Ergebnis nicht mehr verfügbar"-Banner, Key löschen, kein Retry |
| Vorbedingung   | `claude` CLI muss im PATH installiert und eingeloggt sein (identisch zu SPEC-0005)    |

## 7. Implementierungs-Reihenfolge

```
Phase A: Backend
  └─ tool/sdd_cli/frontmatter.py: patch_status(path, new_status) hinzufügen
  └─ tool/sdd_cli/orchestrator.py: _call_code_gen() → Claude Code CLI Subprocess
     (ANTHROPIC_API_KEY entfernen, claude --print --output-format json nutzen)
  └─ CON-0020: Behavior-Contract Execute-Flow (Gherkin) ausformulieren
  └─ CON-0021: API-Contract OpenAPI-YAML erstellen
  └─ web/api/routes/orchestrate.py  — neuer Router mit:
       POST /api/orchestrate
       GET  /api/pipeline/{run_id}
       GET  /api/pipeline/active?spec_id=X
  └─ PipelineRunState-Store + _active-Index (In-Memory, TTL 1h)
  └─ FastAPI BackgroundTasks → run_pipeline() → patch_status() bei Erfolg
  └─ GET /api/status: `has_claude_cli` + `evaluator_base_url` ergänzen

Phase B: Web UI
  └─ Execute-Button in SpecDetail (gate: status=approved)
  └─ Bestätigungs-Modal (claude-CLI-Check, base_url aus config, project_id)
  └─ Pipeline-Status-Panel (Polling alle 5 s, sessionStorage-Persistenz)
  └─ Reload-Recovery: sessionStorage + GET /api/pipeline/active
  └─ api.ts: orchestrate(), getPipelineRun(), getActivePipeline(), abortPipeline(), streamPipelineLog()
  └─ Live-Log-Terminal (SSE, §3.5 / §4.4)
  └─ Abort-Button im Status-Panel (§3.6 / §4.4)

Phase C: Lifecycle-Cleanup
  └─ active aus spec_lifecycle in .sdd/config.yaml entfernen
  └─ sdd validate: unknown_status-Warnung für active-Specs

Phase D: Spec-Konformität (nachträgliche Korrekturen)
  └─ SpecDetail.js (Legacy) gelöscht — Konflikt mit SpecDetail.tsx
  └─ PipelineReport als top-level `report`-Feld in RunState + _to_dict() ergänzt (§3.2)
  └─ api.ts: PipelineReport-Interface + report-Feld in PipelineRunState
  └─ Spec aktualisiert: Non-Goals korrigiert, §3.5/§3.6/§4.4/§4.5 ergänzt, US-09/US-10 hinzugefügt
```

## 8. Offene Fragen

- [x] Soll der Evaluator-Base-URL im Execute-Modal eingegeben oder aus `.sdd/config.yaml`
      vorbelegt werden? → **config.yaml als Default (`evaluator.base_url`), im Modal überschreibbar**
- [x] Was passiert mit dem Status-Panel nach einem Seiten-Reload während die Pipeline läuft?
      → **`run_id` in `sessionStorage` + GET /api/pipeline/active?spec_id=X als Fallback**
- [x] Soll `status: active` in bestehenden Specs automatisch zu `approved` migriert werden?
      → **Nein — manuell; `active` ist semantisch unklar**
- [x] Soll `project_id` in den Request-Body?
      → **Ja, optional; Default leer; Backend liest Fallback aus Spec-Frontmatter**
- [x] ANTHROPIC_API_KEY oder Claude Code CLI für Orchestrator?
      → **Claude Code CLI (subprocess), identisch zu Analyzer — kein API-Key nötig**
- [x] Welche Felder hat `PipelineReport`?
      → **`pass_rate`, `pr_url`, `issue_url`, `failed_scenarios`, `reason`, `explanation` — Schema in §3.2 definiert**
- [x] Wie erhält das Frontend `evaluator.base_url` aus `config.yaml`?
      → **`GET /api/status` wird um `evaluator_base_url: str | null` erweitert — kein separater Endpoint**
- [x] Was gibt `GET /api/pipeline/{run_id}` nach TTL-Ablauf zurück?
      → **HTTP 404 `{"detail": "run_not_found"}` — Frontend zeigt "Ergebnis nicht mehr verfügbar"-Banner und löscht sessionStorage-Key**
- [x] Woher kennt das Frontend den Wert `3` für "Attempt 1/3"?
      → **`max_attempts: int` als Feld in `PipelineRunState`, hartkodiert 3 im Orchestrator (v1)**
- [x] Ist es bewusst, dass `dry_run` keinen `patch_status()`-Aufruf auslöst?
      → **Ja — explizites Nicht-Ziel in §3.3 dokumentiert**
- [x] Wann wird `sessionStorage`-Key `sdd-pipeline-{spec_id}` gelöscht?
      → **Bei terminalem Status, bei erneutem Execute-Klick, bei 404 — vollständige Regel in §4.2**
- [x] Was zeigt das UI bei Crash + stale sessionStorage (run_id liefert 404)?
      → **Identisch zu TTL-Ablauf: "Ergebnis nicht mehr verfügbar"-Banner + Key-Löschen — in §6 spezifiziert**

## 9. Änderungshistorie

| Datum      | Version | Autor   | Änderung                                                                          |
|------------|---------|---------|-----------------------------------------------------------------------------------|
| 2026-05-12 | 0.1.0   | Boris   | Initiale Erstellung                                                               |
| 2026-05-12 | 0.2.0   | Boris   | Analyse-Lücken geschlossen: Claude CLI statt SDK, patch_status(), sessionStorage + active-run Endpoint, project_id, has_claude_cli-Gate, Dry-run-Panel, US-07/08, §8 vollständig abgehakt |
| 2026-05-13 | 0.3.0   | Boris   | Review-Findings eingearbeitet: PipelineReport-Schema (§3.2), max_attempts als State-Feld, TTL-404-Verhalten, evaluator_base_url via GET /api/status, dry_run Nicht-Ziel in §3.3, sessionStorage-Bereinigungsregeln (§4.2), Crash+stale-sessionStorage-Fall (§6), §8 um 8 neue Fragen erweitert und abgehakt |
| 2026-05-14 | 0.4.0   | Boris   | Spec-Drift korrigiert: Non-Goals für SSE + Abort gestrichen (implementiert), §3.5/§3.6/§4.4/§4.5 neu, US-09/US-10 ergänzt, Phase D in §7, `report`-Feld (§3.2) als Top-Level im RunState nachgezogen, SpecDetail.js-Cleanup dokumentiert |
