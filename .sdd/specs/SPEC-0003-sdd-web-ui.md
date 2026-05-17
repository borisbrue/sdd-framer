---
id: SPEC-0003
title: "SDD Web UI"
status: implemented
project: PRJ-0001
owner: "Boris"
created: 2026-05-11
updated: 2026-05-12
version: 0.3.0
priority: high
tags: [tooling, web, developer-experience, fastapi, react]
depends_on: []
contracts: [CON-0007, CON-0008]
tests: [TST-0008, TST-0009]
adrs: []
---

# SDD Web UI

> **Status:** implemented · **Owner:** Boris · **Version:** 0.3.0

## 1. Zielsetzung

Browser-UI für geführtes Erstellen und Verwalten von Specs, Contracts und Tests.
Läuft lokal als FastAPI-Server (`web/api/`), serviert eine React-SPA (`web/ui/`)
und bindet die `sdd`-CLI als Python-Bibliothek ein.

**Kern-Wertversprechen:** Entwickler öffnen `http://localhost:8000` und können
ohne CLI-Kenntnisse Specs anlegen, AI-Fragen beantworten, Contracts generieren
und die Traceability-Matrix einsehen.

## 2. Features

### 2.1 REST-API (FastAPI, `web/api/`)

| Route-Gruppe | Prefix   | Endpunkte                                                  |
|--------------|----------|------------------------------------------------------------|
| Projects     | /api     | `GET /projects`, `GET /projects/{id}`, `POST /projects`, `PATCH /projects/{id}/level` |
| Specs        | /api     | `GET /specs`, `GET /specs/{id}`, `POST /specs`             |
| Contracts    | /api     | `GET /contracts`, `GET /contracts/{id}`, `POST /contracts` |
| Tests        | /api     | `GET /tests`, `GET /tests/{id}`, `POST /tests`             |
| Commands     | /api     | `GET /status`, `POST /validate`, `POST /trace`, `GET /formats`, `POST /open`, `GET /maintenance` |
| AI           | /api/ai  | `POST /ai/generate-spec`, `POST /ai/improve-spec`, `POST /ai/suggest-contracts`, `GET /ai/usage` |
| Copilot      | /api/copilot | `POST /copilot/generate-spec`, `POST /copilot/improve-spec`, `POST /copilot/suggest-contracts` |
| Analyze      | /api/docs | `PUT /docs/{doc_id}/analyze`                               |

Vollständiges Schema: CON-0007 (`contracts/api/web-api.openapi.yaml`).

### 2.2 React SPA (`web/ui/src/`)

**Layout:** 2-Spalten (Sidebar + Main). Persistente StatusBar oben.

**Sidebar:**
- Projektliste mit geklappter Spec-Liste pro Projekt
- `+ Projekt` / `+ Spec` Schnellzugriff
- Autonomy-Level-Badge pro Projekt (z.B. „Level 3 – AI-reviewed")

**Main (Detail-Ansichten):**
- `SpecDetail` — Frontmatter, Markdown-Body, verknüpfte Contracts und Tests, AI-Analyse-Panel
- `ContractDetail` — Frontmatter, Markdown-Body, Artifact-Inhalt (OpenAPI YAML etc.)
- `TestDetail` — Frontmatter, Markdown-Body

**Formulare:**
- `SpecForm` — Titel, Owner, Priority, Projekt-Zuordnung
- `ProjectForm` — Name, Owner, Status, Beschreibung
- `ContractForm` — Spec-Zuordnung, Format-Auswahl
- `TestForm` — Spec + Contract Zuordnung, Level-Auswahl

**Panels:**
- `AnalyzePanel` — KI-Fragebogen pro Spec/Contract (via `/api/docs/{id}/analyze`)
- `AiPanel` — Spec generieren, verbessern, Contracts vorschlagen
- `AiUsageView` — Kosten-Dashboard (Token, USD, Operationen)
- `SettingsPage` — Dark/Light-Theme-Umschalter

**Navigation:** Breadcrumb mit History (Zurück-Schaltfläche), Hash-freies Routing.

### 2.3 AI-Integration

Der AI-Layer läuft **ohne eigenen API-Key** — er delegiert an `claude` (Claude Code CLI)
via Subprocess (identisch zu `web/api/analyzer.py`). Kein separater LLM-Dienst nötig.

Operationen:
- **generate-spec** — erzeugt vollständige Spec aus Titel + Kontext
- **improve-spec** — verbessert bestehende Spec nach Freitext-Anweisung
- **suggest-contracts** — schlägt Contract-Typen für eine Spec vor
- **analyze** — stellt Klärungsfragen zu einer Spec/Contract (strukturiertes Q&A)

### 2.4 Validierung & Traceability

- `POST /api/validate` — führt `sdd validate` aus; Response enthält `errors`, `warnings`,
  und `instruction` (maschinenlesbare Korrekturanweisung für Agenten)
- `POST /api/trace` — aktualisiert `docs/traceability.md`
- `GET /api/maintenance` — führt Drift-Sweep aus (veraltete Specs, fehlende Contracts/Tests)

### 2.5 Dark Factory Integration (SPEC-0004)

- `GET /api/projects` gibt `autonomy_level` (1|2|3|3.5|4) zurück
- `PATCH /api/projects/{id}/level` — setzt Autonomy Level via Web
- Sidebar zeigt Autonomy-Level-Badge pro Projekt

## 3. Architektur

```
web/
├── api/
│   ├── main.py            # FastAPI-App, CORS, Static-File-Serving
│   ├── sdd_context.py     # Lazy-init von SddConfig, ENV SDD_PROJECT_ROOT
│   ├── analyzer.py        # Claude CLI Subprocess + Session-Verwaltung
│   ├── usage_store.py     # SQLite-basiertes Kosten-Tracking
│   └── routes/
│       ├── specs.py       # CRUD Specs
│       ├── contracts.py   # CRUD Contracts
│       ├── tests.py       # CRUD Tests
│       ├── projects.py    # CRUD Projects + set-level
│       ├── commands.py    # validate, trace, status, open, maintenance
│       ├── ai.py          # KI-Operationen (claude CLI)
│       ├── copilot.py     # Copilot-Variante der KI-Operationen
│       └── analyze.py     # Interaktive Dokumenten-Analyse
└── ui/
    ├── src/
    │   ├── api.ts         # Typesafe REST-Client
    │   ├── App.tsx        # Root-Komponente, State-Management
    │   ├── components/    # React-Komponenten (s. 2.2)
    │   └── hooks/
    │       └── useTheme.ts
    └── dist/              # Build-Artefakt (npm run build)
```

**Start-Befehl:**
```bash
cd web/api && python main.py --project /path/to/sdd-project --port 8000
```

**Konfiguration:**
- `SDD_PROJECT_ROOT` (ENV) — Pfad zum SDD-Projekt
- `--port` (Argument) — HTTP-Port (Default: 8000)
- CORS: `http://localhost:5173` (Vite Dev Server) + `http://localhost:8000`

## 4. Nicht-Ziele

- Kein Multi-User / kein Auth — lokales Single-User-Tool
- Kein eigener LLM-API-Key — nutzt Claude Code CLI-Session
- Keine Echtzeit-Kollaboration (kein WebSocket)
- Kein persistentes Backend-State — liest/schreibt immer aus dem Dateisystem

## 5. User Stories

| ID    | Als ...     | möchte ich ...                                    | um ...                                         |
|-------|-------------|---------------------------------------------------|------------------------------------------------|
| US-01 | Entwickler  | Specs im Browser anlegen und bearbeiten            | ohne CLI-Wissen produktiv zu sein              |
| US-02 | Entwickler  | KI-Fragen zu meiner Spec beantworten               | eine vollständige Spec zu erhalten             |
| US-03 | Tech Lead   | die Traceability-Matrix auf Knopfdruck erzeugen    | Lücken zwischen Spec/Contract/Test zu sehen    |
| US-04 | Entwickler  | das Autonomy Level im Browser setzen               | den Dark-Factory-Reifegrad anzupassen          |
| US-05 | Tech Lead   | den Maintenance-Sweep im Browser auslösen          | veraltete Specs und Drift-Probleme zu erkennen |

## 6. Änderungshistorie

| Datum      | Version | Autor   | Änderung                                                    |
|------------|---------|---------|-------------------------------------------------------------|
| 2026-05-11 | 0.1.0   | Boris   | Initialer Entwurf                                           |
| 2026-05-11 | 0.2.0   | Boris   | Implementiert: FastAPI + React SPA + AI-Integration         |
| 2026-05-12 | 0.3.0   | Boris   | Refaktor: vollständige Dokumentation, SPEC-0004-Integration |
