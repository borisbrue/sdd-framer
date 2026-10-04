---
id: SPEC-0065
title: "Rollenkontext beim Erweitern bestehenden Codes"
type: feature
status: implemented
owner: "Boris"
created: 2026-10-04
updated: 2026-10-04
version: 0.2.1
priority: high
tags: [pipeline, roles, context]
depends_on: [SPEC-0053, SPEC-0061, SPEC-0064]
contracts:
- CON-0199
- CON-0231
tests:
- TST-0228
- TST-0260
fr_test_map:
  FR-01: [TST-0260]
  FR-02: [TST-0260]
  FR-03: [TST-0260]
  FR-04: [TST-0260]
  FR-05: [TST-0228, TST-0260]
---

# Rollenkontext beim Erweitern bestehenden Codes

> **Status:** draft · **Owner:** Boris · **Version:** 0.2.1

## 1. Kontext & Motivation

Im ersten vollständigen Pipeline-Lauf mit selbst gehosteten Modellen (Qwen3.8; Testprojekt aus
dem Fixture `todo-service`, SPEC-0001 bis SPEC-0003) wurden alle 90 versteckten Akzeptanztests
grün. Dafür waren aber 3, 16 und 19 Supervisor-Entscheidungen nötig, für SPEC-0003 allein 17 an
S2, davon 12 mit `stage: test`: Der Test war falsch, nicht der Code. Ursache war fast immer
fehlender Kontext, sobald eine Task bestehenden Code erweitert. HF-0012 hat dem Implementer
`current_files` gegeben; die übrigen Lücken behebt diese Spec. Die Befunde gelten unabhängig vom
Modellanbieter.

Befunde (Dogfooding 2026-09-29 bis 2026-10-04):

1. **Test-Autor ohne Code-Kontext.** Er schreibt Tests gegen erfundene Signaturen
   (`Todo("Test", …)` ohne ID; Repository mit `save([todo])`/`load()`), gegen falsche Dateiformate
   und mit `MagicMock` als Repository (IDs werden Mock-Objekte, der Test kann nie grün werden). Die
   Implementierung folgt dem Test und bricht ältere Tests.
2. **Abhängigkeiten unsichtbar.** Implementer und Test-Autor sehen nur Dateien aus den eigenen
   `allowed_paths`. Schnittstellen erledigter Abhängigkeits-Tasks (z. B. `JsonFileRepository` für
   den Service) kennen sie nur als Dateinamen und raten Methoden (`repository.load()`).
3. **Prüf-Tasks am RED-Gate.** Tasks, die nur Bestehendes absichern (etwa „Architektur
   sicherstellen“), legt der Decomposer als `code` an. Ein korrekter Test ist sofort grün und
   scheitert am RED-Gate. Den passenden Typ `test` gibt es bereits (SPEC-0061 FR-06).

Ausgegliedert: S2-Fakten, Versuchszählung und Token-Report in SPEC-0066; die Testsonde des
Fixtures `todo-service` als Hotfix zu SPEC-0063.

## 2. Zielsetzung

**Primärziel:** Test-Autor und Implementer bekommen den Kontext, den sie zum Erweitern bestehenden
Codes brauchen, und Prüf-Tasks laufen über den dafür vorgesehenen Typ.

**Erfolgskriterien (messbar):**
- [ ] Ein erneuter Lauf von SPEC-0003 des Fixtures `todo-service` mit derselben Belegung braucht
      höchstens 6 S2-Entscheidungen mit `stage: test` (vorher 12) bei weiterhin 46/46 versteckten
      Akzeptanztests.
- [ ] Die Golden Cases DEC-009 und TAU-009 bestehen mit der Referenzbelegung (`claude-cli`).

**Nicht-Ziele (explizit):**
- Keine Signatur-Extraktoren außer Python in dieser Spec; weitere Sprachen über die Registry.
- Keine Änderung an S2-Fakten, Versuchszählung oder Report (SPEC-0066).
- Kein Denkmodus als Default; das ist Konfiguration (`llm.profiles`).

## 3. Architektur & Design Patterns

| Pattern | Rolle in dieser Spec |
|---------|----------------------|
| **Strategy** | Jede Kontextquelle ist eine Strategie mit derselben Schnittstelle (Task und Budget rein, Prompt-Abschnitt raus); Rollendateien wählen sie per Namen (`inputs`). Signatur-Extraktoren sind Strategien je Dateiendung in einer Registry; der Kern bleibt sprachneutral, Python wird mitgeliefert. |
| **Proxy** | Der Allowlist-Proxy aus SPEC-0064 steht vor jedem Dateizugriff der Kontextquellen: er schließt `.sdd/`, Holdouts und die Testdatei der Task aus und kürzt nach Budget mit einem sichtbaren Hinweis. Die Datenschutz-Invariante wird an einer Stelle geprüft. |

**Alternativen:** Volle Dateien statt Signaturen für Abhängigkeiten wurden verworfen (großer
Prompt, Tests gegen Interna; SOLID-I im Review).

## 4. Funktionale Anforderungen

- **FR-01:** **`current_files` für den Test-Autor.** Die Rolle `test_author` bekommt die Quelle
  `current_files` (HF-0012): Inhalt der vorhandenen Dateien aus den `allowed_paths` der Task, ohne
  ihre Testdatei, ohne `.sdd/` und ohne Holdouts. Die Testdatei selbst erhalten die Rollen wie
  bisher über ihre eigenen Quellen (`test_file` beim Implementer); der Ausschluss gilt nur für
  `current_files`.
- **FR-02:** **Schnittstellen der Abhängigkeiten.** Neue Kontextquelle `dependency_api` für
  `test_author` und `implementer`. Sie nennt je erledigter Abhängigkeits-Task (`dependencies`) die
  vorhandenen Dateien aus deren `allowed_paths` und darin die öffentlichen Schnittstellen:
  Definitionen mit Signatur und Kurzbeschreibung, ohne Rümpfe. Was öffentlich ist und was als
  Kurzbeschreibung gilt, bestimmt der Extraktor der jeweiligen Sprache (FR-03); für Python sind es
  Klassen, Methoden und Funktionen ohne führenden Unterstrich mit der ersten Docstring-Zeile.
- **FR-03:** **Extraktoren je Dateiendung.** Signaturen liefert ein Extraktor aus einer Registry
  je Dateiendung. Mitgeliefert ist Python (`.py`). Für Dateien ohne Extraktor nennt
  `dependency_api` nur den Pfad.
- **FR-04:** **Prüf-Tasks als `test`.** Die Rolle `decomposer` legt Tasks, die nur bestehendes
  Verhalten absichern und keinen Code ändern sollen, als Typ `test` an. Golden Case DEC-009 prüft
  das an einer Spec mit einer reinen Prüfanforderung.
- **FR-05:** **Regeln für den Test-Autor.** Die Rolle `test_author` testet gegen die Namen aus
  `current_files` und `dependency_api`, erfindet keine Schnittstellen und ersetzt vorhandene
  Klassen des Projekts nicht durch Mocks. Golden Case TAU-009 prüft das an einer Erweiterung mit
  vorhandenem Repository.

## 5. Nicht-funktionale Anforderungen

| Kategorie | Anforderung |
|-----------|-------------|
| Budget | `current_files` beim Test-Autor 8 000, `dependency_api` 4 000 Tokens; Kürzung mit Hinweis |
| Datenschutz | Keine Inhalte aus `.sdd/` oder Holdouts in `current_files` oder `dependency_api` |
| Kompatibilität | Rollendateien behalten ihre bisherigen Quellen; die neuen sind zusätzlich |
| Sprachneutralität | Der Pipeline-Kern nennt keine Sprache; Python-Wissen liegt nur im Extraktor |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Rollenkontext beim Erweitern

  Scenario: Test-Autor sieht bestehenden Code
    Given eine Task erweitert eine vorhandene Datei aus ihren allowed_paths
    When der Test-Autor aufgerufen wird
    Then enthält sein Prompt den Inhalt dieser Datei

  Scenario: Schnittstellen einer erledigten Abhängigkeit
    Given T02 hängt von T01 ab, T01 ist erledigt und hat todo/persistence/storage.py geschrieben
    When der Implementer von T02 aufgerufen wird
    Then nennt dependency_api die Klasse JsonFileRepository mit ihren öffentlichen Methoden ohne Rümpfe
```

## 7. Edge Cases & Fehlerfälle

- Abhängigkeit noch nicht erledigt oder ohne vorhandene Dateien: kein Eintrag.
- Datei nicht parsebar (Syntaxfehler): nur der Pfad mit Hinweis.
- Budget überschritten: Kürzung am Ende mit Hinweis „… gekürzt“.

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ | Was wird garantiert? |
|-------------|-----|----------------------|
| CON-0199 | data | `dependency_api` in der geschlossenen Liste der Kontextquellen |
| CON-0231 | behavior | Inhalt und Grenzen von `current_files` (Test-Autor) und `dependency_api`, Prüf-Tasks als `test`, Regeln für den Test-Autor |

## 9. Tests (wie wird verifiziert)

| Test-ID | Level | Was prüft der Test? |
|---------|-------|---------------------|
| (nach Review) | unit / acceptance | CON-0199-Erweiterung, Szenarien aus CON-0231 |

## 10. Offene Fragen

- Keine. Entscheidungen aus dem Review (2026-10-04): Aufteilung in SPEC-0065 und SPEC-0066 plus
  Hotfix für die Testsonde; `dependency_api` nur mit Signaturen; Patterns Strategy und Proxy.

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung            |
|------------|---------|---------------|---------------------|
| 2026-10-04 | 0.1.0   | Boris, Claude | Initiale Erstellung (Sammel-Spec) |
| 2026-10-04 | 0.2.0   | Boris, Claude | Review: aufgeteilt (S2/Report in SPEC-0066, Testsonde als Hotfix), Signaturen statt Dateien, Extraktor-Registry, Patterns |
| 2026-10-04 | 0.2.1   | Boris, Claude | SOLID-Warnungen: sprachneutrale Definition von „öffentlich“, Testdatei-Ausschluss nur für current_files |
