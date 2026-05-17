---
id: SPEC-0005
project: PRJ-0001
title: "KI-gestützte geführte Spec- und Contract-Erstellung"
status: implemented
owner: "Boris"
created: 2026-05-12
updated: 2026-05-12
version: 1.1.0
priority: high
tags: ["guided", "ai-assist", "web-ui", "claude-code", "ux"]
depends_on: ["SPEC-0003"]
contracts: ["CON-0013", "CON-0014"]
tests: ["TST-0013"]
adrs: []
---

# KI-gestützte geführte Spec- und Contract-Erstellung

> **Status:** implemented · **Owner:** Boris · **Version:** 1.1.0

## 1. Kontext & Motivation

Specs und Contracts sind nur so gut wie ihr Inhalt. Aktuell liegt die
Qualitätssicherung vollständig beim Autor: Fehlende Erfolgskriterien,
unpräzise Verhaltensbeschreibungen oder vergessene Randfälle werden erst
beim Code-Review oder — schlimmer — beim Evaluator-Lauf sichtbar.

Ziel dieser Spec ist ein **geführter Erstellungsmodus** in der Web UI, der
während des Schreibens gezielt nachfragt:
- "Was passiert, wenn der Nutzer das Formular ohne Titel abschickt?"
- "Welche HTTP-Status-Codes soll der Contract abdecken?"
- "Fehlt noch ein messbares Erfolgskriterium für diese User Story."

Die KI läuft als **Claude Code CLI Subprocess** im sdd-web-api-Prozess — kein
eigener API-Key nötig, die bestehende Claude Code Authentifizierung des Users
wird genutzt.

## 2. Zielsetzung

**Primärziel:**
Der Autor erhält während der Erstellung kontextsensitive, dokumentspezifische
Rückfragen und Hinweise — nicht generische Checklisten.

**Erfolgskriterien (messbar):**
- [ ] "Analyze"-Aufruf liefert in < 5 s mindestens eine konkrete Nachfrage
- [ ] Fragen referenzieren immer einen konkreten Abschnitt des Dokuments
- [ ] Analyse ohne laufenden ANTHROPIC_API_KEY funktioniert (nur Claude Code CLI)
- [ ] Keine Frage wird zweimal gestellt, wenn der Autor sie bereits beantwortet hat
- [ ] Gilt für Spec- und Contract-Dokumente (beide Typen unterstützt)

**Nicht-Ziele (explizit):**
- Vollautomatisches Ausfüllen von Specs (Autor bleibt Hauptverantwortlicher)
- Unterstützung für TST- und ADR-Dokumente (separates Feature)
- Integration in die VS Code Extension (folgt in SPEC-0006)

## 3. Architektur

```
Web UI (Browser)
  ↓ PUT /api/docs/{id}/analyze  (Dokument-Inhalt als Body)
sdd-web-api (FastAPI)
  ↓ subprocess: claude --print --output-format json -p "<prompt>"
Claude Code CLI  (bestehende User-Auth, kein eigener API-Key)
  ↓ JSON: { "questions": [...], "issues": [...], "suggestions": [...] }
sdd-web-api parst Response
  ↓ HTTP 200: AnalysisResult
Web UI rendert Fragen als Inline-Panel neben dem Editor
```

### 3.1 Claude Code CLI-Aufruf

```bash
claude --print --output-format json -p "<ANALYSIS_PROMPT>"
```

Der Prompt enthält:
- Dokumenttyp (spec | contract)
- Aktuellen Dokumentinhalt (Markdown + Frontmatter, max. 50 000 Zeichen)
- Bisherige Fragen + Antworten dieser Session (Kontext-Akkumulation)
- Anweisung: strukturiertes JSON zurückgeben

**Timeout:** 120 Sekunden. Überschreitet der Subprocess dieses Limit, wird er beendet
und der Endpoint gibt HTTP 504 zurück. Ein stilles Weiterwarren findet nie statt.

### 3.2 Response-Format (von Claude Code CLI)

```json
{
  "questions": [
    {
      "id": "q1",
      "section": "Erfolgskriterien",
      "text": "Was passiert, wenn der Nutzer das Formular ohne Titel abschickt?",
      "severity": "error | warning | suggestion"
    }
  ],
  "issues": [
    {
      "section": "User Stories",
      "text": "US-02 hat kein messbares Erfolgskriterium.",
      "severity": "warning"
    }
  ],
  "suggestions": [
    {
      "text": "Für diesen Contract-Typ empfiehlt sich ein SLO für Response-Zeit."
    }
  ]
}
```

**ID-Stabilität:** Das `id`-Feld (z.B. `"q1"`) ist ein von Claude generierter Kurzslug
und hat keine formale Stabilitätsgarantie über mehrere Analyse-Läufe. In der Praxis
wählt Claude konsistente Slugs solange der Dokumentinhalt gleich bleibt. Ändert sich
der Inhalt erheblich, können neue IDs vergeben werden — beantwortete Fragen können dann
erneut erscheinen. Dies ist eine bekannte Einschränkung von v1; eine hash-basierte
Fragen-ID (z.B. über Abschnitt + gekürzten Fragetext) ist als Verbesserung vorgesehen.

### 3.3 Session-Tracking

Der Session-State ist **zweischichtig**:

| Schicht | Speicherort | Lebensdauer |
|---------|-------------|-------------|
| Beantwortete Fragen (Client) | React-State im Browser | Bis Seiten-Reload / Tab-Schließen |
| Session-Akkumulation (Server) | In-Memory (`_sessions`-Dict) | TTL 1 Stunde seit letzter Nutzung |

Der Client schickt bei jedem Analyze-Aufruf die bisher beantworteten Fragen als
`answered_questions` mit. Der Server akkumuliert sie in der Session und filtert sie
aus der nächsten Response heraus.

**Reload-Verhalten:** Ein Seiten-Reload löscht den Browser-State (beantwortete Fragen
sind im Panel nicht mehr sichtbar). Die Server-Session bleibt erhalten (TTL 1 h),
hat aber keine Auswirkung ohne die Client-seitigen Antworten.

**Mehrere Tabs:** Jeder Tab hat seinen eigenen Browser-State. Zwei Tabs können dieselbe
`session_id` verwenden; beantwortete Fragen des jeweils anderen Tabs sind dem Server
bekannt, aber im anderen Tab-Panel nicht sichtbar. Schreibkonflikte werden durch
additives Merging auf dem Server aufgelöst (INV-02 in CON-0013).

## 4. Feature-Details

### 4.1 "Analyze"-Trigger (Web UI)

- **Manuell:** Button "KI-Analyse" im Spec/Contract-Editor
- **Auto-Trigger:** optional nach 3 s Inaktivität (konfigurierbar, default: off)

### 4.2 Inline-Fragen-Panel

Neben dem Markdown-Editor öffnet sich ein Panel mit:
- Fragen gruppiert nach Abschnitt (Section-Header aus dem Dokument)
- Severity-Icons (🔴 error / 🟡 warning / 💡 suggestion)
- Pro Frage: Freitext-Antwortfeld + "Beantwortet"-Toggle
- Beantwortete Fragen werden ausgegraut, nicht entfernt (Kontext bleibt sichtbar)

### 4.3 Analyse-Prompt-Template

Das Prompt-Template liegt in `.sdd/templates/analysis/spec-prompt.md` bzw.
`contract-prompt.md` und ist pro Projekt anpassbar.

### 4.4 Keine ANTHROPIC_API_KEY-Abhängigkeit

Der sdd-web-api-Prozess ruft `claude` als Subprocess auf. Voraussetzung:
- `claude` CLI ist im PATH installiert (`which claude` → Pfad)
- User ist in Claude Code eingeloggt
Fehlt `claude`, gibt der Endpoint HTTP 503 mit klarer Fehlermeldung zurück.

## 5. User Stories

| ID    | Als ...     | möchte ich ...                                         | um ...                                      | Akzeptanzbedingung |
|-------|-------------|--------------------------------------------------------|---------------------------------------------|--------------------|
| US-01 | Spec-Autor  | während des Schreibens gezielt befragt werden          | keine Lücken im fertigen Dokument zu haben  | Analyze-Button liefert ≥ 1 konkrete Frage für ein unvollständiges Dokument |
| US-02 | Spec-Autor  | sehen, welcher Abschnitt die Frage betrifft            | schnell navigieren zu können                | Jede Frage zeigt den Abschnittsnamen als Label; kein Auto-Scroll in v1 |
| US-03 | Spec-Autor  | beantwortete Fragen als erledigt markieren             | den Überblick zu behalten                   | Beantwortet-Toggle graut die Frage aus; sie bleibt sichtbar |
| US-04 | Contract-Autor | für meinen Contract-Typ passende Fragen bekommen   | z.B. bei Gherkin: Szenarien und Randfälle   | `doc_type: contract` verwendet contract-prompt.md Template |
| US-05 | Spec-Autor  | keine bereits beantworteten Fragen erneut gestellt bekommen | effizient arbeiten zu können          | Beantwortete IDs werden serverseitig gefiltert (solange Session aktiv und Dokument unverändert) |

## 6. Nicht-funktionale Anforderungen

| Kategorie          | Anforderung                                                                     |
|--------------------|---------------------------------------------------------------------------------|
| Latenz             | Analyze-Aufruf: < 5 s bis erste Frage sichtbar (kein Streaming in v1)          |
| Timeout            | CLI-Subprocess-Timeout: 120 s; danach HTTP 504, kein stilles Weiterwarren      |
| Verfügbarkeit      | Ohne Claude Code CLI: Graceful Degradation (HTTP 503, kein Crash)              |
| Datenschutz        | Dokument-Inhalt verlässt Maschine nur über Claude Code CLI (lokal)             |
| Sicherheit         | Endpoint ist nicht auth-gesichert; ausschließlich für localhost-Betrieb vorgesehen. Kein Einsatz in Multi-User-Netzwerken ohne vorgelagerte Auth. |
| Dokumentgröße      | Dokumentinhalt wird serverseitig auf 50 000 Zeichen gekürzt (CON-0013 INV-03) |
| Session-Größe      | Akkumulierte Antworten werden auf max. 20 beantwortete Fragen begrenzt; älteste werden verdrängt |
| Max. Fragen        | Pro Analyze-Aufruf maximal 5 Fragen in der Response (CON-0013 G-05)           |
| Konfigurierbarkeit | Auto-Trigger-Delay in `.sdd/config.yaml` einstellbar (default: off)           |

## 7. Implementierungs-Reihenfolge

```
Phase A: Backend
  └─ CON-0013: Claude-Code-CLI-Subprocess-Contract
  └─ CON-0014: /api/docs/{id}/analyze Endpoint-Contract (OpenAPI)
  └─ TST-0013: Integrations-Test für Analyze-Endpoint
  └─ sdd_web_api/analyzer.py  – subprocess-Wrapper + Prompt-Builder
  └─ Prompt-Templates in .sdd/templates/analysis/

Phase B: Web UI
  └─ Inline-Fragen-Panel im Spec/Contract-Editor
  └─ Session-Tracking (beantwortete Fragen)
  └─ Auto-Trigger (konfigurierbar)
```

## 8. Offene Fragen

- [ ] Soll der Analyze-Endpoint Streaming unterstützen (SSE) oder reicht ein einzelner Response?
- [x] Wie viele Fragen pro Analyse maximal? → **5** (implementiert in CON-0013 G-05 und CON-0014 INV-01)
- [ ] Prompt-Templates: versioniert im Blueprint oder nur lokal?
- [x] Auto-Trigger default on oder off? → **off** (implementiert; `sdd.analyzeOnSave: false`)

## 9. Änderungshistorie

| Datum      | Version | Autor   | Änderung                          |
|------------|---------|---------|-----------------------------------|
| 2026-05-12 | 0.1.0   | Boris   | Initiale Erstellung               |
| 2026-05-12 | 1.0.0   | Boris   | Vollständig implementiert (Phase A + B) |
| 2026-05-12 | 1.1.0   | Boris   | KI-Analyse-Nachfragen bearbeitet: Session-State-Modell präzisiert, Timeout dokumentiert, ID-Stabilitätseinschränkung festgehalten, US-02-Akzeptanzbedingung ergänzt, NFR um Sicherheit/Größenlimits/Timeout erweitert, §8 teilweise abgehakt |
