---
id: SPEC-0059
title: "Architekturregeln und ADRs für sdd-framer (Dogfooding)"
type: feature
status: draft
owner: "Boris"
created: 2026-09-25
updated: 2026-09-25
version: 0.1.0
priority: medium
tags: [architecture, adr, dogfooding, quality]
depends_on: [SPEC-0054]
contracts: []
tests: []
---

# Architekturregeln und ADRs für sdd-framer (Dogfooding)

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

SPEC-0054 führt `sdd quality measure`, `sdd arch check` und die Bindung von Architekturregeln an
ADRs ein. sdd-framer selbst beschreibt seine Architektur bisher nur als Prosa in AGENTS.md:

- Web/UI → CLI → Filesystem.
- „Die CLI ist der einzige Schreiber auf dem Filesystem.“
- Taste Invariant „CLI als einziger Filesystem-Schreiber“.

Maschinell geprüft wird davon nichts. `docs/adr/` enthält nur das Blueprint-Beispiel ADR-0001
(Brute-Force-Schutz), keine Entscheidung über sdd-framer selbst. Die Konsolidierung (SPEC-0058) und
die Rollen-Pipeline (SPEC-0053) brauchen aber eine Absicherung, dass die bereinigte Struktur nicht
wieder zerfällt, z. B. dass LLM-Zugriffe nur über die Factory laufen.

Diese Spec wendet SPEC-0054 auf das eigene Repo an. Sie steht getrennt, weil sie sich unabhängig
von der Messlogik ändert: neue Regeln, neue ADRs, eine kleiner werdende Baseline.

## 2. Zielsetzung

**Primärziel:** sdd-framer hält seine Architekturentscheidungen als ADRs fest und prüft ihre Folgen
bei jedem Lauf maschinell. Bekannte Altlasten sind sichtbar, blockieren aber nicht.

**Erfolgskriterien (messbar):**
- [ ] Für jede Startregel existiert ein ADR mit Status `accepted` und `enforced_by`.
      `sdd validate` meldet keine ADR-Verknüpfungsfehler.
- [ ] `sdd arch check` ist auf `main` grün (Exit 0): Alle bestehenden Verstöße stehen in der
      Baseline, und ein neu eingebauter Verstoß führt zu Exit 1.
- [ ] `sdd quality measure` läuft auf sdd-framer mit dem Preset `python` ohne `n/a` bei den Sonden
      `tests`, `lint` und `deps`.
- [ ] Die Baseline enthält mindestens die bekannten Verstöße aus `decompose.py` und
      `local_agent.py`. Nach Umsetzung von SPEC-0053/SPEC-0058 ist sie für die Regeln ARCH-03 und
      ARCH-04 leer.

**Nicht-Ziele (explizit):**
- Keine Behebung der Altlasten; das leisten SPEC-0053 und SPEC-0058.
- Keine Regeln für die VS-Code-Extension (nicht mehr im Fokus).
- Keine Regel für „IDs nur über die CLI“; das bleibt eine Prozessregel in AGENTS.md.

## 3. Architektur & Design Patterns

Keine neuen Mechanismen: Die Spec liefert ausschließlich Daten für SPEC-0054, also
`.sdd/architecture.yaml`, `.sdd/quality.yaml`, ADRs und die Baseline. Die Baseline-Mechanik selbst
ist Teil von SPEC-0054 FR-07.

## 4. Funktionale Anforderungen

- **FR-01:** Es werden vier ADRs über `sdd new adr` angelegt, jede mit Status `accepted`, Bezug
  auf AGENTS.md und `enforced_by`:
  - „CLI ist einziger Schreiber für SDD-Artefakte“ → ARCH-01.
  - „Schichtrichtung Web/UI/PWA → CLI → LLM“ → ARCH-02.
  - „LLM-Zugriff nur über die Provider-Factory“ → ARCH-03.
  - „Claude-CLI wird nur im Provider `claude_cli` gestartet“ → ARCH-04.
- **FR-02:** `.sdd/architecture.yaml` definiert die Schichten `web` (`tool/sdd_cli/web/**`), `ui`
  (`tool/sdd_cli/ui.py`), `pwa`, `hub` (`tool/sdd_cli/hub/**`), `llm` (`tool/sdd_cli/llm/**`) und
  `cli` (übrige Module unter `tool/sdd_cli/`). Dazu kommen die Regeln:
  - **ARCH-01** `write_ownership`: Schreibzugriffe auf `.sdd/specs/**`, `.sdd/contracts/**`,
    `.sdd/tests/**`, `docs/adr/**` nur aus der Schicht `cli`.
  - **ARCH-02** `allowed_dependencies`: `web|ui|pwa|hub → cli → llm`; keine Abhängigkeit von `cli`
    oder `llm` nach `web|ui|pwa|hub`.
  - **ARCH-03** `forbidden_dependency`: Nichts außerhalb von `tool/sdd_cli/llm/**` importiert aus
    `tool/sdd_cli/llm/providers/**`.
  - **ARCH-04** `forbidden_call`: `subprocess.*` mit dem Programm `claude` nur in
    `tool/sdd_cli/llm/providers/claude_cli.py`.
- **FR-03:** `.sdd/quality.yaml` wird mit `sdd quality init --preset python` erzeugt und an
  sdd-framer angepasst (Testpfade, `.venv/bin/`-Präfix, Ausschlüsse wie `vscode-extension/`).
- **FR-04:** `.sdd/quality/arch-baseline.json` wird beim Einführen mit
  `sdd arch check --write-baseline` erzeugt. Jeder Eintrag bekommt einen Grund und die Spec, die ihn beheben soll (z. B.
  `decompose.py` → SPEC-0053; `local_agent.py` → SPEC-0058).
- **FR-05:** Die Taste Invariant „CLI als einziger Filesystem-Schreiber“ in AGENTS.md verweist auf
  `[ARCH-01]`. AGENTS.md bekommt im Abschnitt „Architektur“ einen Verweis auf die vier ADRs.
- **FR-06:** Die GitHub-Action bzw. der Pre-Commit-Hook von sdd-framer führt `sdd arch check` aus.

## 5. Nicht-funktionale Anforderungen

| Kategorie   | Anforderung                                                          |
|-------------|----------------------------------------------------------------------|
| Laufzeit    | `sdd arch check` auf sdd-framer unter 10 s.                          |
| Wartbarkeit | Jede neue Architekturentscheidung mit maschineller Folge bekommt ADR und Regel im selben PR. |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Architekturregeln für sdd-framer

  Scenario: Main ist grün trotz Altlasten
    Given die Baseline enthält den Verstoß ARCH-03 in tool/sdd_cli/decompose.py
    When ich "sdd arch check" auf main ausführe
    Then ist der Exit-Code 0
    And die Ausgabe listet ARCH-03 in decompose.py als "warn (Baseline, SPEC-0053)"

  Scenario: Neuer Verstoß blockiert
    Given tool/sdd_cli/web/api/routes/new.py importiert tool/sdd_cli/llm/providers/openai_compat.py
    When ich "sdd arch check" ausführe
    Then ist der Exit-Code 1
    And die Ausgabe nennt ARCH-03 und das zugehörige ADR
```

## 7. Edge Cases & Fehlerfälle

- Lokale Importe in Funktionen (in sdd-framer häufig) zählen wie Modulimporte; das stellt der
  Extraktor aus dem Preset sicher.
- `tool/sdd_cli/web/api/` hat eigene venv-Pfade: Ausschlüsse in `quality.yaml` verhindern
  Fehlbefunde aus `site-packages`.

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert?                                   |
|-------------|----------|--------------------------------------------------------|
| –           | –        | Keine eigenen Contracts; es gelten die Contracts aus SPEC-0054. Die Spec liefert Daten (Regeln, ADRs, Baseline). |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level       | Was prüft der Test?                                        |
|----------|-------------|------------------------------------------------------------|
| TST-XXXX | integration | `sdd arch check` auf dem Repo-Stand: Exit 0, Baseline-Treffer |
| TST-XXXX | acceptance  | Gherkin-Szenarien aus Abschnitt 6 (mit temporärer Kopie)   |

## 10. Offene Fragen

- [x] Baseline-Mechanik → Kern von SPEC-0054 (FR-07), weil jedes Projekt mit Altlasten sie
      braucht (entschieden 2026-09-25).

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung                                    |
|------------|---------|---------------|---------------------------------------------|
| 2026-09-25 | 0.1.0   | Boris, Claude | Aus SPEC-0054 FR-14 (0.4.0) ausgelagert     |
