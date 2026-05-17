---
id: TST-0010
project: ""
title: "Evaluator-Integrations-Test"
level: integration
spec: SPEC-0004
contract: CON-0010
status: planned
framework: "pytest"
artifact: "tests/integration/test_evaluator.py"
tags: ["evaluator", "holdout", "dark-factory"]
---

# Test: Evaluator-Integrations-Test

> **Level:** integration · **Spec:** SPEC-0004 · **Contract:** CON-0010 · **Status:** planned

## Was wird geprüft?

Die Kerngarantien aus CON-0010:
- 3-Runs-Protokoll pro Szenario (G-03)
- 2/3 Pass-Threshold (G-03)
- Report-Persistenz im richtigen Format (G-06)
- Exit-Code-Logik (G-05)
- Sourcecode-Isolation: Evaluator liest nur aus `.sdd/holdout/` (INV-01)

## Vorbedingungen

- `sdd-cli[evaluate]` installiert (anthropic, httpx)
- `ANTHROPIC_API_KEY` gesetzt (für LLM-Calls) **oder** LLM wird mit Mock ersetzt
- Ein minimales SDD-Testprojekt mit `pytest` tmp_path-Fixture

## Ablauf

### TC-01: Happy Path — 2/3 bestehende Runs

1. Lege ein HOL-Dokument in `.sdd/holdout/HOL-0001-test.md` an
2. Mocke `_call_llm` so dass es abwechselnd `passed: true/true/false` zurückgibt
3. Mocke httpx so, dass HTTP-Request mit Status 200 beantwortet wird
4. Rufe `run_evaluation(cfg, "http://localhost")` auf
5. Prüfe: `report.scenarios[0].passed == True`
6. Prüfe: `report.scenarios[0].pass_count == 2`
7. Prüfe: `report.pass_rate == 1.0`

### TC-02: Fail — nur 1/3 Runs bestehen

1. Mocke `_call_llm`: `passed: true/false/false`
2. Prüfe: `report.scenarios[0].passed == False`
3. Prüfe: Exit-Code wäre 1

### TC-03: Report-Persistenz

1. Rufe `persist_report(cfg, report)` auf
2. Prüfe: Datei existiert in `.sdd/evaluations/`
3. Prüfe: JSON ist valide und enthält `summary.pass_rate`

### TC-04: HOL-Filter

1. Lege zwei HOL-Dokumente an (HOL-0001, HOL-0002)
2. Rufe `run_evaluation(cfg, url, hol_ids=["HOL-0001"])` auf
3. Prüfe: Nur HOL-0001 im Report, HOL-0002 nicht

### TC-05: Disabled-Szenarien überspringen

1. Setze `status: disabled` in HOL-Dokument
2. Prüfe: Szenario erscheint nicht im Report

### TC-06: Fehlende Dependencies

1. Stelle sicher httpx nicht importierbar (monkeypatch)
2. Prüfe: `run_evaluation` wirft `RuntimeError` mit Install-Hinweis

## Erwartetes Ergebnis

Alle 6 Test-Cases bestehen ohne echte API-Calls oder laufenden Service.

## Negativfälle / Edge Cases

- Leeres `.sdd/holdout/` → leerer Report, pass_rate == 0.0, Exit-Code 0
- HTTP-Timeout im Run → nur dieser Run als `passed: false`, andere Runs laufen weiter
- LLM gibt kein valides JSON zurück → Run als `passed: false, reasoning: "LLM-Planungsfehler"`

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0010:

- [ ] G-03: 3 Runs pro Szenario, min. 2/3 Threshold (TC-01, TC-02)
- [ ] G-05: Pass-Rate-Ausgabe und Exit-Code (TC-02)
- [ ] G-06: Report-Persistenz und JSON-Format (TC-03)
- [ ] INV-01: Nur .sdd/holdout/ wird gelesen (TC-04)
- [ ] INV-02: status: disabled überspringen (TC-05)
- [ ] G-07: Klare Fehlermeldung bei fehlenden Dependencies (TC-06)

## Hinweise zur Implementierung

```python
# pytest-Fixture für minimales SDD-Testprojekt
@pytest.fixture
def sdd_project(tmp_path):
    (tmp_path / ".sdd" / "holdout").mkdir(parents=True)
    (tmp_path / ".sdd" / "config.yaml").write_text("version: '1.0.0'\n")
    return SddConfig(root=tmp_path, raw={})
```

LLM-Calls via `monkeypatch.setattr(evaluator, "_call_llm", mock_fn)` mocken.
HTTP-Calls via `respx` oder `pytest-httpx` mocken.
