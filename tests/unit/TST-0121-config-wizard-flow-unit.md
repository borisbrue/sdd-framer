---
id: TST-0121
title: "Config-Wizard-Flow (Unit)"
level: unit
spec: SPEC-0027
contract: CON-0102
status: draft
artifact: tests/unit/test_tst_0121.py
---

# TST-0121: Config-Wizard-Flow

## Zu prüfendes Verhalten

`config_wizard.py` führt durch alle Config-Sections, unterstützt Section-Routing,
CI/CD-Modus und schreibt `config.yaml` atomar (CON-0102).

## Testfälle

- T01: Vollständiger Wizard-Durchlauf schreibt valide `config.yaml`
- T02: `--section llm` fragt nur LLM-Pool-Abschnitt ab
- T03: Wizard-Abbruch (Abbruch-Signal) lässt bestehende `config.yaml` unverändert (INV-01)
- T04: Ungültige Eingabe für `max_parallel_containers` → Fehlermeldung + Wiederholung (INV-02)
- T05: `--non-interactive` mit gültigen Flags → Exit-Code 0, kein Prompt (INV-03)
- T06: `--non-interactive` mit ungültigem Wert → Exit-Code 1 (INV-03)
- T07: Automatischer Start wenn `project.description` Platzhalter enthält
