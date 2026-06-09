---
id: SPEC-0041
title: Implementierungs-Vollständigkeits-Gate
type: feature
status: implemented
owner: borisbrue
created: 2026-06-09
updated: '2026-06-09'
version: 0.1.0
priority: high
tags:
- process
- validation
- tdd-gate
- fr-traceability
depends_on:
- SPEC-0010
- SPEC-0014
- SPEC-0028
contracts:
- CON-0152
- CON-0153
- CON-0154
- CON-0155
- CON-0156
tests:
- TST-0178
- TST-0179
- TST-0180
- TST-0181
- TST-0182
adrs: []
started_at: '2026-06-09T07:46:57Z'
---
# Implementierungs-Vollständigkeits-Gate

## 1. Kontext & Motivation

SPEC-0037 wurde als `implemented` markiert, obwohl zwei funktionale Anforderungen
nie implementiert wurden: FR-05 (React-SPA-Einstiegspunkt) hatte keinen einzigen
Test, und die Router-Registrierung wurde durch einen späteren Hotfix-Commit
unbemerkt entfernt.

Die Ursache liegt in strukturellen Lücken im SDD-Prozess:

1. **`sdd finalize` prüft nur „Tests grün"** — `_mark_implemented()` wird
   aufgerufen sobald `pytest` Exit-Code 0 zurückgibt. Ob alle FRs durch Tests
   abgedeckt sind, ist irrelevant.

2. **`spec_approve` prüft nur Existenz, nicht Vollständigkeit** — Es wird
   geprüft ob *irgendwelche* Contracts und Tests verknüpft sind, nicht ob
   *jedes FR* mindestens eine Test-Referenz hat.

3. **`sdd validate` kennt keine FR→Test-Traceability** — Es gibt keinen Check
   der sagt: „FR-05 ist in keinem Test referenziert."

4. **Tests decken nur Backend-Klassen ab** — Für Specs mit Tag `webui`,
   `frontend` oder `api` gibt es keine Pflicht für einen Integration-Test, der
   das Feature in der laufenden App nachweist.

5. **Hotfixes haben kein Regressions-Gate** — Manuelle Commits außerhalb des
   `sdd implement`-Zyklus können Routen oder UI-Komponenten entfernen, ohne
   dass dies aufgefangen wird.

SPEC-0028 deckt den inhaltlichen Code-Review-Prozess ab. Diese Spec ergänzt
ihn um die strukturelle Vollständigkeitsprüfung: „Ist alles, was die Spec
fordert, auch tatsächlich vorhanden?"

## 2. Zielsetzung

**Primärziel:**
Jede Spec kann den Status `implemented` nur noch dann erreichen, wenn alle ihre
funktionalen Anforderungen auf mindestens einen passing Test verweisen und
typen-spezifische Pflichtanforderungen (Integration-Test für UI/API-Specs,
Route-Smoke-Test für API-Specs) erfüllt sind.

**Erfolgskriterien (messbar):**
- [ ] `sdd finalize` bricht mit einer klaren Fehlermeldung ab, wenn mindestens
      ein FR keine Test-Referenz im Spec-Frontmatter hat
- [ ] `spec_approve` bricht ab wenn FRs ohne zugeordneten Test-ID existieren —
      die bloße Existenz von Tests reicht nicht mehr
- [ ] `sdd validate` meldet einen Error für Specs mit Tag `webui`, `frontend`
      oder `api`, die keinen Test vom Typ `integration` oder `contract` haben
      der eine laufende Instanz voraussetzt
- [ ] Ein Post-Commit-Hook schlägt an wenn `main.py`, `routes/` oder `App.tsx`
      geändert werden, ohne dass die betroffenen Spec-Tests noch grün sind
- [ ] Das SPEC-0037-Szenario ist nicht mehr möglich: eine Spec mit UI-FR kann
      `implemented` nur erreichen wenn ein Test die UI-Komponente oder
      Route-Erreichbarkeit nachweist

**Nicht-Ziele (explizit):**
- Kein vollständiges Test-Coverage-Tool (kein Line-Coverage, kein
  Branch-Coverage — nur FR→Test-Mapping auf Spec-Ebene)
- Kein automatisches Test-Generieren wenn ein FR ohne Test erkannt wird —
  nur Blockierung mit erklärender Fehlermeldung
- Kein rückwirkendes Enforcement auf bereits `implemented` Specs — nur Specs
  mit Status `draft` oder `approved` unterliegen dem Gate
- Kein Ersatz für inhaltliche Code-Reviews — diese bleiben Aufgabe von
  SPEC-0028; diese Spec prüft ausschließlich strukturelle Vollständigkeit
- Keine Änderung am Test-Inhalt oder Test-Qualität — ein Test der immer
  grün ist erfüllt formal die Anforderung (Qualität = SPEC-0028)

## 3. Architektur & Design Patterns

### Pattern 1 — Chain of Responsibility (Vollständigkeits-Checks)
> [Refactoring Guru – Chain of Responsibility](https://refactoring.guru/design-patterns/chain-of-responsibility)

Die Vollständigkeits-Checks werden als verkettete Handler implementiert:
`FrCoverageChecker → TypeAwareTestChecker → RouteRegistrationChecker`.
Jeder Handler prüft einen Aspekt und gibt bei Fehler eine strukturierte
`ComplianceIssue` zurück. Der `FinalizationGate` ruft die Kette auf und
bricht bei erstem Fehler ab (oder sammelt alle Fehler für Übersichtlichkeit).

**Begründung:** Neue Checks können ohne Änderung bestehender Checker
hinzugefügt werden. Jeder Check ist einzeln testbar. Die Reihenfolge ist
explizit und konfigurierbar.

```python
class ComplianceChecker(Protocol):
    def check(self, spec: SpecDoc, cfg: SddConfig) -> list[ComplianceIssue]: ...

class FrCoverageChecker:
    """FR-01: Jedes FR im Spec-Text muss in mindestens einem test_ids-Feld referenziert sein."""
    def check(self, spec: SpecDoc, cfg: SddConfig) -> list[ComplianceIssue]: ...

class TypeAwareTestChecker:
    """FR-03: Specs mit Tag webui/frontend/api brauchen mind. 1 Integration/Contract-Test."""
    def check(self, spec: SpecDoc, cfg: SddConfig) -> list[ComplianceIssue]: ...

class RouteRegistrationChecker:
    """FR-04: Specs mit Tag api prüfen ob ihre Routen in main.py registriert sind."""
    def check(self, spec: SpecDoc, cfg: SddConfig) -> list[ComplianceIssue]: ...
```

### Pattern 2 — Specification (FR→Test-Mapping-Regel)
> [Refactoring Guru – Specification (via Composite)](https://refactoring.guru/design-patterns/composite)

Die Regel „FR-X muss durch TST-Y abgedeckt sein" wird als
`FrCoverageSpecification` modelliert: Sie liest alle `FR-XX`-Bezeichner aus
dem Spec-Text, liest alle `test_ids`-Einträge aus den Task-Definitionen
(`.sdd/tasks/SPEC-XXXX.json`) und meldet die Differenzmenge als
nicht-abgedeckte FRs.

**Begründung:** Die Regel ist deklarativ und unabhängig von der
Implementierungssprache. Sie kann in `spec_approve`, `sdd validate` und
`sdd finalize` ohne Duplizierung eingebunden werden.

```python
@dataclass
class FrCoverageResult:
    covered: list[str]      # ["FR-01", "FR-02"]
    uncovered: list[str]    # ["FR-05"]  ← blockiert finalize

class FrCoverageSpecification:
    def is_satisfied_by(self, spec: SpecDoc, tasks: list[Task]) -> FrCoverageResult: ...
```

### Pattern 3 — Hook (Post-Commit-Regressions-Gate)
> [Refactoring Guru – Observer](https://refactoring.guru/design-patterns/observer)

Der Post-Commit-Hook ist ein Git-Hook-Skript das als Observer auf
Dateiänderungen reagiert: Wenn `main.py`, `routes/*.py` oder
`src/App.tsx` im Commit enthalten sind, ermittelt es die betroffenen
Spec-IDs (via `.sdd/tasks/SPEC-XXXX.json` `commit_hash`-Feld) und ruft
`pytest` für die zugehörigen Tests auf.

**Begründung:** Git-Hooks sind projektlokal, versionierbar und brauchen keine
externe CI-Infrastruktur. Der Observer-Ansatz entkoppelt die
Regressions-Erkennung von der eigentlichen Commit-Logik.

## 4. Funktionale Anforderungen

- **FR-01: FR-Extraktion aus Spec-Text** — `FrCoverageSpecification` extrahiert
  alle Bezeichner der Form `FR-\d+` aus dem Spec-Markdown-Body. Nur FRs aus
  dem Abschnitt „Funktionale Anforderungen" zählen (Überschrift
  `## \d+\. Funktionale Anforderungen`).

- **FR-02: FR→Test-Mapping über Task-Definitionen** — Jeder Task in
  `.sdd/tasks/SPEC-XXXX.json` hat ein `test_ids`-Array und eine
  `description` die FRs referenziert. `FrCoverageSpecification` prüft für
  jedes extrahierte FR ob mindestens ein Task existiert dessen `description`
  das FR enthält UND dessen `test_ids` nicht leer ist. Alternativ kann der
  Spec-Autor FRs direkt im Frontmatter unter `fr_test_map` explizit zuordnen
  (Override für manuell erstellte Tasks).

- **FR-03: Typen-aware Test-Pflicht** — `TypeAwareTestChecker` prüft: Hat die
  Spec einen der Tags `webui`, `frontend`, `api`? Falls ja: Gibt es mindestens
  einen Test dessen `.sdd/tests/<stufe>/TST-XXXX.md`-Datei `stufe: contract`
  oder `stufe: integration` hat? Falls nicht: `ComplianceIssue` mit Severity
  `error`.

- **FR-04: Route-Registrierungs-Check** — `RouteRegistrationChecker` prüft für
  Specs mit Tag `api`: Enthält mindestens einer der in
  `compliance.route_entry_points` konfigurierten Entry-Points (Default:
  `tool/sdd_cli/web/api/main.py`) einen `include_router`-Aufruf der auf eine
  Datei aus `routes/` verweist die im selben Commit wie die Spec angelegt
  wurde? Prüfung via `grep` auf den Router-Variablennamen aus der Route-Datei.
  Mehrere Entry-Points ermöglichen den Einsatz in Hub- und Tool-Projekten.

- **FR-05: Enforcement in `spec_approve`** — `sdd spec approve` ruft
  `FrCoverageSpecification` auf bevor die Phase `spec-approved` gesetzt wird.
  Bei `uncovered` FRs: Exit 2 mit Meldung „FR-XX hat keinen zugeordneten Test
  — lege zuerst TST-XXXX an und trage es in tasks/SPEC-XXXX.json ein."

- **FR-06: Enforcement in `sdd finalize`** — `SpecFinalizer.run()` ruft die
  vollständige Checker-Kette auf bevor `_mark_implemented()` aufgerufen wird.
  Bei `ComplianceIssue` mit Severity `error`: kein Commit, kein Status-Update,
  strukturierte Fehlerliste im Terminal.

- **FR-07: Enforcement in `sdd validate`** — `validate.py` ergänzt
  `_check_lifecycle_rules()` um einen Aufruf der Checker-Kette für alle Specs
  mit Status `approved` oder `in-progress`. Severity `error` → `sdd validate`
  gibt Exit-Code 1 zurück.

- **FR-08: Post-Commit-Hook (blocking)** — `sdd install-hooks` installiert
  einen `pre-commit`-Hook (nicht post-commit, da blocking). Der Hook liest
  `git diff --cached --name-only`, prüft ob `main.py`, `routes/` oder
  `App.tsx` betroffen sind, ermittelt die betroffenen Spec-IDs und führt
  `pytest tests/ -k "<spec_test_filter>" --tb=short` aus. Bei Fehler: Hook
  gibt Exit-Code 1 zurück — der Commit wird abgebrochen. Explizites Opt-out
  via `git commit --no-verify` ist möglich und wird im Terminal protokolliert.

- **FR-09: Konfigurierbarkeit** — Alle Checks können in `.sdd/config.yaml`
  unter `compliance:` deaktiviert werden (Default: alle aktiv). Ermöglicht
  schrittweise Einführung ohne bestehende Workflows zu brechen.

```yaml
# .sdd/config.yaml
compliance:
  fr_coverage_check: true        # FR-01/FR-02: FR→Test-Mapping
  type_aware_test_check: true    # FR-03: Integration-Test für webui/api
  route_registration_check: true # FR-04: Router-Registrierung prüfen
  route_entry_points:            # FR-04: Entry-Points für Router-Check
    - tool/sdd_cli/web/api/main.py
    - web/api/main.py
  post_commit_hook: true         # FR-08: Blocking pre-commit Regressions-Hook
```

## 5. User Stories

| ID    | Als …  | möchte ich …                                                                          | um …                                                               |
|-------|--------|---------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| US-01 | Boris  | beim `sdd spec approve` sofort sehen welche FRs keinen Test haben                    | Tests gezielt nachzutragen bevor ich implementiere                 |
| US-02 | Boris  | dass `sdd finalize` abbricht wenn ein FR-Test fehlt                                   | nie wieder eine Spec als `implemented` zu markieren die es nicht ist |
| US-03 | Boris  | dass `sdd validate` eine Spec mit `webui`-Tag ohne Integration-Test als Fehler meldet | UI-Specs immer mit Erreichbarkeits-Nachweis zu versehen            |
| US-04 | Boris  | nach einem Hotfix-Commit automatisch eine Warnung wenn betroffene Spec-Tests rot sind | Regressions wie in SPEC-0037 sofort zu erkennen                   |
| US-05 | Boris  | alle Checks einzeln in config.yaml deaktivieren können                                | die Einführung schrittweise vorzunehmen ohne bestehende Specs zu blockieren |

## 6. Nicht-funktionale Anforderungen

| Kategorie     | Anforderung                                                                                    |
|---------------|------------------------------------------------------------------------------------------------|
| Performance   | Vollständige Checker-Kette für eine Spec < 2 s (kein LLM-Aufruf, nur statische Analyse)       |
| Rückwärtskomp.| Alle Checks per config.yaml deaktivierbar — keine bestehende Spec wird rückwirkend blockiert  |
| Verständlichkeit | Fehlermeldungen nennen konkret: welches FR, welcher Test fehlt, welcher Befehl hilft       |
| Testbarkeit   | Jeder Checker hat eigene Unit-Tests mit Fixtures für compliant/non-compliant Specs             |

## 7. Contracts

*(werden in Phase contracts-proposed ergänzt)*

## 8. Tests

*(werden in Phase contracts-proposed ergänzt)*

## 9. Implementierungsreihenfolge

1. `FrCoverageSpecification` — FR-Extraktion + Task-Mapping (FR-01, FR-02)
2. `FrCoverageChecker` — Wrapper als ComplianceChecker (FR-01, FR-02)
3. Unit-Tests `FrCoverageSpecification` — compliant/non-compliant Fixtures
4. `TypeAwareTestChecker` — Tag-Check + Stufen-Check (FR-03)
5. Unit-Tests `TypeAwareTestChecker`
6. `RouteRegistrationChecker` — grep-basiert auf main.py (FR-04)
7. Unit-Tests `RouteRegistrationChecker`
8. Enforcement in `spec_approve` (FR-05)
9. Enforcement in `sdd finalize` (FR-06)
10. Enforcement in `sdd validate` (FR-07)
11. Contract-Tests für alle drei Enforcement-Punkte
12. Post-Commit-Hook + `sdd install-hooks` Erweiterung (FR-08)
13. Konfigurationsschema `compliance:` (FR-09)

## 10. Offene Fragen

- [x] Wie wird das FR→Test-Mapping für ältere Specs ohne `test_ids` in den
      Task-JSONs gehandhabt? → **Option B:** Nur Specs mit Status `draft`/`approved`
      unterliegen dem neuen Gate — `implemented`-Specs sind ausgenommen.
      Entspricht dem Nicht-Ziel „kein rückwirkendes Enforcement".
- [x] Soll FR-04 (Route-Registrierungs-Check) auch für Hub-Projekte greifen
      die `web/api/main.py` statt `tool/sdd_cli/web/api/main.py` nutzen?
      → **Ja, konfigurierbar** via `compliance.route_entry_points` als Liste
      von Pfaden relativ zum Projekt-Root.
- [x] Soll der Post-Commit-Hook bei Fehler den Commit blockieren (blocking)
      oder nur warnen (non-blocking)? → **Blocking** — der Commit wird
      abgebrochen wenn betroffene Spec-Tests rot sind. Hotfixes können mit
      `git commit --no-verify` überbrückt werden (explizites Opt-out).

## 11. Änderungshistorie

| Datum      | Version | Autor     | Änderung            |
|------------|---------|-----------|---------------------|
| 2026-06-09 | 0.1.0   | borisbrue | Initiale Erstellung |
