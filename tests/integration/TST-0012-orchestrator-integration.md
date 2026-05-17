---
id: TST-0012
project: ""
title: "Orchestrator-Integrations-Test"
level: integration
spec: SPEC-0004
contract: CON-0012
status: planned
framework: "pytest"
artifact: "tests/integration/test_orchestrator.py"
tags: ["orchestrator", "dark-factory", "pipeline"]
---

# Test: Orchestrator-Integrations-Test

> **Level:** integration · **Spec:** SPEC-0004 · **Contract:** CON-0012 · **Status:** planned

## Was wird geprüft?

Die Kerngarantien aus CON-0012:
- Pipeline-Schritte in korrekter Reihenfolge (G-02)
- Code-Generierungs-Prompt enthält keine Holdout-Inhalte (G-03/G-08)
- Retry-Logik: max. 3 Versuche, Fehlerkontext akkumuliert (G-05)
- dry-run: kein Dateisystem-Zugriff (INV-02)
- Branch-Namenskonvention (INV-01)
- Fehlende gh CLI: Warnung, kein Abbruch (INV-03)

## Vorbedingungen

- `sdd-cli[evaluate]` installiert
- LLM-Calls und git-Operationen werden gemockt
- Kein echter GitHub-Zugriff nötig

## Ablauf

### TC-01: Happy Path — erster Attempt besteht

1. Mocke `_call_llm` (Orchestrator-Code-Gen) → gibt `{"files": [...], "explanation": "..."}`
2. Mocke Evaluator → `pass_rate = 1.0`
3. Mocke `subprocess.run` für Build → Exit-Code 0
4. Mocke `subprocess.run` für `gh pr create` → gibt PR-URL zurück
5. Rufe `run_pipeline(cfg, "SPEC-0001", dry_run=False, no_pr=False)` auf
6. Prüfe: `report.final_status == "labeled"`
7. Prüfe: Branch-Name entspricht `sdd/SPEC-0001-attempt-1`
8. Prüfe: `gh pr edit --add-label sdd-auto-merge` aufgerufen

### TC-02: Retry — zweiter Attempt besteht

1. Attempt 1: Evaluator `pass_rate = 0.5` → Fail
2. Attempt 2: Evaluator `pass_rate = 1.0` → Pass
3. Prüfe: Code-Gen-Prompt im 2. Attempt enthält Evaluator-Report aus Attempt 1
4. Prüfe: `report.attempts` hat 2 Einträge
5. Prüfe: `report.final_status == "labeled"`

### TC-03: Alle Attempts scheitern

1. Alle 3 Evaluator-Läufe: `pass_rate = 0.0`
2. Prüfe: `report.final_status == "failed"`
3. Prüfe: Exit-Code 1
4. Prüfe: Genau 3 Attempts in `report.attempts`

### TC-04: dry-run — kein Schreibzugriff

1. Rufe `run_pipeline(cfg, "SPEC-0001", dry_run=True)` auf
2. Prüfe: Keine Dateien geschrieben (tmp_path unverändert)
3. Prüfe: Kein `subprocess.run` mit git/gh aufgerufen
4. Prüfe: `report.final_status == "dry_run"`

### TC-05: Holdout-Isolation im Prompt

1. Lege HOL-Dokument in `.sdd/holdout/` an
2. Erfasse den Code-Gen-Prompt (LLM-Mock)
3. Prüfe: Prompt enthält KEINEN Inhalt aus `.sdd/holdout/`
4. Prüfe: Prompt enthält Spec + AGENTS.md + Contracts

### TC-06: gh nicht verfügbar → Warnung, kein Abbruch

1. Mocke `subprocess.run(['gh', ...])` → FileNotFoundError
2. Rufe `run_pipeline(cfg, "SPEC-0001", no_pr=False)` auf
3. Prüfe: Pipeline läuft weiter (kein Exception-Abbruch)
4. Prüfe: `report.attempts[0].pr_url == None`

### TC-07: Report-Persistenz

1. Führe erfolgreiche Pipeline aus
2. Prüfe: `.sdd/pipeline/*.json` existiert
3. Prüfe: JSON enthält `spec_id`, `final_status`, `attempts`

## Erwartetes Ergebnis

Alle 7 Test-Cases bestehen mit gemockten Abhängigkeiten (kein echtes LLM, git, gh).

## Negativfälle / Edge Cases

- Spec-ID nicht gefunden → `ValueError` mit klarer Meldung
- `ANTHROPIC_API_KEY` fehlt → `RuntimeError` mit Install-Hinweis, Exit-Code 1
- Code-Gen-Response ist kein valides JSON → Attempt als Fehler markieren, Retry

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0012:

- [ ] G-02: Pipeline-Schritte in korrekter Reihenfolge (TC-01)
- [ ] G-03/G-08: Holdout-Isolation im Prompt (TC-05)
- [ ] G-05: Retry-Logik + Fehlerkontext-Akkumulation (TC-02, TC-03)
- [ ] G-07: Report-Persistenz (TC-07)
- [ ] INV-01: Branch-Namensformat (TC-01)
- [ ] INV-02: dry-run ohne Seiteneffekte (TC-04)
- [ ] INV-03: gh nicht verfügbar → kein Abbruch (TC-06)

## Hinweise zur Implementierung

```python
@pytest.fixture
def mock_llm(monkeypatch):
    responses = iter([
        '{"files": [{"path": "src/foo.py", "content": "def foo(): pass"}], "explanation": "add foo"}',
    ])
    monkeypatch.setattr("sdd_cli.orchestrator._call_code_gen", lambda *a, **kw: next(responses))
```

Git-Operationen via `monkeypatch.setattr("subprocess.run", mock_subprocess)` mocken.
