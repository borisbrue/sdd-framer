---
id: SPEC-0016
title: Asynchrone & persistente KI-Analyse – Hintergrundjobs, Benachrichtigungen und Verlauf
status: implemented
owner: Boris
created: 2026-05-16
updated: 2026-05-16
version: 0.1.0
priority: high
tags:
- frontend
- ux
- ai-analysis
- async
- persistence
- notifications
depends_on:
- SPEC-0003
- SPEC-0008
contracts:
- CON-0049
- CON-0050
- CON-0051
- CON-0052
- CON-0053
tests:
- TST-0064
- TST-0065
- TST-0066
- TST-0067
adrs: []
---
# Asynchrone & persistente KI-Analyse – Hintergrundjobs, Benachrichtigungen und Verlauf

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Die aktuelle `AnalyzePanel`-Komponente hat drei grundlegende Einschränkungen:

1. **Synchroner Blockieraufruf:** Der Klick auf „Analysieren" blockiert die UI, bis das LLM antwortet
   (~5–30 s). Der User kann währenddessen nicht weiterarbeiten.

2. **Kein Verlauf – keine Persistenz:** Analyseergebnisse existieren nur im React-State. Ein
   Seitenreload löscht alles. Jedes Tab-Close ist ein Verlust.

3. **Kontext-Overhead trotz erledigter Punkte:** Selbst beantwortete Fragen werden weiterhin
   als Volltext an das LLM gesendet (via `answered_questions`). Abgehakte Punkte reduzieren
   das Kontextfenster nicht.

Diese SPEC überarbeitet die KI-Analyse von Grund auf zu einem **asynchronen, persistenten
Analyse-System** mit vier Kernprinzipien:

- **Fire-and-forget:** Der Button startet einen Backend-Job und kehrt sofort zurück.
- **Push-Benachrichtigung:** Das Frontend wird informiert, wenn die Analyse fertig ist.
- **Persistenter Verlauf:** Jede Analyse wird an das Spec gebunden gespeichert und ist
  nach Reload sofort wieder abrufbar.
- **Kontext-Pruning:** Abgehakte Items werden aus dem LLM-Kontext bei Folge-Analysen entfernt.

## 2. Zielsetzung

**Primärziel:**
Der User startet eine KI-Analyse, arbeitet weiter, wird benachrichtigt wenn sie fertig ist,
sieht alle bisherigen Analysen im Verlauf und kann Items dauerhaft abhaken.

**Erfolgskriterien (messbar):**

- [ ] `POST /api/docs/{doc_id}/analyze/start` antwortet in < 200 ms mit einer `job_id`
- [ ] Der UI-Thread blockiert nicht während der Analyse läuft
- [ ] Eine In-App-Benachrichtigung erscheint ≤ 3 s nach Fertigstellung der Analyse
- [ ] Analyseergebnisse überleben einen Browser-Reload (Laden aus Backend-Storage)
- [ ] Mindestens die letzten 10 Analysen pro Spec sind im Verlauf abrufbar
- [ ] Abgehakte Items werden beim nächsten Analyselauf **nicht** an das LLM gesendet
- [ ] Abgehakte Items sind im UI als kollabierter „Erledigt"-Bereich sichtbar (nicht gelöscht)
- [ ] Ein abgehakter Item kann wieder aktiv gesetzt werden (Toggle)

**Nicht-Ziele (explizit):**
- WebSockets oder SSE in v0.1.0 (Polling reicht, SSE als optionales Upgrade)
- Analyseverlauf über mehrere Specs hinweg (kein globales Analyse-Dashboard)
- Automatisches Auslösen der Analyse bei Dateiänderungen (autoTrigger bleibt optional)
- Löschen von Analysen durch den User (Read-only Verlauf)
- Merge oder Vergleich von zwei Analyse-Snapshots

## 3. Architektur-Entscheidungen & Design Patterns

### 3.1 Command Pattern (Behavioral) — Job-Trigger

**Anwendung:** `POST /analyze/start` kapselt den Analyse-Wunsch als Command-Objekt (`AnalysisJob`).
Der FastAPI-Handler erstellt den Job und gibt ihn an den `AnalysisJobQueue` weiter, ohne
die HTTP-Response zu blockieren.

**Begründung:** Das Command Pattern entkoppelt den Aufrufer (HTTP-Handler) von der Ausführung
(LLM-Aufruf). Der Job kann zukünftig in eine echte Queue (Celery, ARQ) migriert werden,
ohne die API-Schnittstelle zu ändern.

**Alternative:** Der Handler selbst führt die Analyse in einem `asyncio.create_task()` aus —
einfacher, aber schlechter testbar (kein Pause/Cancel, kein Status-Tracking).

### 3.2 Repository Pattern (Structural) — Analyse-Persistenz

**Anwendung:** `AnalysisRepository` kapselt den Zugriff auf `.sdd/analyses/{spec_id}/`.
Schreibt `{timestamp}_{job_id}.json`, liest Listing und einzelne Analyse.

**Begründung:** Das Repository Pattern hält FastAPI-Routen und Dateisystemlogik getrennt.
Tests können ein InMemoryAnalysisRepository gegen dasselbe Interface einsetzen.

**Alternative:** Direkte Dateioperationen im Route-Handler — kürzer, aber nicht testbar
und nicht austauschbar gegen DB-Storage.

### 3.3 Observer Pattern (Behavioral) — Polling-Benachrichtigung

**Anwendung:** `GET /analyze/status/{job_id}` liefert `{status, result_id}`. Das Frontend
pollt alle 2 s solange `status == "running"`. Bei `status == "complete"` lädt es das
Ergebnis und zeigt eine In-App-Notification.

**Begründung:** Polling ist einfacher als SSE/WebSocket, funktioniert durch alle Proxys,
und ist vollständig zustandslos auf Server-Seite. Der Overhead (2 s × max. 60 Requests)
ist bei < 20 concurrent Usern vernachlässigbar.

**Upgrade-Pfad:** Wenn Polling zu teuer wird, ersetzt ein SSE-Endpoint den Poll-Loop
ohne Änderung der Repository- oder Job-Schicht.

### 3.4 Decorator Pattern (Structural) — Kontext-Pruning

**Anwendung:** `DismissalFilterDecorator` wraps die bestehende `analyze()`-Funktion.
Bevor der Prompt gebaut wird, filtert der Decorator alle `dismissed_ids` aus dem
Input-Content heraus und ergänzt eine System-Notiz.

**Begründung:** Die bestehende `analyze()`-Funktion bleibt unverändert (OCP). Der Decorator
kann deaktiviert werden oder durch einen anderen Filtermechanismus ersetzt werden.

## 4. Funktionale Anforderungen

### 4.1 Backend – Job-Verwaltung

**FR-01** `POST /api/docs/{doc_id}/analyze/start` nimmt `AnalyzeStartRequest`
(`content`, `doc_type`, `dismissed_ids: list[str]`) und antwortet sofort mit
`{ job_id: str, status: "queued" }`.

**FR-02** Der Job wird als `asyncio.create_task()` gestartet. Ergebnis und Status werden
in einem In-Memory-Dict (`JobStore`) gespeichert, kein External-Broker in v0.1.0.

**FR-03** `GET /api/docs/{doc_id}/analyze/status/{job_id}` antwortet mit:
```json
{ "status": "queued|running|complete|failed", "result_id": "2026-05-16T12:00:00_abc123" }
```
`result_id` ist nur bei `status == "complete"` gesetzt.

**FR-04** Bei `status == "failed"` enthält die Response zusätzlich `{ "error": "<message>" }`.

**FR-05** Jobs älter als 24 h werden aus dem `JobStore` gelöscht (Memory-Leak-Schutz).

### 4.2 Backend – Persistenz

**FR-06** Bei Fertigstellung eines Jobs schreibt `AnalysisRepository` das Ergebnis als:
```
.sdd/analyses/{doc_id}/{YYYY-MM-DDTHH:MM:SS}_{job_id[:8]}.json
```
Inhalt: vollständiges Analyse-Ergebnis (`questions`, `issues`, `suggestions`, `usage`,
`dismissed_ids`, `session_id`, `timestamp`).

**FR-07** `GET /api/docs/{doc_id}/analyses` antwortet mit einer Liste aller Analysen
(neueste zuerst), limitiert auf 50 Einträge:
```json
[{ "result_id": "...", "timestamp": "...", "question_count": 3, "issue_count": 1 }]
```

**FR-08** `GET /api/docs/{doc_id}/analyses/{result_id}` liefert das vollständige JSON
eines gespeicherten Analyse-Ergebnisses.

**FR-09** `PATCH /api/docs/{doc_id}/analyses/{result_id}/dismiss` nimmt
`{ "item_id": str, "dismissed": bool }` und aktualisiert die `dismissed_ids`-Liste
im gespeicherten JSON. Kein LLM-Aufruf.

### 4.3 Frontend – AnalyzePanel (Umbau)

**FR-10** Der „Analysieren"-Button ruft `POST /analyze/start` auf und zeigt sofort
einen Status-Indikator „⏳ Analyse läuft…" an, ohne die restliche UI zu blockieren.

**FR-11** Das Panel startet einen Poll-Loop: alle 2 s wird `/analyze/status/{job_id}`
gefragt. Bei `complete` stoppt der Loop, lädt das Ergebnis und zeigt eine
In-App-Notification (Toast): „✓ Analyse für {doc_id} abgeschlossen".

**FR-12** Beim ersten Öffnen des Panels (oder bei Reload) wird `GET /analyses` gerufen.
Die neueste Analyse wird automatisch geladen und angezeigt.

**FR-13** Ein Dropdown/Selektor zeigt alle verfügbaren Analysen (Timestamp + Kurzinfo).
Der User kann ältere Analysen ansehen (read-only).

**FR-14** Jedes Question-, Issue- und Suggestion-Item hat eine Checkbox „Abhaken".
Klick ruft `PATCH /analyses/{result_id}/dismiss` auf. Das Item wird lokal als
`dismissed` markiert, kollabiert und in einen „Erledigt"-Bereich verschoben.

**FR-15** Beim nächsten Analyse-Start (`POST /analyze/start`) werden alle `dismissed_ids`
aus der **aktuell geladenen** Analyse mitgeschickt. Das Backend filtert diese Items
aus dem Prompt.

**FR-16** Ein abgehaktes Item zeigt ein „↩ Wiederherstellen"-Link. Klick ruft
`PATCH /dismiss` mit `dismissed: false` auf und stellt das Item wieder her.

**FR-17** Der Dismissed-Bereich ist standardmäßig kollabiert mit Label
„{N} erledigte Punkte". Ein Klick expandiert ihn.

### 4.4 In-App-Notification

**FR-18** Der `NotificationContext` (React Context) verwaltet eine Liste von Toasts
mit `{ id, message, type: "success|error|info", duration_ms }`.

**FR-19** Toasts erscheinen oben rechts, auto-dismiss nach 5 s, können manuell
geschlossen werden.

**FR-20** `NotificationContext` ist unabhängig von `AnalyzePanel` — andere Komponenten
können ihn ebenfalls nutzen (Vorbereitung für Orchestrator-Notifications).

## 5. Nicht-funktionale Anforderungen

| Attribut | Anforderung |
|---|---|
| Latenz Job-Start | < 200 ms (kein LLM-Blocking) |
| Poll-Intervall | 2 s |
| Max. Job-Laufzeit | 120 s (dann `status: "failed"` mit Timeout-Meldung) |
| Analyse-Verlauf | ≥ 10 Einträge persistent, ≥ 50 via API |
| Dateigröße pro Analyse | < 100 KB (JSON) |
| Concurrent Jobs | ≤ 5 gleichzeitig (Throttle per Doc-ID) |

## 6. User Stories

| ID | Als… | möchte ich… | damit… |
|---|---|---|---|
| US-001 | Autor | die Analyse starten und sofort weitertippen können | ich nicht blockiert werde |
| US-002 | Autor | eine Benachrichtigung erhalten wenn die Analyse fertig ist | ich den richtigen Zeitpunkt zum Reviewen weiß |
| US-003 | Autor | frühere Analysen nach einem Reload noch sehen | ich keine Ergebnisse verliere |
| US-004 | Autor | einzelne Punkte abhaken | sie das LLM-Kontextfenster nicht mehr belasten |
| US-005 | Autor | abgehakte Punkte wieder reaktivieren | ich bei Bedarf zurückgehen kann |
| US-006 | Autor | den Analyse-Verlauf durchblättern | ich Verbesserungen über Zeit nachverfolgen kann |

## 7. Datenmodell

### AnalysisJob (In-Memory)
```python
@dataclass
class AnalysisJob:
    job_id: str              # UUID4
    doc_id: str
    status: str              # queued | running | complete | failed
    result_id: str | None    # Dateiname ohne Extension
    error: str | None
    created_at: datetime
```

### PersistedAnalysis (JSON-Datei)
```json
{
  "result_id": "2026-05-16T12:00:00_abc12345",
  "doc_id": "SPEC-0016",
  "timestamp": "2026-05-16T12:00:00Z",
  "session_id": "sess-xyz",
  "dismissed_ids": [],
  "questions": [...],
  "issues": [...],
  "suggestions": [...],
  "usage": { "input_tokens": 1200, "output_tokens": 340 }
}
```

## 8. API-Übersicht

| Methode | Pfad | Beschreibung |
|---|---|---|
| `POST` | `/api/docs/{doc_id}/analyze/start` | Startet asynchronen Analyse-Job |
| `GET` | `/api/docs/{doc_id}/analyze/status/{job_id}` | Poll-Endpunkt für Job-Status |
| `GET` | `/api/docs/{doc_id}/analyses` | Listing aller persistierten Analysen |
| `GET` | `/api/docs/{doc_id}/analyses/{result_id}` | Vollständige gespeicherte Analyse |
| `PATCH` | `/api/docs/{doc_id}/analyses/{result_id}/dismiss` | Item abhaken / reaktivieren |

Der bestehende `PUT /api/docs/{doc_id}/analyze`-Endpunkt **bleibt erhalten** (Backward-Kompatibilität,
z. B. für CLI-Nutzung via `sdd validate`).

## 9. Implementierungsreihenfolge

1. `AnalysisRepository` + Dateistruktur `.sdd/analyses/{doc_id}/`
2. `JobStore` (In-Memory Dict mit Cleanup)
3. FastAPI-Routen: `start`, `status`, `listing`, `detail`, `dismiss`
4. Backend-Integration: `analyze()` → `DismissalFilterDecorator`
5. React `NotificationContext` + Toast-Komponente
6. `AnalyzePanel` Umbau: Poll-Loop, Verlauf-Selektor, Dismissed-Sektion
7. E2E-Test: Button → Job → Poll → Notification → Reload → Verlauf sichtbar

## 10. Offene Fragen

- [ ] Sollen Analysen auch über `sdd` CLI auslösbar sein (nicht nur via Web-UI)?
- [ ] Wie lange sollen persistierte Analysen aufbewahrt werden (kein Ablaufdatum vs. 90 Tage)?
- [ ] SSE als Option für v0.2.0: Lohnt sich die Komplexität bei < 5 concurrent Usern?
