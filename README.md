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
- **LLM Task Distribution Engine**: Spec → Tasks → parallele LLM-Ausführung → PR

### 2. Web API + Web UI (`web/`)

FastAPI-Backend (`tool/sdd_cli/web/api/`) mit eingebetteter React-SPA (`web/ui/`).

- Alle CLI-Befehle per HTTP aufrufbar
- WebSocket-Live-Logs für Pipeline-Runs
- KI-Analyse asynchron (Hintergrundqueue)
- Projekt-Hub: laufende SDD-Projekt-Server registrieren und im Dashboard anzeigen

Erreichbar unter `http://localhost:8000` (API + SPA).

### 5. Hub-Daemon (`tool/sdd_cli/hub/`)

Systemd-User-Service für dauerhaften Multi-Projekt-Betrieb (Port **4711**):

- File-basierte Projekt-Registry (`~/.config/sdd/hub-registry.yaml`)
- Projektserver per Klick starten und stoppen (ohne Terminal)
- SSE-Stream für Live-Statusupdates
- WebUI unter `/hub/` — zeigt alle registrierten Projekte mit Status-Badges
- Manueller Start (`sdd hub start`) und systemd-Daemon (`sdd hub install`) nutzen **dieselbe** Implementierung

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
| Docker **oder Podman** | 24 / aktuell | Isolierte Dev-Umgebungen (optional) |

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
#    Legt zusätzlich einen Test-Stub an – Level passend zum Contract-Typ
#    (api → contract, data → unit, behavior → acceptance, performance → performance).
sdd new contract --spec SPEC-0001 --format openapi --title "Login API"

# 5. Optional: weitere Tests zum Contract, wenn ein Stub nicht reicht
#    (der aus Schritt 4 existiert bereits – nicht doppelt anlegen)
sdd new test --spec SPEC-0001 --contract CON-0001 --level acceptance --title "Login-Ablauf"

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

> ### Migration: umbenannte und entfernte Befehle
>
> SPEC-0044 hat die CLI auf das Schema `sdd <noun> <verb>` vereinheitlicht. Die alten
> Namen sind als Stubs erhalten und verweisen beim Aufruf auf ihren Nachfolger.
>
> | Alt | Neu |
> |---|---|
> | `sdd evaluate` | `sdd holdout run` |
> | `sdd generate-holdouts` | `sdd holdout generate` |
> | `sdd solid-check` | `sdd spec solid` |
> | `sdd regression-check` | `sdd spec regression` |
> | `sdd review-contract` | `sdd review contract` |
> | `sdd review-pending` | `sdd review pending` |
> | `sdd test-run` | `sdd test run` |
> | `sdd test-results` | `sdd test results` |
> | `sdd mark-false-positive` | `sdd autonomy false-positive` |
> | `sdd level` | `sdd autonomy level` |
> | `sdd set-level` | `sdd autonomy set-level` |
> | `sdd contract review` | `sdd contract analyze` |
>
> **Ersatzlos entfallen:**
>
> | Entfernt | Grund |
> |---|---|
> | `sdd dev` (start/exec/close/pr/build/push/up/down) | Container-Lifecycle wird von `sdd start`, `sdd finalize` und `sdd orchestrate` intern verwaltet |
> | `sdd pattern`, `sdd pattern-suggest` | Pattern-Entscheidungen stehen in der Spec unter „Architektur & Design Patterns" |
> | `sdd status-check` | läuft automatisch im pre-commit-Hook (`sdd install-hooks`) |
> | `sdd new agents-md` | `sdd init` legt die `AGENTS.md` an |
> | `sdd new github-workflow` | Vorlage unter `.sdd/templates/github-actions/` |
> | `sdd implement` | ausschließlich als Skill `/sdd-implement` |


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

> `sdd new contract` legt bereits einen Test-Stub mit passendem Level an.
> Dieser Befehl ist für **zusätzliche** Tests gedacht – wer ihn direkt nach
> `sdd new contract` aufruft, erhält zwei Test-Dokumente für denselben Contract.

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

Kein eigener Befehl mehr: `sdd init` legt die `AGENTS.md` im Projekt-Root an.
Der Aufruf ist idempotent — eine bestehende Datei bleibt unangetastet, `--force`
überschreibt sie.

```bash
sdd init --name "<Titel>"     # legt AGENTS.md mit an, falls sie fehlt
```

#### GitHub-Workflow

Kein eigener Befehl — `sdd new github-workflow` wurde mit SPEC-0044 entfernt.
Die Vorlage liegt nach `sdd init` unter `.sdd/templates/github-actions/sdd-orchestrate.yml`
und wird bei Bedarf von Hand kopiert:

```bash
mkdir -p .github/workflows
cp .sdd/templates/github-actions/sdd-orchestrate.yml .github/workflows/
```

> Der Workflow startet `sdd orchestrate` bei jedem Push auf `main` mit geänderten
> Spec-Dateien und benötigt dafür einen `ANTHROPIC_API_KEY` als GitHub-Secret.
> SPEC-0044 FR-06 sieht vor, dass `sdd init` ihn nach Rückfrage selbst anlegt —
> das ist noch nicht umgesetzt.

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

### `sdd pipeline` — Rollen-Pipeline mit Supervisor

```bash
sdd pipeline run SPEC-XXXX [--dry-run] [--resume <run_id>] [--max-tasks N]
sdd pipeline decide <run_id> --json '{"point": "S1", "command": "approve", "reason": "…"}'
sdd pipeline status <run_id>
sdd pipeline report <run_id>
```

Rollen (`decomposer`, `test_author`, `implementer`, `reviewer`) arbeiten über die Modelle aus
`llm.roles.<rolle>` in `.sdd/config.yaml`; die Rollen selbst stehen in `.sdd/roles/<rolle>.md`.
Der Supervisor entscheidet nur an S1 (Zerlegung), S2 (Eskalation) und S3 (Abnahme):
`llm.roles.supervisor.mode: inline` (Supervisor-Modell antwortet sofort) oder `session`
(der Run hält mit Exit 3 an; Claude Code entscheidet im Dialog über `/sdd-supervise`).
Schreibrechte regelt die PathPolicy: nur `test_author` (Testdatei) und `implementer`
(`allowed_paths` des Tasks). Protokoll und Zustand liegen unter `.sdd/runs/<SPEC>/<run_id>/`.

```yaml
llm:
  profiles:                                   # benannte Modelle (SPEC-0061)
    lokal: {provider: openai-compat, base_url: http://localhost:8080/v1, model: qwen3-coder}
    denker: {provider: openai-compat, base_url: http://localhost:8080/v1, model: qwen3-thinking}
  roles:
    decomposer:  {profile: denker}
    implementer: {by_complexity: {low: lokal, medium: lokal, high: session}}
    reviewer:    {provider: claude-cli}
    supervisor:  {provider: claude-cli, mode: session}
pipeline:
  task_gates: [tests, architecture]           # Gates nach jedem Implementer-Versuch
  auto_steps: [holdout, finalize, automerge]  # Abschluss-Kette für --auto
```

Weitere Möglichkeiten (SPEC-0061):

- **Arbeit im Dialog:** Jede Arbeitsrolle kann `mode: session` sein (oder per `by_complexity`
  einzelne Stufen). Der Run hält mit Exit 3 und einem Auftrag in `pending-work.json` an; Claude Code
  schreibt die Dateien und bestätigt mit `sdd pipeline done <run_id>` (`--json` für `decomposer`
  und `reviewer`). Es gelten dieselben PathPolicy, Gates und Eskalationen wie bei Modellen.
- **Einzelner Task:** `sdd pipeline run SPEC --task T02` bearbeitet einen Task der gespeicherten
  Zerlegung.
- **Autonom bis zum Merge:** `sdd pipeline run SPEC --auto` – das Holdout-Ergebnis erscheint in der
  S3-Anfrage (der Supervisor kann Tasks mit `reopen` erneut öffnen), danach PR und Auto-Merge nach
  Autonomie-Level.
- **Modelle prüfen:** `sdd config test-llm [--role R | --profile P]`.

---

### `sdd holdout run` — Holdout-Evaluation

```bash
sdd holdout run --base-url <url> [--hol HOL-XXXX ...] [--save] [--json]
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

### `sdd spec solid` — SOLID-Analyse

```bash
sdd spec solid <SPEC-XXXX|CON-XXXX> [--json]
```

KI-gestützte Prüfung der fünf SOLID-Prinzipien für eine Spec oder einen Contract.

---

### `sdd review contract` — Contract reviewen

```bash
sdd review contract <CON-XXXX>
```

LLM-Review eines Contracts: Vollständigkeit, Testvorschlag.

---

### `sdd review pending` — Alle pendenden Contracts reviewen

```bash
sdd review pending [--auto]
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

### `sdd autonomy false-positive` — False Positive markieren

```bash
sdd autonomy false-positive <SPEC-XXXX>
```

---

### `sdd install-hooks` — Git-Hooks installieren

```bash
sdd install-hooks
```

Installiert einen `pre-commit`-Hook. Vor jedem Commit laufen dann:

1. **Status-Check** — inhaltlich geänderte Specs und Contracts fallen von
   `approved`/`implemented` zurück auf `review`. Sind die Dateien Teil des Commits,
   wird der Statuswechsel mit eingecheckt. Schlägt der Check fehl, meldet er sich,
   blockiert den Commit aber nicht.
2. **Regressions-Gate** — betrifft der Commit `main.py`, `routes/*.py` oder `App.tsx`,
   werden die Tests der betroffenen Specs ausgeführt und der Commit bei roten Tests
   abgebrochen.

Es gibt kein eigenes `sdd status-check`-Kommando mehr (entfernt mit SPEC-0044); die
Prüfung läuft ausschließlich über diesen Hook.

---

### `sdd obsidian` — Obsidian-Vault-Synchronisation

```bash
sdd obsidian export [--vault <pfad>] [--dry-run]
sdd obsidian import [--vault <pfad>]
sdd obsidian watch  [--vault <pfad>] [--interval <sekunden>]
```

Exportiert alle SDD-Artefakte als Obsidian-kompatible Markdown-Dateien und importiert Änderungen zurück.

---

### `sdd decompose` — Spec in Tasks zerlegen

```bash
sdd decompose <SPEC-XXXX> [--yes]
```

Analysiert eine Spec via LLM und zerlegt sie in atomare, klassifizierte Tasks:

- **Komplexität:** `low` / `medium` / `high`
- **Kontextgröße:** `S` / `M` / `L`
- **Typ:** `code` / `test` / `config` / `doc`

Der Entwickler bestätigt die Task-Liste interaktiv vor der Ausführung. Ergebnis wird in `.sdd/tasks/SPEC-XXXX.json` gespeichert.

---

### `sdd distribute` — entfernt

`sdd distribute` wurde mit SPEC-0058 entfernt (es erzeugte keinen Code; der `llm_pool` aus der
Config wurde nie gelesen). Der Befehl verweist nur noch auf den Ersatz und endet mit Exit 1.
Tasks setzt die Rollen-Pipeline um: [`sdd pipeline run`](#sdd-pipeline--rollen-pipeline-mit-supervisor),
Modelle je Rolle stehen in `llm.roles`. Alte `llm_pool`-Blöcke kommentiert `sdd upgrade` aus.

---

### `sdd task-status` — Fortschritt anzeigen

```bash
sdd task-status <SPEC-XXXX>
```

Zeigt den aktuellen Status aller Tasks einer laufenden Distribution:

```
Tasks für SPEC-0026 (8):
  committed   Implementiere TaskLifecycle State Machine
  committed   Erstelle LLM-Pool-Registry
  running     ReviewPipeline Chain of Responsibility
  retrying    sdd decompose CLI-Command (retry 1)
  blocked     Container-Netzwerk-Isolation
  pending     PR-Workflow End-to-End
```

---

### `sdd hub` — Multi-Projekt-Hub verwalten

Der Hub-Daemon läuft auf Port **4711** und verwaltet mehrere Projektserver zentral.

#### `sdd hub start` — Manueller Start (Vordergrund)

```bash
sdd hub start [--port INTEGER] [--no-browser]
```

Startet den Hub im laufenden Terminal. Blockiert bis Strg+C. Warnt wenn Port bereits belegt.
Öffnet automatisch die WebUI im Browser (deaktivierbar mit `--no-browser`).

#### `sdd hub install` — systemd-Daemon installieren

```bash
sdd hub install
```

Installiert und aktiviert `sdd-hub.service` als systemd-User-Service.
Der Hub startet dann automatisch beim Systemboot — kein Terminal nötig.

#### `sdd hub register` — Projekt registrieren

```bash
sdd hub register --name <name> --path <pfad> --cmd <befehl...> --port <port> [--force]
```

Trägt ein Projekt in die Hub-Registry ein (`~/.config/sdd/hub-registry.yaml`).
`--cmd` kann mehrfach angegeben werden (z.B. `--cmd uv --cmd run --cmd sdd --cmd ui`).

#### `sdd hub status` — Registry-Übersicht

```bash
sdd hub status
```

Zeigt alle registrierten Projekte mit aktuellem Status und PID in einer Tabelle.

**Hub-API-Endpunkte** (alle unter `http://localhost:4711`):

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/hub/projects` | Alle registrierten Projekte (JSON) |
| `POST` | `/hub/projects/{id}/start` | Projektprozess starten |
| `POST` | `/hub/projects/{id}/stop` | Projektprozess stoppen |
| `GET` | `/hub/projects/stream` | Live-Statusupdates (SSE) |
| `GET` | `/hub/` | WebUI (HTML-Dashboard) |

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

### Hub — Projekt-Dashboard (Auto-Register, Port 8000)

Projektserver melden sich automatisch an wenn `sdd ui` gestartet wird.

| Methode | Pfad | Beschreibung |
|---|---|---|
| `POST` | `/api/hub/register` | Projekt-Server anmelden |
| `POST` | `/api/hub/deregister` | Projekt-Server abmelden |
| `GET` | `/api/hub/projects` | Alle registrierten Server |
| `GET` | `/hub` | Browser-Dashboard (HTML) |

> Für dauerhaften Multi-Projekt-Betrieb mit Start/Stop-Steuerung: `sdd hub install` (Port 4711).

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
| `/sdd-holdout SPEC-XXXX` | Holdout-Szenarien aus Spec + Contracts generieren (isolierter Kontext, kein Sourcecode) |
| `/sdd-implement SPEC-XXXX` | TDD-Implementierungsphase im Container starten |
| `/sdd-config` | `config.yaml` interaktiv bearbeiten |

**Empfohlener Workflow:**

```
/sdd-new spec          → Spec erstellen
/sdd-new contract      → Contracts definieren
/sdd-new test          → Test-Stubs anlegen
/sdd-holdout SPEC-XXXX → Holdout-Szenarien generieren (vor sdd start!)
sdd start SPEC-XXXX    → Container starten, Implementierung beginnen
/sdd-implement SPEC-XXXX → TDD → finalize → evaluate (alles im Container)
```

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

docs/ adr/                 # ADR-XXXX – Architecture Decision Records
  traceability.md      # Generiert von `sdd trace`

tests/
  unit/
  contract/
  acceptance/
  performance/

tool/
  sdd_cli/             # Python-Paket – CLI-Kern
    hub/               # Hub-Daemon (SPEC-0038/0039, Port 4711)
      app.py           # FastAPI-App (create_app Factory)
      registry.py      # File-basierte Projekt-Registry
      process_manager.py # Prozess-Start/Stop + Crash-Detection
      events.py        # SSE-EventBus
      models.py        # ProjectEntry Pydantic-Model
      config.py        # HubConfig (Default-Port 4711)
      routes/          # FastAPI-Router
      templates/       # HTML-Dashboard + systemd-Unit-Template
    task_model.py      # Task Dataclass + Enums (SPEC-0026)
    task_lifecycle.py  # State Machine – Zustandsübergänge
    decompose.py       # TaskDecomposer über die Rolle decomposer
    pipeline/          # Rollen-Pipeline (SPEC-0053): Rollen, PathPolicy, Runner, Mediator, Monitor

web/
  api/                 # FastAPI – Web API
  ui/                  # React – Web UI (SPA)
  pwa/                 # React – Progressive Web App

vscode-extension/      # VS Code Extension (TypeScript)
```

---

## Troubleshooting

### Podman in VS Code Flatpak (SteamOS / Linux mit Flatpak)

VS Code aus dem Flatpak-Store läuft in einem isolierten Namespace und kann Host-Binaries nicht direkt aufrufen. Wenn `sdd start` oder `sdd finalize` fehlschlägt mit:

```
FileNotFoundError: [Errno 2] No such file or directory: 'podman'
```

oder Podman startet, wirft aber Shared-Library-Fehler (`libsubid.so.5 not found`):

**Lösung:** Wrapper-Script anlegen, das `flatpak-spawn --host` nutzt.

```bash
mkdir -p ~/.local/bin
cat > ~/.local/bin/podman << 'EOF'
#!/bin/bash
flatpak-spawn --host podman "$@"
EOF
chmod +x ~/.local/bin/podman
```

Sicherstellen, dass `~/.local/bin` in `$PATH` vor `/usr/bin` liegt (in `~/.bashrc` oder `~/.profile`):

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Danach einmalig prüfen:

```bash
podman --version   # muss die Host-Version ausgeben
podman info        # muss ohne Fehler durchlaufen
```

Anschließend den Container starten — `sdd start` baut das Image beim ersten Lauf
selbst, ein eigener Build-Befehl ist nicht nötig:

```bash
sdd start SPEC-0001
```

**Hintergrund:** Das Wrapper-Script leitet alle `podman`-Aufrufe per `flatpak-spawn --host` an die Host-Installation weiter. Alle Code-seitigen Fixes (kein `--userns=keep-id`, korrekte pip-Flags, Fallback wenn `gh` fehlt) sind bereits im Repo und greifen automatisch.

---

### `sdd finalize` — pytest im Container nicht gefunden

Wenn `sdd finalize` mit `bash: pytest: command not found` abbricht, liegt meist ein veraltetes `.local/`-Verzeichnis im Projektroot vor (aus einem fehlgeschlagenen Lauf). Bereinigen:

```bash
rm -rf .local/
sdd finalize <SPEC-XXXX> --no-commit
```

---

## CI-Integration

```yaml
# .github/workflows/sdd.yml
- name: SDD Validate
  run: sdd validate --strict
```

---

## Lizenz

MIT

BR
