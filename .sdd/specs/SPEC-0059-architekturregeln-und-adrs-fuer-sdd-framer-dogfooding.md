---
id: SPEC-0059
title: "Architekturregeln und ADRs für sdd-framer (Dogfooding)"
type: feature
status: approved
owner: "Boris"
created: 2026-09-25
updated: 2026-09-25
version: 0.2.0
priority: medium
tags: [architecture, adr, dogfooding, quality]
depends_on: [SPEC-0054, SPEC-0053, SPEC-0060]
contracts: [CON-0208, CON-0209]
tests: [TST-0237, TST-0238]
fr_test_map:
  FR-01: [TST-0238]
  FR-02: [TST-0238]
  FR-03: [TST-0238]
  FR-04: [TST-0238]
  FR-05: [TST-0238]
  FR-06: [TST-0238]
  FR-07: [TST-0237, TST-0238]
  FR-08: [TST-0238]
---

# Architekturregeln und ADRs für sdd-framer (Dogfooding)

> **Status:** draft · **Owner:** Boris · **Version:** 0.2.0

## 1. Kontext & Motivation

SPEC-0054 führt `sdd quality measure`, `sdd arch check` und die Bindung von Architekturregeln an
ADRs ein. sdd-framer selbst beschreibt seine Architektur bisher nur als Prosa in AGENTS.md:

- Web/UI → CLI → Filesystem.
- „Die CLI ist der einzige Schreiber auf dem Filesystem.“
- Taste Invariant „CLI als einziger Filesystem-Schreiber“.

Maschinell geprüft wird davon nichts. `docs/adr/` enthält nur das Blueprint-Beispiel ADR-0001
(Brute-Force-Schutz), keine Entscheidung über sdd-framer selbst. Die Konsolidierung (SPEC-0058) und
die Rollen-Pipeline (SPEC-0053) brauchen eine Absicherung, dass die bereinigte Struktur nicht wieder
zerfällt, z. B. dass LLM-Zugriffe nur über die Factory laufen.

Ein Probelauf der Regeln auf `main` (nach SPEC-0053/0060, 2026-09-25) hat gezeigt:

- Alle Schreibzugriffe im Code haben variable Ziele (`md.write_text(...)`). Der Extraktor meldet sie
  als unaufgelöst, `write_ownership` überspringt sie. Eine Regel „nur die CLI schreibt“ wäre blind,
  obwohl die Web-API heute selbst Specs schreibt (`web/api/routes/specs.py`).
- `main.py` startet als Einstiegspunkt Web, Hub und PWA; `llm/` nutzt `config`. Eine strikte
  Schichtung `web → cli → llm` ohne Einstiegs- und Basisschicht meldet diese Strukturen als Verstoß.
- `claude` wird immer über eine Variable gestartet; erkennbar ist nur `shutil.which("claude")`.
- SPEC-0053 hat zwei Verstöße eingeführt: `pipeline/providers.py` baut Provider selbst, und
  `openai_compat.py` importiert `pipeline.path_policy`.

## 2. Zielsetzung

**Primärziel:** sdd-framer hält seine Architekturentscheidungen als ADRs fest und prüft ihre Folgen
bei jedem Lauf maschinell. Bekannte Altlasten sind sichtbar, blockieren aber nicht.

**Erfolgskriterien (messbar):**
- [ ] Für jede Regel ARCH-01 bis ARCH-04 existiert ein ADR mit Status `accepted` und
      `enforced_by`. `sdd validate` meldet keine ADR-Verknüpfungsfehler.
- [ ] `sdd arch check` ist auf `main` grün (Exit 0): Alle bestehenden Verstöße stehen in der
      Baseline, und ein neu eingebauter Verstoß führt zu Exit 1.
- [ ] Die Baseline enthält für ARCH-03 keinen Eintrag; die Verstöße aus SPEC-0053 sind behoben.
- [ ] `sdd quality measure` läuft auf sdd-framer ohne `n/a` bei den Sonden `tests`, `lint` und
      `deps`.

**Nicht-Ziele (explizit):**
- Keine Behebung der Altlasten außerhalb der eigenen Verstöße aus SPEC-0053 (FR-08); `local_agent.py`
  und der Task-Loop folgen mit SPEC-0058, die direkten Schreibzugriffe der Web-API mit einer eigenen
  Spec.
- Keine Regeln für die VS-Code-Extension (nicht mehr im Fokus).
- Keine Regel für „IDs nur über die CLI“; das bleibt eine Prozessregel in AGENTS.md.

## 3. Architektur & Design Patterns

Die Spec liefert überwiegend Daten für SPEC-0054: `.sdd/architecture.yaml`, `.sdd/quality.yaml`,
ADRs und die Baseline. Neu ist nur die Option `unresolved: violation` für `write_ownership` (FR-07).

Angenommene Patterns (Wiederverwendung, keine neuen Mechanismen):
- **Strategy** (SPEC-0054): jede Regel bildet über `kind` auf eine bestehende Strategie ab; FR-07
  erweitert die Strategie `write_ownership`, keine neue Regelart.
- **Factory Method** (SPEC-0060): ARCH-03/ARCH-04 sichern ab, dass nur die Factory Provider erzeugt.
- **Template Method** (SPEC-0054): das Sonden-Skelett des Presets bleibt; angepasst werden nur Pfade
  und Ausschlüsse.
- **Decorator** (SPEC-0054 FR-07): die Baseline liegt als Schicht um das Regelergebnis.

## 4. Funktionale Anforderungen

- **FR-01:** Es werden vier ADRs über `sdd new adr` angelegt, jede mit Status `accepted`, Bezug
  auf AGENTS.md und `enforced_by`:
  - „CLI ist einziger Schreiber für SDD-Artefakte“ → ARCH-01.
  - „Schichtrichtung Einstieg → Web/UI/PWA/Hub → CLI → LLM → Core“ → ARCH-02.
  - „LLM-Zugriff nur über die Provider-Factory“ → ARCH-03.
  - „Claude-CLI wird nur im Provider `claude_cli` aufgelöst“ → ARCH-04.
- **FR-02:** `.sdd/architecture.yaml` definiert die Schichten in dieser Reihenfolge (die erste
  passende gewinnt):
  - `entry`: `tool/sdd_cli/main.py`, `tool/sdd_cli/*_cli.py` (Kompositionswurzel, darf alles);
  - `core`: `tool/sdd_cli/config.py`, `tool/sdd_cli/frontmatter.py`,
    `tool/sdd_cli/quality/files.py`, `tool/sdd_cli/pipeline/path_policy.py`;
  - `web` (`tool/sdd_cli/web/api/**`), `ui` (`tool/sdd_cli/ui.py`, `tool/sdd_cli/web/ui/**`),
    `pwa` (`tool/sdd_cli/web/pwa/**`), `hub` (`tool/sdd_cli/hub/**`), `llm` (`tool/sdd_cli/llm/**`);
  - `cli`: übrige Module unter `tool/sdd_cli/`.

  Regeln:
  - **ARCH-01** `write_ownership` mit `unresolved: violation`: Schreibzugriffe auf `.sdd/**` und
    `docs/adr/**` nur aus `cli` und `entry`; ein Schreibzugriff mit unaufgelöstem Ziel aus einer
    anderen Schicht gilt als Verstoß.
  - **ARCH-02** `allowed_dependencies`: `entry → alle`; `web|ui|pwa|hub → cli, llm, core`;
    `cli → llm, core`; `llm → core`; `core → –`.
  - **ARCH-03** `forbidden_dependency`: Nichts außerhalb von `tool/sdd_cli/llm/**` importiert aus
    `tool/sdd_cli/llm/providers/**`.
  - **ARCH-04** `forbidden_call`: `shutil.which` mit dem Argument `claude` nur in
    `tool/sdd_cli/llm/providers/claude_cli.py`.
- **FR-03:** `.sdd/quality.yaml` wird mit `sdd quality init --preset python` erzeugt und an
  sdd-framer angepasst: `paths` auf `tool/**/*.py`, Testpfade, `.venv/bin/`-Präfix, Ausschlüsse
  (`vscode-extension/`, `node_modules/`, `web/ui/dist/`).
- **FR-04:** `.sdd/quality/arch-baseline.json` wird mit `sdd arch check --write-baseline` erzeugt.
  Jeder Eintrag bekommt einen Grund und, wo eine Spec ihn behebt, `fixed_by` (`local_agent.py` →
  SPEC-0058; `llm/usage.py → estimation` → SPEC-0058). Direkte Schreibzugriffe der Web-API bleiben
  ohne `fixed_by` mit dem Grund „Web-API schreibt direkt; Behebung offen“.
- **FR-05:** Die Taste Invariant „CLI als einziger Filesystem-Schreiber“ in AGENTS.md verweist auf
  `[ARCH-01]`. AGENTS.md bekommt im Abschnitt „Architektur“ einen Verweis auf die vier ADRs und den
  Hinweis, dass ein Commit am Pre-Commit-Hook (`sdd arch check`) scheitern kann.
- **FR-06:** Der Pre-Commit-Hook (`sdd install-hooks`) führt `sdd arch check` aus, wenn
  `.sdd/architecture.yaml` existiert und `.py`-Dateien gestaged sind; Exit 1 blockiert den Commit.
  `quality.arch_pre_commit: false` schaltet das ab. Der Hook erweitert CON-0155 (Reihenfolge und
  Exit-Verhalten in CON-0209).
- **FR-07:** Erweiterung von SPEC-0054 (CON-0194): Eine Regel `write_ownership` akzeptiert
  `unresolved: skip | violation` (Default `skip`, bisheriges Verhalten). Bei `violation` ist jeder
  Schreibzugriff mit unaufgelöstem Ziel aus einer Schicht außerhalb von `owners` ein Verstoß; das
  Symbol ist die Schreibfunktion (z. B. `pathlib.Path.write_text`). `sdd arch check` zeigt bei
  Baseline-Treffern `fixed_by` an (`warn (Baseline, SPEC-0058)`).
- **FR-08:** Die Verstöße aus SPEC-0053 werden behoben: Die Factory bietet
  `get_role_provider(config, binding)` und baut Provider je Rolle; `pipeline/providers.py`
  importiert nichts mehr aus `llm/providers/**`. `pipeline/path_policy.py` liegt in der Schicht
  `core` und importiert nur `core`.

## 5. Nicht-funktionale Anforderungen

| Kategorie   | Anforderung                                                          |
|-------------|----------------------------------------------------------------------|
| Laufzeit    | `sdd arch check` auf sdd-framer unter 10 s.                          |
| Wartbarkeit | Jede neue Architekturentscheidung mit maschineller Folge bekommt ADR und Regel im selben PR. |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Architekturregeln für sdd-framer

  Scenario: Main ist grün trotz Altlasten
    Given die Baseline enthält den Verstoß ARCH-04 in tool/sdd_cli/local_agent.py
    When ich "sdd arch check" auf main ausführe
    Then ist der Exit-Code 0
    And die Ausgabe listet ARCH-04 in local_agent.py als Baseline-Treffer mit SPEC-0058

  Scenario: Neuer Verstoß blockiert
    Given tool/sdd_cli/web/api/routes/new.py importiert tool/sdd_cli/llm/providers/openai_compat.py
    When ich "sdd arch check" ausführe
    Then ist der Exit-Code 1
    And die Ausgabe nennt ARCH-03 und das zugehörige ADR

  Scenario: Unaufgelöster Schreibzugriff aus der Web-API
    Given tool/sdd_cli/web/api/routes/new.py schreibt mit Path(ziel).write_text(...)
    When ich "sdd arch check" ausführe
    Then ist der Exit-Code 1
    And die Ausgabe nennt ARCH-01 und pathlib.Path.write_text

  Scenario: Ohne Option bleibt write_ownership beim alten Verhalten
    Given eine Regel write_ownership ohne unresolved
    When eine Datei außerhalb der owners mit unaufgelöstem Ziel schreibt
    Then meldet die Regel keinen Verstoß
```

## 7. Edge Cases & Fehlerfälle

- Lokale Importe in Funktionen (in sdd-framer häufig) zählen wie Modulimporte; das stellt der
  Extraktor aus dem Preset sicher.
- `tool/sdd_cli/web/api/` hat eigene venv-Pfade: Ausschlüsse in `quality.yaml` verhindern
  Fehlbefunde aus `site-packages`.
- Verfügbarkeitsprüfungen der Web-API (`shutil.which("claude")` in `routes/commands.py`,
  `routes/orchestrate.py`) sind ARCH-04-Treffer; sie kommen in die Baseline mit `fixed_by: SPEC-0058`.
- Der Pre-Commit-Hook ohne `.sdd/architecture.yaml` ändert sein Verhalten nicht.

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert?                                   |
|-------------|----------|--------------------------------------------------------|
| CON-0208    | data     | Erweiterung von CON-0194: `write_ownership.unresolved` |
| CON-0209    | behavior | `sdd arch check` auf sdd-framer, Pre-Commit-Hook (Gherkin aus Abschnitt 6) |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level       | Was prüft der Test?                                        |
|----------|-------------|------------------------------------------------------------|
| TST-0237 | unit        | Schema und Strategie `write_ownership` mit `unresolved`    |
| TST-0238 | acceptance  | Gherkin-Szenarien (Repo-Stand und temporäre Kopie), Pre-Commit-Hook |

## 10. Offene Fragen

- [x] Baseline-Mechanik → Kern von SPEC-0054 (FR-07), weil jedes Projekt mit Altlasten sie
      braucht (entschieden 2026-09-25).
- [x] ARCH-01 bei variablen Schreibzielen → `unresolved: violation` (FR-07), entschieden 2026-09-25.
- [x] Schichten `entry` und `core` statt großer Baseline (entschieden 2026-09-25).
- [x] Eigene Verstöße aus SPEC-0053 werden hier behoben (FR-08), entschieden 2026-09-25.
- [ ] Welche Spec übernimmt die direkten Schreibzugriffe der Web-API (Delegation an die CLI)?

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung                                    |
|------------|---------|---------------|---------------------------------------------|
| 2026-09-25 | 0.1.0   | Boris, Claude | Aus SPEC-0054 FR-14 (0.4.0) ausgelagert     |
| 2026-09-25 | 0.2.0   | Boris, Claude | Review nach Probelauf: ARCH-01 mit `unresolved`, Schichten `entry`/`core`, ARCH-04 über `shutil.which`, FR-07/FR-08, Pre-Commit-Hook |
