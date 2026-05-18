# SDD Framer

**Spec-Driven Development** — ein vollständiges, sprachneutrales System, das Traceability zwischen Feature-Specs, API-Contracts und Tests erzwingt. Kein Code ohne dokumentierte Anforderung.

```
Feature-Specs  →  Contracts  →  Tests  →  Code
    SPEC-XXXX       CON-XXXX    TST-XXXX
```

---

## Systembestandteile

### 1. SDD CLI (`tool/`)

Python-Paket `sdd-cli` — der Kern des Systems. Alle anderen Komponenten delegieren an die CLI.

- Dokumente anlegen (Spec, Contract, Test, ADR)
- Frontmatter und referenzielle Integrität validieren
- Traceability-Matrix erzeugen
- KI-gestützte Analyse, SOLID-Prüfung, Pattern-Vorschläge
- Lifecycle-Management (draft → approved → in-progress → implemented)
- Isolierte Docker-Entwicklungsumgebung pro Spec

### 2. Web API + Web UI (`web/`)

FastAPI-Backend (`web/api/`) mit eingebetteter React-SPA (`web/ui/`).

- Alle CLI-Befehle per HTTP aufrufbar
- WebSocket-Live-Logs für Pipeline-Runs
- KI-Analyse asynchron (Hintergrundqueue)
- Hub-Mechanismus: mehrere SDD-Projekte registrieren und verwalten

Erreichbar unter `http://localhost:8000` (API) und `http://localhost:8000` (SPA).

### 3. VS Code Extension (`vscode-extension/`)

Native VS Code-Integration:

- TreeView: alle Specs, Contracts, Tests auf einen Blick
- Validate on Save, CodeLens-Links
- Pipeline-Steuerung direkt aus der IDE
- KI-Analyse-Panel
- Web UI starten/stoppen/öffnen per Kommando

### 4. PWA — Mobile Remote Client (`web/pwa/`)

Progressive Web App für iOS und Android (installierbar, offline-fähig):

- Dashboard: Spec-Liste mit Status des aktiven Projekts
- Spec-Detail-Ansicht
- Multi-Projekt-Verwaltung mit QR-Code-Onboarding
- Token-Rotation für sichere Verbindung
- Zugriff über Tailscale oder lokales WLAN

---

## Installation

### Voraussetzungen

| Werkzeug | Minimalversion | Zweck |
|---|---|---|
| Python | 3.10 | CLI und Web API |
| Node.js | 18 | Web UI und VS Code Extension |
| uv | aktuell | Paketmanagement (empfohlen) |
| Docker | 24 | Isolierte Dev-Umgebungen (optional) |

### CLI installieren

```bash
# Empfohlen: uv
cd /pfad/zum/sdd-framer
uv sync

# Klassisch mit pip
cd tool
pip install -e ".[evaluate]"
```

Die Option `[evaluate]` installiert zusätzlich `anthropic` und `httpx` für KI-gestützte Features.  
Für lokale LLMs (LM Studio): `pip install -e ".[lm-studio]"`

Prüfen:

```bash
sdd --version
```

### Web API + Web UI starten

```bash
cd web

# Abhängigkeiten installieren (einmalig)
cd api && pip install -e . && cd ..
cd ui && npm install && npm run build && cd ..

# API starten (serviert gleichzeitig die SPA)
uvicorn main:app --reload --port 8000
```

Die SPA wird automatisch unter `http://localhost:8000` ausgeliefert.

### PWA bauen

```bash
cd web/pwa
npm install
npm run build   # → dist/ (statische Dateien)
```

Im Dev-Modus: `npm run dev` → `http://localhost:5173`

### VS Code Extension installieren

```bash
cd vscode-extension
npm install
# .vsix packen
npx vsce package
# In VS Code installieren
code --install-extension sdd-framer-*.vsix
```

Oder direkt im Dev-Modus: `F5` in VS Code öffnet eine Extension Development Host Instanz.

---

## Quick Setup — Neues Projekt

```bash
# 1. In das neue Projektverzeichnis wechseln
mkdir mein-projekt && cd mein-projekt

# 2. SDD-Struktur initialisieren
sdd init --name "Mein Projekt" --provider claude

# 3. Erste Spec anlegen
sdd new spec "User Login"

# 4. Contract zur Spec hinzufügen
sdd new contract --spec SPEC-0001 --format openapi --title "Login API"

# 5. Test zum Contract hinzufügen
sdd new test --spec SPEC-0001 --contract CON-0001 --level contract --title "OpenAPI Konformität"

# 6. Referenzen in der Spec eintragen (contracts, tests im Frontmatter)
$EDITOR .sdd/specs/SPEC-0001-*.md

# 7. Validierung
sdd validate

# 8. Traceability-Matrix erzeugen
sdd trace
```

> Für bestehende Projekte: `sdd upgrade` aktualisiert Schemas und Templates auf die aktuelle Version.

---

## SDD CLI — Alle Befehle

### `sdd init` — Projekt initialisieren

```bash
sdd init [--path <verzeichnis>] [--name <titel>] [--provider claude|lm-studio] [--force]
```

Erzeugt die vollständige SDD-Ordnerstruktur mit Schemas, Templates und `config.yaml`.

---

### `sdd upgrade` — Projekt aktualisieren

```bash
sdd upgrade [--path <verzeichnis>] [--verbose]
```

Synchronisiert Schemas und Templates mit der aktuellen Paketversion.

---

### `sdd new` — Dokumente anlegen

#### Spec

```bash
sdd new spec "<Titel>" [--owner <name>] [--type feature|bug-fix]
```

#### Contract

```bash
sdd new contract --spec SPEC-XXXX --format <format> --title "<Titel>"
```

Formate: `openapi`, `asyncapi`, `graphql`, `grpc`, `json-schema`, `avro`, `protobuf`, `gherkin`, `markdown`, `slo-yaml`

#### Test

```bash
sdd new test --spec SPEC-XXXX --contract CON-XXXX --level <level> --title "<Titel>"
```

Level: `contract`, `unit`, `integration`, `acceptance`, `performance`

#### ADR

```bash
sdd new adr "<Titel>"
```

#### Holdout-Szenario (KI-Evaluation)

```bash
sdd new holdout --spec SPEC-XXXX --contract CON-XXXX --title "<Titel>"
```

#### AGENTS.md

```bash
sdd new agents-md [--subdir <unterverzeichnis>] [--force]
```

#### GitHub-Workflow

```bash
sdd new github-workflow
```

---

### `sdd validate` — Konsistenz prüfen

```bash
sdd validate [--strict] [--instruct]
```

Prüft:
- Frontmatter-Konformität gegen JSON-Schemas
- Referenzielle Integrität (Spec → Contract → Test)
- Verwaiste Dokumente ohne Spec-Bezug

`--strict`: Warnungen als Fehler behandeln (für CI).  
`--instruct`: Gibt maschinenlesbare Hinweise für KI-Agenten aus.

---

### `sdd trace` — Traceability-Matrix

```bash
sdd trace
```

Generiert `docs/traceability.md` mit der vollständigen Spec↔Contract↔Test-Matrix.

---

### `sdd status` — Projekt-Übersicht

```bash
sdd status
```

Tabellarische Übersicht aller Specs mit Status, Contract- und Test-Coverage.

---

### `sdd status-check` — Content-Hash-Prüfung

```bash
sdd status-check [--fix]
```

Vergleicht Content-Hashes mit gespeichertem Stand und meldet veraltete Status.  
`--fix`: Aktualisiert Status automatisch.

---

### `sdd start` — TDD-Implementierungsphase

```bash
sdd start <SPEC-XXXX> [--auto] [--base-url <url>] [--build-cmd <cmd>] [--no-pr]
```

Setzt die Spec auf `in-progress`, erzeugt Test-Stubs und startet optional den vollautomatischen Implement-Zyklus.

---

### `sdd orchestrate` — Dark-Factory-Pipeline

```bash
sdd orchestrate --spec SPEC-XXXX [--base-url <url>] [--build-cmd <cmd>]
                [--max-retries 3] [--no-pr] [--dry-run] [--save/--no-save]
                [--project PRJ-XXXX] [--resume]
```

Vollautomatische Pipeline: Spec → Code → Tests → PR → Evaluation → Retry.

---

### `sdd evaluate` — Holdout-Evaluation

```bash
sdd evaluate --base-url <url> [--hol HOL-XXXX ...] [--save] [--json]
```

Führt KI-gestützte Holdout-Szenarien gegen einen laufenden Service aus.

---

### `sdd estimate` — Token-Kosten schätzen

```bash
sdd estimate [SPEC-XXXX] [--all] [--status <status>] [--model <modell>] [--json]
```

Schätzt Token-Kosten für Spec-Implementierung basierend auf Contracts und Tests.

---

### `sdd token-history` — Token-Verbrauch anzeigen

```bash
sdd token-history [SPEC-XXXX] [--export <datei.csv>]
```

---

### `sdd calibrate` — Kosten-Kalibrierung

```bash
sdd calibrate <SPEC-XXXX>
```

Markiert tatsächlichen Token-Verbrauch als Kalibrierungs-Datenpunkt.

---

### `sdd solid-check` — SOLID-Analyse

```bash
sdd solid-check <SPEC-XXXX|CON-XXXX> [--json]
```

KI-gestützte Prüfung der fünf SOLID-Prinzipien für eine Spec oder einen Contract.

---

### `sdd pattern-suggest` — Design-Pattern-Vorschläge

```bash
sdd pattern-suggest <SPEC-XXXX|CON-XXXX>
```

Schlägt passende Design Patterns (Refactoring Guru) für ein Artefakt vor.

---

### `sdd pattern` — Pattern-Register

```bash
sdd pattern accept <SPEC-XXXX> <pattern-name> --reason "<Begründung>" [--url <url>]
sdd pattern reject <SPEC-XXXX> <pattern-name> --reason "<Begründung>" [--url <url>]
sdd pattern list [SPEC-XXXX]
```

---

### `sdd review-contract` — Contract reviewen

```bash
sdd review-contract <CON-XXXX>
```

LLM-Review eines Contracts: Vollständigkeit, Testvorschlag.

---

### `sdd review-pending` — Alle pendenden Contracts reviewen

```bash
sdd review-pending [--auto]
```

Listet und reviewed alle Contracts im Status `review` ohne zugehörigen Test.

---

### `sdd conflict` — Konflikte verwalten

```bash
sdd conflict list <SPEC-XXXX>
sdd conflict resolve <SPEC-XXXX> <CF-ID> --action "<Beschreibung>"
sdd conflict acknowledge <SPEC-XXXX> <CF-ID> --reason "<Begründung>"
```

---

### `sdd mark-false-positive` — False Positive markieren

```bash
sdd mark-false-positive <SPEC-XXXX>
```

---

### `sdd install-hooks` — Git-Hooks installieren

```bash
sdd install-hooks
```

Installiert einen `pre-commit`-Hook, der `sdd status-check --fix` vor jedem Commit ausführt.

---

### `sdd obsidian` — Obsidian-Vault-Synchronisation

```bash
sdd obsidian export [--vault <pfad>] [--dry-run]
sdd obsidian import [--vault <pfad>]
sdd obsidian watch  [--vault <pfad>] [--interval <sekunden>]
```

Exportiert alle SDD-Artefakte als Obsidian-kompatible Markdown-Dateien und importiert Änderungen zurück.

---

### `sdd dev` — Isolierte Docker-Entwicklungsumgebung

```bash
sdd dev start <SPEC-XXXX>           # Container + Git-Branch starten
sdd dev exec  <SPEC-XXXX> <cmd...>  # Befehl im Container ausführen
sdd dev close <SPEC-XXXX> [--delete-branch]  # Container stoppen
sdd dev pr    <SPEC-XXXX>           # Lokalen PR erstellen
sdd dev build                        # Docker-Image bauen
sdd dev push                         # Image in Registry pushen
sdd dev up    <SPEC-XXXX>            # Compose-Stack starten
sdd dev down  <SPEC-XXXX>            # Compose-Stack stoppen
```

---

## Web API — Endpunkte

Die API ist unter `http://localhost:8000/api/...` erreichbar. Interaktive Dokumentation: `http://localhost:8000/docs`

### Status & Konfiguration

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/api/status` | Projektübersicht |
| `GET` | `/api/config` | `config.yaml` lesen |
| `PUT` | `/api/config` | `config.yaml` schreiben |
| `PATCH` | `/api/config` | Einzelne Felder aktualisieren |
| `GET` | `/api/formats` | Verfügbare Contract-Formate |
| `GET` | `/api/maintenance` | Maintenance-Sweep |
| `POST` | `/api/open` | Datei im Editor öffnen |

### Specs

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/api/specs` | Alle Specs auflisten |
| `GET` | `/api/specs/{spec_id}` | Eine Spec abrufen |
| `POST` | `/api/specs` | Neue Spec anlegen |
| `PUT` | `/api/specs/{spec_id}` | Spec-Body aktualisieren |

### Contracts

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/api/contracts` | Alle Contracts auflisten |
| `GET` | `/api/contracts/{contract_id}` | Einen Contract abrufen |
| `POST` | `/api/contracts` | Neuen Contract anlegen |

### Validierung & Traceability

| Methode | Pfad | Beschreibung |
|---|---|---|
| `POST` | `/api/validate` | `sdd validate` ausführen |
| `POST` | `/api/trace` | Traceability-Matrix aktualisieren |

### Gate — Execution Gate

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/api/gate/{spec_id}/status` | Gate-Status abrufen |
| `POST` | `/api/gate/{spec_id}/spec-review` | Spec-Review starten |
| `POST` | `/api/gate/{spec_id}/contract-propose` | Contract vorschlagen |
| `POST` | `/api/gate/{spec_id}/contract-review` | Contract reviewen |
| `POST` | `/api/gate/{spec_id}/test-generate` | Tests generieren |
| `POST` | `/api/gate/{spec_id}/approve` | Gate freigeben |
| `GET` | `/api/gate/{spec_id}/conflicts` | Konflikte auflisten |
| `PATCH` | `/api/gate/{spec_id}/conflicts/{cf_id}` | Konflikt aktualisieren |

### Pipeline / Orchestrierung

| Methode | Pfad | Beschreibung |
|---|---|---|
| `POST` | `/api/orchestrate` | Pipeline starten |
| `GET` | `/api/pipeline/active` | Aktiver Lauf für eine Spec |
| `POST` | `/api/pipeline/{run_id}/abort` | Pipeline abbrechen |
| `GET` | `/api/pipeline/{run_id}/log` | Live-Log (SSE-Stream) |
| `GET` | `/api/pipeline/{run_id}` | Pipeline-Status |

### KI-Analyse

| Methode | Pfad | Beschreibung |
|---|---|---|
| `PUT` | `/api/{doc_id}/analyze` | Synchrone KI-Analyse |
| `POST` | `/api/{doc_id}/analyze/start` | Asynchrone Analyse starten |
| `GET` | `/api/{doc_id}/analyze/status/{job_id}` | Analyse-Job-Status |
| `GET` | `/api/{doc_id}/analyses` | Alle Analyse-Ergebnisse |
| `GET` | `/api/{doc_id}/analyses/{result_id}` | Ein Ergebnis abrufen |
| `PATCH` | `/api/{doc_id}/analyses/{result_id}/dismiss` | Ergebnis verwerfen |
| `POST` | `/api/generate-spec` | Spec KI-generieren |
| `POST` | `/api/improve-spec` | Spec verbessern |
| `POST` | `/api/suggest-contracts` | Contracts vorschlagen |
| `GET` | `/api/usage` | Token-Verbrauch abrufen |

### Hub — Multi-Projekt-Verwaltung

| Methode | Pfad | Beschreibung |
|---|---|---|
| `POST` | `/api/hub/register` | Projekt registrieren |
| `POST` | `/api/hub/deregister` | Projekt abmelden |
| `GET` | `/api/hub/projects` | Alle registrierten Projekte |

### Remote Control (SPEC-0023)

| Methode | Pfad | Beschreibung |
|---|---|---|
| `POST` | `/api/sdd/run` | SDD-Befehl remote ausführen |
| `POST` | `/api/push/subscribe` | Push-Notification abonnieren |

### Auth (SPEC-0025)

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/api/server-info` | Server-Informationen |
| `GET` | `/api/auth/qr-payload` | QR-Code-Payload für PWA-Onboarding |
| `POST` | `/api/auth/generate-token` | Neues Auth-Token generieren |
| `POST` | `/api/auth/rotate-token` | Auth-Token rotieren |

---

## VS Code Extension — Befehle

Alle Befehle sind über die Command Palette (`Ctrl+Shift+P`) erreichbar:

| Befehl | Titel |
|---|---|
| `sdd.newSpec` | SDD: New Spec |
| `sdd.newContract` | SDD: New Contract |
| `sdd.newTest` | SDD: New Test |
| `sdd.newAdr` | SDD: New ADR |
| `sdd.validate` | SDD: Validate |
| `sdd.updateTrace` | SDD: Update Trace Matrix |
| `sdd.refresh` | SDD: Refresh Tree |
| `sdd.analyzeDoc` | SDD: KI-Analyse starten |
| `sdd.analyzeReset` | SDD: Analyse-Session zurücksetzen |
| `sdd.startWebUI` | SDD: Start Web UI |
| `sdd.stopWebUI` | SDD: Stop Web UI |
| `sdd.restartWebUI` | SDD: Restart Web UI |
| `sdd.openWebUI` | SDD: Open Web UI |
| `sdd.executeSpec` | SDD: Execute Spec |
| `sdd.executeCurrentSpec` | SDD: Execute Current Spec |
| `sdd.abortPipeline` | SDD: Abort Pipeline |
| `sdd.reviewContract` | SDD: Review Contract |
| `sdd.reviewPending` | SDD: Review Pending Contracts |
| `sdd.estimateCurrentSpec` | SDD: Estimate Current Spec |
| `sdd.statusCheck` | SDD: Status Check |
| `sdd.obsidianExport` | SDD: Obsidian Export |
| `sdd.obsidianImport` | SDD: Obsidian Import |
| `sdd.showOutput` | SDD: Show Output |

### Extension-Einstellungen (`settings.json`)

```json
{
  "sdd.webApiUrl": "http://localhost:8000",
  "sdd.pythonPath": "python",
  "sdd.cliPath": "",
  "sdd.validateOnSave": true,
  "sdd.showCodeLens": true,
  "sdd.analyzeOnSave": false,
  "sdd.treeViewRefreshInterval": 0,
  "sdd.webUi.port": 0,
  "sdd.webUi.externalUrl": "",
  "sdd.webUi.autoStart": false,
  "sdd.webUi.openBrowser": true,
  "sdd.pipeline.pollInterval": 5000
}
```

---

## PWA — Mobile Client

### Onboarding per QR-Code

1. Web API starten
2. Im Browser: `http://localhost:8000/api/auth/qr-payload` → QR-Code anzeigen
3. PWA öffnen → "Projekt hinzufügen" → QR-Code scannen
4. Verbindung wird automatisch konfiguriert (URL + Token)

### Token-Rotation

```bash
# Neues Token generieren
curl -X POST http://localhost:8000/api/auth/rotate-token \
  -H "Authorization: Bearer <aktuelles-token>"
```

Das neue Token wird automatisch in der PWA aktualisiert.

---

## Claude Skills (`/sdd-*`)

Im Projekt sind Claude Code Skills integriert, die über die Command Palette aufrufbar sind:

| Skill | Beschreibung |
|---|---|
| `/sdd` | Projektübersicht: alle Specs, Status, offene Punkte |
| `/sdd-new` | Interaktiv Spec, Contract, Test oder ADR erstellen |
| `/sdd-validate` | Validierung ausführen und Fehler erklären |
| `/sdd-review` | SOLID-Analyse + Design-Pattern-Vorschläge |
| `/sdd-status` | Lifecycle-Status und Blockaden anzeigen |
| `/sdd-implement` | TDD-Implementierungsphase starten |

---

## Garantierte Invarianten

`sdd validate` erzwingt folgende Regeln — im CI-Einsatz mit `--strict` blockiert es jeden Merge:

1. Jede Spec referenziert mindestens einen Contract.
2. Jeder Contract referenziert mindestens einen Test.
3. Alle Referenzen (Spec ↔ Contract ↔ Test) zeigen auf existierende Dokumente.
4. Frontmatter aller Dokumente entspricht den JSON-Schemas.
5. Keine verwaisten Contracts oder Tests ohne Spec-Bezug.

---

## Projektstruktur

```
.sdd/
  config.yaml          # Projektkonfiguration
  schemas/             # JSON-Schemas für Frontmatter-Validierung
  specs/               # SPEC-XXXX-*.md
  contracts/
    api/               # CON-XXXX – OpenAPI, AsyncAPI, GraphQL, gRPC
    behavior/          # CON-XXXX – Gherkin, Markdown
    performance/       # CON-XXXX – SLO-YAML
  pipeline/            # Gate-Status pro Spec
  patterns/            # Pattern-Register

docs/
  adr/                 # ADR-XXXX – Architecture Decision Records
  traceability.md      # Generiert von `sdd trace`

tests/
  unit/
  contract/
  acceptance/
  performance/

tool/
  sdd_cli/             # Python-Paket – CLI-Kern

web/
  api/                 # FastAPI – Web API
  ui/                  # React – Web UI (SPA)
  pwa/                 # React – Progressive Web App

vscode-extension/      # VS Code Extension (TypeScript)
```

---

## CI-Integration

```yaml
# .github/workflows/sdd.yml (generiert von `sdd new github-workflow`)
- name: SDD Validate
  run: sdd validate --strict
```

---

## Lizenz

MIT
