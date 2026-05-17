# sdd-cli

Sprachneutrale CLI für Spec-Driven Development. Verwaltet Specs, Contracts und Tests in einem
einheitlichen, validierbaren Format — projektübergreifend wiederverwendbar.

## Installation

```bash
# Aus diesem Verzeichnis heraus, editierbar:
pip install -e .

# Oder global aus dem gebauten Wheel:
pip install dist/sdd_cli-0.1.0-py3-none-any.whl
```

Nach der Installation steht der Befehl `sdd` im Pfad zur Verfügung.

## Befehle

| Befehl                                                     | Wirkung                                                       |
|------------------------------------------------------------|---------------------------------------------------------------|
| `sdd init [--name X] [--path .] [--force]`                 | Legt `.sdd/`, `specs/`, `contracts/`, `tests/`, `docs/` an    |
| `sdd new spec "<Titel>" [--owner X]`                       | Neue Spec mit nächster freier ID                              |
| `sdd new contract --spec SPEC-NNNN --format openapi …`     | Neuer Contract, automatisch verknüpft mit der Spec            |
| `sdd new test --spec … --contract … --level contract`      | Neuer Test, verknüpft mit Spec und Contract                   |
| `sdd new adr "<Titel>"`                                    | Neue Architecture Decision Record                             |
| `sdd validate [--strict]`                                  | Prüft Frontmatter, Schemas und Verknüpfungen                  |
| `sdd trace`                                                | Generiert `docs/traceability.md`                              |
| `sdd status`                                               | Tabellarische Übersicht aller Specs                           |

## Unterstützte Contract-Formate

Werden mit `--format` ausgewählt:

- **API:** `openapi`, `asyncapi`, `graphql`, `grpc`
- **Daten:** `json-schema`, `avro`, `protobuf`
- **Verhalten:** `gherkin`, `markdown`
- **Performance:** `slo-yaml`

## Typischer Workflow

```bash
# 1. Neues Projekt aufsetzen
mkdir mein-projekt && cd mein-projekt
sdd init --name "Mein Projekt"

# 2. Vision, Glossar, Constraints ausfüllen
$EDITOR specs/vision.md  # ggf. aus Template kopieren

# 3. Erste Spec
sdd new spec "User Login"

# 4. Contracts und Tests anlegen
sdd new contract --spec SPEC-0001 --format openapi --title "Login API"
sdd new contract --spec SPEC-0001 --format gherkin --title "Login Behavior"
sdd new test     --spec SPEC-0001 --contract CON-0001 --level contract --title "OpenAPI Konformitaet"
sdd new test     --spec SPEC-0001 --contract CON-0002 --level acceptance --title "Login Szenarien"

# 5. IDs in der Spec eintragen (Frontmatter: contracts: [...], tests: [...])
$EDITOR specs/SPEC-0001-user-login.md

# 6. Konsistenzcheck
sdd validate

# 7. Traceability-Matrix erzeugen
sdd trace
```

## Validierungsregeln

Konfiguriert in `.sdd/config.yaml` unter `validation:`:

| Regel                          | Default | Bedeutung                                          |
|--------------------------------|---------|----------------------------------------------------|
| `require_contract_per_spec`    | `true`  | Jede Spec MUSS ≥ 1 Contract referenzieren          |
| `require_test_per_contract`    | `true`  | Jeder Contract MUSS ≥ 1 Test referenzieren         |
| `fail_on_orphans`              | `true`  | Verwaiste Contracts/Tests erzeugen Fehler          |

## CI-Integration

Beispiel für GitHub Actions:

```yaml
- name: Validate SDD
  run: |
    pip install sdd-cli
    sdd validate --strict
    sdd trace
    git diff --exit-code docs/traceability.md  # Drift erkennen
```

## Architektur

```
sdd_cli/
├── main.py          – click-Frontend
├── config.py        – Projekt-Konfiguration laden
├── frontmatter.py   – Markdown + YAML-Frontmatter parsen
├── ids.py           – Eindeutige ID-Vergabe
├── templates.py     – Template-Rendering
├── init.py          – Projekt-Initialisierung
├── validate.py      – JSON-Schema und referenzielle Integrität
└── traceability.py  – Matrix-Generator
```

Reine Logik in eigenen Modulen, `main.py` ist nur Wrapper → das VS-Code-Plugin kann
dieselben Module direkt importieren.
