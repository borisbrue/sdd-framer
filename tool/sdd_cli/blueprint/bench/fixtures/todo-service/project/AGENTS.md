# AGENTS.md

> Kontext für Code-generierende Agenten in diesem Repository.

## Service-Zweck

`todo-service` verwaltet Aufgaben (Todos): anlegen, bearbeiten, taggen, mit Fälligkeit versehen,
filtern, exportieren und rückgängig machen. Bedienung über eine Python-API (`TodoService`) und die
Kommandozeile `python -m todo`. Die Anforderungen stehen in `.sdd/specs/SPEC-0001` bis `SPEC-0003`.

## Architektur

- **Typ:** Python-Paket mit CLI, **nur Standardbibliothek** (Python ≥ 3.10), keine Abhängigkeiten.
- **Schichten** (verbindlich, geprüft mit `sdd arch check`, Regel ARCH-01 / ADR-0001):
  ```
  todo/__init__.py, todo/__main__.py   entry        darf alles; verdrahtet CLI und Persistenz
  todo/cli/                            cli          nur service, domain
  todo/service/                        service      nur domain
  todo/persistence/                    persistence  nur domain (JSON-Datei)
  todo/domain/                         domain       nichts aus todo; keine Datei-/Prozess-I/O
  ```
- Die Persistenz wird dem Service injiziert: `TodoService(repository)`. `todo.service` importiert
  `todo.persistence` nie; die CLI bekommt den Service bzw. eine Fabrik vom Einstieg.
- Öffentliche Namen werden aus dem jeweiligen Paket re-exportiert
  (`from todo.domain import Todo, ValidationError`, `from todo.service import TodoService`,
  `from todo.persistence import JsonFileRepository, StorageError`).

## Verzeichnisstruktur

```
/
├── todo/                 # Paket (Schichten siehe oben)
├── tests/
│   └── unit/             # unittest-Tests; jedes Testverzeichnis braucht eine __init__.py
├── docs/adr/             # Architekturentscheidungen
└── .sdd/                 # Specs, Gates, quality.yaml, architecture.yaml
```

## Externe Abhängigkeiten

| Paket / Dienst | Zweck | Env-Variable |
|----------------|-------|--------------|
| Python-Standardbibliothek (≥ 3.10) | alles | – |

Keine Drittpakete, kein Netzwerk, keine Datenbank; gespeichert wird in einer JSON-Datei.

## Build- und Start-Befehle

```bash
# Tests (unittest, JUnit-Ausgabe für sdd quality)
python3 .sdd/quality/run_tests.py --start tests --junit /tmp/junit.xml
python3 -m unittest discover -s tests -t .

# CLI
python3 -m todo --file todo.json add "Milch kaufen"
python3 -m todo --file todo.json list

# Architektur und Qualität
sdd arch check
sdd quality measure
```

## Linting- und Formatierungsregeln

- **Stil:** PEP 8, Zeilen ≤ 100 Zeichen, Typannotationen an öffentlichen Funktionen.
- **Kein Linter-Zwang:** Es gibt keine Drittwerkzeuge; `python3 -m compileall -q todo` muss durchlaufen.

## Taste Invariants

- **Inline-Disable verboten:** keine `# noqa`, `# type: ignore` oder `# pragma: no cover`, um Befunde
  zu umgehen; behebe die Ursache.
- **Schichten einhalten:** `sdd arch check` meldet keine Verstöße (ARCH-01); keine Umgehung über
  dynamische Importe.
- **Domäne ohne I/O:** `todo.domain` importiert weder `os`, `io`, `pathlib`, `json`, `csv`, `shutil`,
  `subprocess` noch `tempfile`.
- **Nur Standardbibliothek:** keine neuen Abhängigkeiten, keine `requirements.txt`.
- **CLI-Fehler:** Meldung auf stderr, Exit 1; nie ein Traceback für erwartbare Fehler.

## Konventionen

- **Sprache:** Code und Identifier Englisch; Meldungen, Docstrings und Doku Deutsch.
- **Tests:** unittest, Dateien `tests/unit/test_*.py`. Jeder Test, der eine Anforderung prüft,
  trägt den Marker `spec000N_frNN` im Namen, z. B. `test_spec0001_fr02_leerer_titel_wird_abgelehnt`.
- **Fehler:** eigene Ausnahmen (`ValidationError`, `TodoNotFoundError`, `StorageError`), keine
  nackten `Exception`s; die CLI übersetzt sie in eine Meldung auf stderr und Exit 1.
- **Keine Abhängigkeiten** außerhalb der Standardbibliothek, keine Netzwerkzugriffe.

## SDD-Kontext

- Specs: `.sdd/specs/` (SPEC-0001 → SPEC-0002 → SPEC-0003, jeweils `approved`, Gate `execute-unlocked`)
- Architektur: `.sdd/architecture.yaml`, `docs/adr/`
- Qualität: `.sdd/quality.yaml` (Sonden `tests` und `imports`)
