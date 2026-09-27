# AGENTS.md – SDD Blueprint

Kontext-Datei für KI-Agenten und automatisierte Tools. Wird von `sdd validate` auf Vollständigkeit geprüft.

## Service-Zweck

SDD Blueprint ist ein sprachneutrales Spec-Driven Development System. Es erzwingt Traceability zwischen Feature-Specs, Contracts und Tests und stellt sicher, dass kein Code ohne dokumentierte Anforderung und Contract existiert.

Bestandteile:
- **`sdd`-CLI** – Dokumente anlegen, validieren, Traceability erzeugen
- **Web API** – FastAPI-Wrapper um die CLI-Logik
- **VS Code Extension** – TreeView, Linting, Go-to-Definition (in Entwicklung)
- **Blueprint** – Das gesamte Repo dient als wiederverwendbares Grundgerüst (`sdd init` kopiert es)

## Architektur

```
Web UI / VS Code Extension
        │
        ▼
   FastAPI (web/)
        │
        ▼
  sdd_cli (tool/sdd_cli/)
        │
   ┌────┴────────────────┐
   │                     │
Filesystem           .sdd/
(specs/, contracts/,  config.yaml
 tests/, docs/)       schemas/
                       templates/
```

Die CLI ist der einzige Schreiber auf dem Filesystem. Web API und Extension delegieren alle Operationen an die CLI-Module. Keine Datenbank – alle Daten liegen als Markdown-Dateien mit YAML-Frontmatter vor.

Architekturentscheidungen mit maschineller Folge stehen als ADR unter `docs/adr/`, ihre Regeln in `.sdd/architecture.yaml` (SPEC-0054, SPEC-0059):

| ADR | Entscheidung | Regel |
|-----|--------------|-------|
| ADR-0002 | CLI ist einziger Schreiber für SDD-Artefakte | ARCH-01 |
| ADR-0003 | Schichtrichtung Einstieg → Web/UI/PWA/Hub → CLI/Pipeline → LLM → Core | ARCH-02 |
| ADR-0004 | LLM-Zugriff nur über die Provider-Factory (`tool/sdd_cli/llm/factory.py`) | ARCH-03 |
| ADR-0005 | Claude-CLI wird nur im Provider `claude_cli` aufgelöst | ARCH-04 |
| ADR-0006 | Pipeline-Interna (`mediator`, `runner`, `steps`, `gates`, `providers`, `decisions`, `context`) nur in `pipeline` und im Einstieg; sonst `pipeline.facade` | ARCH-05 |

`sdd arch check` wertet sie aus; bekannte Altlasten stehen mit Grund in `.sdd/quality/arch-baseline.json`. **Ein Commit kann am Pre-Commit-Hook scheitern** (`sdd install-hooks`), sobald eine gestagte `.py`-Datei eine Regel neu verletzt. Neue Architekturentscheidung = ADR und Regel im selben PR.

## Verzeichnisstruktur

```
.sdd/               # Projektkonfiguration
  config.yaml       # Name, Präfixe, aktive Regeln
  schemas/          # JSON-Schemas für Frontmatter-Validierung
  templates/        # Jinja2-Templates für neue Dokumente
specs/              # SPEC-XXXX-*.md  – Feature-Anforderungen
contracts/
  api/              # CON-XXXX – OpenAPI-Contracts
  behavior/         # CON-XXXX – Gherkin-Contracts
  performance/      # CON-XXXX – SLO-Contracts
tests/
  unit/             # TST-XXXX – Unit-Tests
  contract/         # TST-XXXX – Contract-Konformitätstests
  acceptance/       # TST-XXXX – Acceptance-Tests
  performance/      # TST-XXXX – Performance-Tests
docs/
  adr/              # ADR-XXXX – Architecture Decision Records
  traceability.md   # Generiert von `sdd trace`
tool/
  sdd_cli/          # Python-Paket: CLI-Kern
web/                # FastAPI-App
vscode-extension/   # VS Code Extension (TypeScript)
```

## Externe Abhängigkeiten

| Paket | Zweck |
|---|---|
| `click` ≥ 8.1 | CLI-Framework |
| `pyyaml` ≥ 6.0 | YAML-Frontmatter-Parsing |
| `jsonschema` ≥ 4.21 | Frontmatter-Schemavalidierung |
| `rich` ≥ 13.7 | Terminal-Ausgabe (Tabellen, Farben) |
| `fastapi` ≥ 0.111 | Web-API-Framework |
| `uvicorn[standard]` ≥ 0.29 | ASGI-Server |
| `ruff` ≥ 0.4 | Linting + Formatting (dev) |
| `pytest` ≥ 8.0 | Tests (dev) |
| `httpx` ≥ 0.27 | HTTP-Client für API-Tests (dev) |

Keine Datenbank, kein externer Service – das System ist vollständig offline-fähig.

## Container-Runtime (Podman / Docker)

`sdd start` und `sdd finalize` starten isolierte Container. Die Runtime wird in `.sdd/config.yaml` konfiguriert:

```yaml
docker:
  runtime: podman   # oder: docker
  image: sdd-dev:latest
  dockerfile: .sdd/Dockerfile
```

**Wichtige Eigenschaft der PodmanRuntime:** Kein `--userns=keep-id` — der Container läuft als uid=0 im rootless User-Namespace, was System-pip-Installs (`/usr/local/lib/...`) erlaubt. Mit `keep-id` würde der Container als Host-User laufen und könnte nicht in die System-Site-Packages schreiben.

**Flatpak-Umgebung (VS Code aus Flatpak-Store, z.B. SteamOS):** Podman ist im Flatpak-Namespace nicht direkt erreichbar. Einmaliges Setup:

```bash
mkdir -p ~/.local/bin
cat > ~/.local/bin/podman << 'EOF'
#!/bin/bash
flatpak-spawn --host podman "$@"
EOF
chmod +x ~/.local/bin/podman
# ~/.local/bin muss vor /usr/bin in $PATH stehen (prüfen mit: which podman)
```

Danach Podman testen und Image bauen:

```bash
podman info && sdd dev build
```

Dieses Wrapper-Script ist **nicht** im Repo — es muss einmalig pro Entwickler-Maschine angelegt werden, wenn VS Code als Flatpak läuft.

## Build- und Start-Befehle

```bash
# Abhängigkeiten installieren (uv empfohlen)
uv sync
# oder klassisch:
cd tool && pip install -e ".[dev]"

# CLI nutzen
sdd --help
sdd validate
sdd status

# Neue Dokumente anlegen
sdd new spec "Feature Name"
sdd new contract --spec SPEC-0001 --format openapi --title "API Titel"
sdd new test --spec SPEC-0001 --contract CON-0001 --level contract --title "Test Titel"
sdd new adr "Architekturentscheidung"

# Traceability-Matrix erzeugen
sdd trace

# Qualität messen (SPEC-0054)
sdd stack apply python-cli --only quality   # Sonden ins Projekt kopieren (SPEC-0057)
sdd quality doctor                  # Sonden prüfen
sdd quality measure --spec SPEC-0054 --json
sdd arch check                      # Architekturregeln

# Web API starten
cd web && uvicorn main:app --reload

# Tests ausführen
pytest
pytest tests/unit/
pytest tests/contract/
```

## Linting- und Formatierungsregeln

Tool: **ruff** (konfiguriert in `pyproject.toml`)

```bash
ruff check tool/          # Linting
ruff check tool/ --fix    # Auto-Fix
ruff format tool/         # Formatierung
```

Aktive Regelgruppen: `E`, `F`, `I` (isort), `UP` (pyupgrade), `B` (bugbear), `SIM` (simplify).  
Zeilenlänge: 100 Zeichen. `E501` (Zeilenlängen-Fehler) ist deaktiviert.  
Python-Zielversion: 3.10+.

Für die VS Code Extension gilt: TypeScript strict mode, ESLint mit Standard-Regeln.

## Taste Invariants

Diese Regeln gelten für alle Code-Änderungen im gesamten Repo und werden von
`sdd validate` als Fehler durchgesetzt — nie als Warnung.

- **Inline-Disable verboten:** Unterdrücke niemals Linter-Fehler durch Inline-Kommentare
  (`# noqa`, `# type: ignore`, `// eslint-disable-next-line`, `@SuppressWarnings`).
  Behebbe die Ursache — unterdrücke nicht den Fehler.
- **Kein manuelles Vergeben von IDs:** Dokument-IDs (SPEC-XXXX, CON-XXXX, TST-XXXX)
  werden ausschließlich von der CLI vergeben. Niemals manuell nummerieren oder korrigieren.
- **CLI als einziger Filesystem-Schreiber [ARCH-01]:** Web API und Extension delegieren alle
  Schreiboperationen an CLI-Module. Kein direktes Schreiben in `.sdd/` aus Web- oder
  Extension-Code.

## Konventionen

**Dokument-IDs** werden automatisch von der CLI vergeben – niemals manuell nummerieren.

**Dateinamen-Schema:**
- `SPEC-XXXX-kebab-case-titel.md`
- `CON-XXXX-kebab-case-titel.md`
- `TST-XXXX-kebab-case-titel.md`
- `ADR-XXXX-kebab-case-titel.md`

**Frontmatter:** Jedes Dokument hat YAML-Frontmatter. Das Schema liegt in `.sdd/schemas/`. `sdd validate` prüft Konformität.

**Referenzielle Integrität** (Invarianten):
1. Jede Spec referenziert ≥ 1 Contract.
2. Jeder Contract referenziert ≥ 1 Test.
3. Alle Referenzen zeigen auf existierende Dokumente.
4. Keine verwaisten Contracts oder Tests ohne Spec-Bezug.

**Commit-Stil:** Konventionelle Commits (`feat:`, `fix:`, `docs:`, `chore:`).  
**Sprache:** Deutsch in Kommentaren, Docs und Commit-Messages; Englisch im Code.

## SDD-Kontext

Dieses Repository *ist selbst* das Blueprint. Es dient zwei Zwecken gleichzeitig:

1. **Laufendes System** – Die CLI ist hier installierbar und voll funktionsfähig.
2. **Vorlage** – `sdd init --name "Neues Projekt"` kopiert die Struktur in ein anderes Verzeichnis.

Das Beispiel-Feature **"User Login"** (SPEC-0001 → CON-0001/2/3 → TST-0001/2/3/4, ADR-0001) zeigt, wie alle Bestandteile zusammenwirken. Beim Anpassen des Blueprints diese Beispieldateien ersetzen, nicht löschen.

In CI sollte `sdd validate --strict` als Pflicht-Gate laufen – es blockiert jeden Merge, der gegen die Traceability-Invarianten verstößt.
