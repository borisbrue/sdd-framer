---
id: TST-0260
title: "Rollenkontext beim Erweitern"
level: acceptance            # unit | integration | contract | acceptance | performance | property
spec: SPEC-0065
contract: CON-0231
status: implemented
framework: pytest
artifact: "tests/acceptance/test_con_0231.py"
tags: [pipeline, roles, context]
---

# Test: Rollenkontext beim Erweitern

> **Level:** acceptance · **Spec:** SPEC-0065 · **Contract:** CON-0231 · **Status:** implemented

## Was wird geprüft?

Test-Autor und Implementer bekommen den bestehenden Stand (`current_files`) und die öffentlichen
Schnittstellen erledigter Abhängigkeiten (`dependency_api`); der Decomposer zerlegt reine
Absicherung als `test`-Task; der Test-Autor nutzt nur bestehende Namen und keine Mocks für
Projektklassen.

## Vorbedingungen

- Für die Pipeline-Szenarien: `openai` installiert (FakeLLM), sonst werden sie übersprungen;
  im Dev-Container laufen sie.

## Ablauf

1. Extraktor-Registry und Python-Extraktor direkt mit Quelltext aufrufen.
2. `ProjectContext.dependency_api` gegen ein temporäres Projekt mit Holdout- und Testdatei.
3. Pipeline-Lauf mit zwei Tasks (T02 hängt von T01 ab) und Fake-Rollen; Prompts auswerten.
4. Rollen, Check `task_type_present` und Golden Cases DEC-009/TAU-009 prüfen.

## Erwartetes Ergebnis

- Signaturen ohne Rümpfe, nur öffentliche Namen; Dataclass-Felder und kurze Konstanten sichtbar.
- Erster Test-Autor-Prompt zeigt `src/start.sh` unter „Aktueller Inhalt“, keine Testdatei.
- Zweiter Implementer- und Test-Autor-Prompt zeigen `src/start.sh (T01 Start)` unter
  „Schnittstellen“; der erste nicht.

## Negativfälle / Edge Cases

- Datei ohne Extraktor (`config/app.toml`): nur Pfad mit Hinweis, kein Inhalt.
- Syntaxfehler: Hinweis „nicht lesbar“.
- `.sdd/holdout/` und die Testdatei der Abhängigkeit erscheinen nie.
- Kürzung nach Budget mit Hinweis „gekürzt auf etwa N Tokens“.

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0231:

- [x] INV-01 Quellen der Rollen
- [x] INV-02 nur erledigte Abhängigkeiten, ohne Rümpfe
- [x] INV-03 Extraktor je Dateityp, sonst nur Pfad
- [x] INV-04 Budgets und Kürzung
- [x] INV-05 Prüf-Tasks als `test`
- [x] INV-06 Regeln des Test-Autors

## Hinweise zur Implementierung

Fake-Rollen über `tests/support/fake_llm.py` und `tests/support/pipeline_project.py`.
