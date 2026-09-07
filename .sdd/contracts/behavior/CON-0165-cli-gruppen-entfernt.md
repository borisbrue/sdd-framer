---
id: CON-0165
project: PRJ-0001
title: "CLI-Gruppen `pattern` und `dev` entfernt"
type: behavior
format: markdown
spec: SPEC-0044
version: 0.1.0
status: approved
artifact: "contracts/behavior/cli-gruppen-entfernt.md"
tests:
  - TST-0193
---

# Contract: CLI-Gruppen `pattern` und `dev` entfernt

> **Spec:** SPEC-0044 · **Typ:** Verhalten · **Status:** draft

## Zweck

Garantiert, dass die CLI-Gruppen `sdd pattern` und `sdd dev` vollständig entfernt
werden, die Gruppen `sdd obsidian` und `sdd pwa` erhalten bleiben, und `CHANGELOG.md`
eine Migrationsnotiz enthält.

## Garantien

- `sdd pattern` und alle Unterkommandos (`pattern-suggest`, `pattern accept`,
  `pattern reject`, `pattern list`) sind nach dem Cleanup nicht mehr aufrufbar
- `sdd dev` und alle Unterkommandos (`start`, `exec`, `close`, `pr`, `build`,
  `push`, `up`, `down`) sind nach dem Cleanup nicht mehr aufrufbar
- `sdd obsidian` bleibt vollständig funktionsfähig
- `sdd pwa` bleibt vollständig funktionsfähig
- `DevContainerManager`-Modul bleibt als interne Dependency erhalten
- `CHANGELOG.md` enthält für jede entfernte Gruppe einen Migrationshinweis

## Invarianten

- Kein Aufruf von `sdd pattern *` oder `sdd dev *` darf mit Exit 0 enden
- `sdd --help` listet weder `pattern` noch `dev` als Gruppe auf
- Obsidian- und PWA-Tests bleiben grün

## Gherkin

```gherkin
Feature: CLI-Cleanup — pattern und dev Gruppen entfernt

  Scenario: sdd pattern liefert Fehler
    When ich `sdd pattern list` aufrufe
    Then endet der Prozess mit Exit-Code ungleich 0
    And die Fehlermeldung enthält "unbekannter Befehl"

  Scenario: sdd dev liefert Fehler
    When ich `sdd dev start` aufrufe
    Then endet der Prozess mit Exit-Code ungleich 0

  Scenario: sdd obsidian funktioniert noch
    When ich `sdd obsidian --help` aufrufe
    Then endet der Prozess mit Exit-Code 0

  Scenario: CHANGELOG enthält Migrationshinweis
    Given die Datei CHANGELOG.md existiert
    Then enthält sie den Text "pattern" im Kontext einer Entfernung
    And enthält sie den Text "dev" im Kontext einer Entfernung
```

## LLM Review Notes

Der Contract ist inhaltlich sinnvoll, aber in vier Punkten nicht abnahmefähig:

1. **Status-Widerspruch:** Frontmatter sagt `status: approved`, der Body-Header `**Status:** draft`. Eine der beiden Angaben ist falsch.
2. **Kaputte Rückverlinkung:** Der Contract referenziert `spec: SPEC-0044`, aber SPEC-0044 listet unter `contracts:` nur CON-0169/CON-0170 und unter `tests:` nur TST-0201/TST-0202. Weder CON-0165 noch das hier deklarierte TST-0193 tauchen dort auf — die Traceability-Matrix bricht.
3. **Nicht verifizierbare Assertion in der Gherkin-Datei:** `And die Fehlermeldung enthält "unbekannter Befehl"` ist gegen die reale Implementierung falsch. Die CLI ist eine Click-Gruppe (`sdd_cli.main.cli`); Click gibt englisch `Error: No such command 'pattern'.` mit Exit-Code 2 aus. Die Garantie muss entweder auf den tatsächlichen Text/Exit-Code 2 umformuliert oder auf „Gruppe nicht in `cli.commands` registriert" abstrahiert werden.
4. **Unmessbare Garantien ohne Szenario:**
   - „`sdd obsidian`/`sdd pwa` bleiben *vollständig funktionsfähig*" — nur `obsidian --help` ist abgedeckt, für `pwa` existiert gar kein Szenario; „vollständig" ist kein prüfbares Kriterium (Vorschlag: konkrete Subcommand-Liste einfrieren).
   - „`DevContainerManager`-Modul bleibt als interne Dependency erhalten" — keinerlei Szenario; muss als Import-/Nutzungsassertion formuliert werden (`from sdd_cli.dev_container import DevContainerManager` importierbar).
   - „`CHANGELOG.md` enthält den Text `dev` im Kontext einer Entfernung" — `dev` ist ein triviales Substring-Match; „im Kontext einer Entfernung" ist nicht operationalisiert. Vorschlag: Pflicht auf eine `### Removed`-Sektion, die die Zeichenketten `sdd pattern` und `sdd dev` enthält.
   - Invariante „Obsidian- und PWA-Tests bleiben grün" nennt keine Testdateien.

Zusätzlich ambig (aus der Spec geerbt): Die Subcommand-Liste mischt `pattern-suggest` (Top-Level-Schreibweise) mit `pattern accept/reject/list` (Gruppen-Schreibweise). Der Contract sollte festlegen, ob beide Formen verschwinden. Ebenfalls offen ist Spec-Frage 9.4 (Deprecation-Aliases vs. Hard-Cut) — der Contract setzt implizit den Hard-Cut, ohne das zu benennen.

## LLM Review Notes

Die Substanz stimmt — die Implementierung erfüllt die Garantien bereits (verifiziert: `pattern`/`dev` sind nicht in `cli.commands`, `obsidian`/`pwa` sind registriert, `CHANGELOG.md` hat eine `### Removed`-Sektion mit beiden Migrationshinweisen). Abnahmefähig ist der Contract trotzdem nicht:

1. **Status-Widerspruch:** Frontmatter `status: approved` vs. Body-Header `**Status:** draft`. Genau eine Angabe ist gültig — bei `approved` muss der Body nachgezogen werden.
2. **Traceability gebrochen:** SPEC-0044 listet unter `contracts:` nur CON-0169/CON-0170 und unter `tests:` nur TST-0201/TST-0202. `.sdd/contracts/behavior/CON-0165-cli-gruppen-entfernt.md` und `.sdd/tests/integration/TST-0193-cli-gruppen-entfernt.md` existieren, sind aber in der Spec nicht eingetragen. Beide IDs müssen in die Spec-Frontmatter, sonst bricht `sdd trace`.
3. **Falsche Assertion im Gherkin:** `And die Fehlermeldung enthält "unbekannter Befehl"` ist gegen die Implementierung falsch. Verifiziert: Click gibt `Error: No such command 'pattern'.` mit **Exit-Code 2** aus. Das Szenario würde garantiert rot. Umformulieren auf Exit-Code 2 + `"No such command"` oder besser auf die implementierungsnahe Assertion `"pattern" not in cli.commands` abstrahieren.
4. **Unmessbare Garantien:**
   - „`obsidian`/`pwa` bleiben *vollständig funktionsfähig*" — für `pwa` existiert kein Szenario; „vollständig" ist nicht prüfbar. Vorschlag: Subcommand-Liste einfrieren (`pwa` hat aktuell genau `start`).
   - „`DevContainerManager` bleibt interne Dependency" — kein Szenario. Als Import-Assertion formulieren.
   - „`CHANGELOG.md` enthält den Text `dev`" — triviales Substring-Match. Vorschlag: Pflicht auf eine `### Removed`-Sektion, die die Literale `sdd pattern` und `sdd dev` enthält (so ist es faktisch bereits umgesetzt).
   - Invariante „Obsidian- und PWA-Tests bleiben grün" nennt keine Testdateien.
5. **Artefakt-Pfad falsch:** Frontmatter sagt `artifact: "contracts/behavior/cli-gruppen-entfernt.md"`, die Datei liegt unter `.sdd/contracts/behavior/CON-0165-cli-gruppen-entfernt.md` (mit ID-Präfix).
6. **Aus der Spec geerbte Ambiguität:** Die Subcommand-Liste mischt `pattern-suggest` (Top-Level) mit `pattern accept/reject/list` (Gruppe). Beide Formen sind faktisch entfernt und im CHANGELOG separat gelistet — der Contract sollte das explizit machen. Ebenso setzt er implizit den Hard-Cut, obwohl Spec-Frage 9.4 (Deprecation-Aliases) offen ist; entweder Frage schließen oder im Contract benennen.

## LLM Review Notes

Die Substanz des Contracts ist korrekt und die Implementierung erfüllt sie bereits (verifiziert: `pattern`/`dev` fehlen in `cli.commands`, `obsidian` (`export/import/watch`) und `pwa` (`start`) sind registriert, `from sdd_cli.dev_container import DevContainerManager` funktioniert, `CHANGELOG.md` hat eine `### Removed`-Sektion mit beiden Migrationshinweisen inkl. `pattern-suggest`). Abnahmefähig ist der Contract dennoch nicht:

1. **Status-Widerspruch:** Frontmatter `status: approved` vs. Body-Header `**Status:** draft`. Genau eine Angabe darf gelten — bei `approved` muss der Body nachgezogen werden.
2. **Traceability gebrochen:** SPEC-0044 listet unter `contracts:` nur CON-0169/CON-0170, unter `tests:` nur TST-0201/TST-0202. CON-0165 und das im Contract deklarierte TST-0193 fehlen dort → `sdd trace` bricht. Beide IDs in die Spec-Frontmatter eintragen.
3. **Falsche Assertion im Gherkin:** `And die Fehlermeldung enthält "unbekannter Befehl"` ist gegen die Implementierung falsch — verifiziert liefert Click `Error: No such command 'pattern'.` bei **Exit-Code 2**. Das Szenario wäre garantiert rot. Auf Exit-Code 2 + `"No such command"` umformulieren oder implementierungsnah auf `"pattern" not in cli.commands` abstrahieren.
4. **Unmessbare Garantien ohne Szenario:**
   - „`obsidian`/`pwa` bleiben *vollständig funktionsfähig*" — für `pwa` existiert kein Szenario, „vollständig" ist kein prüfbares Kriterium. Subcommand-Listen einfrieren: `obsidian` = `{export, import, watch}`, `pwa` = `{start}`.
   - „`DevContainerManager` bleibt interne Dependency" — kein Szenario; als Import-Assertion auf `sdd_cli.dev_container` formulieren.
   - „`CHANGELOG.md` enthält den Text `dev`" — triviales Substring-Match, „im Kontext einer Entfernung" ist nicht operationalisiert. Pflicht auf eine `### Removed`-Sektion mit den Literalen `sdd pattern` und `sdd dev` (so faktisch bereits umgesetzt).
   - Invariante „Obsidian- und PWA-Tests bleiben grün" nennt keine Testdateien/Testpfade.
5. **Artefakt-Pfad falsch:** Frontmatter sagt `contracts/behavior/cli-gruppen-entfernt.md`, die Datei liegt unter `.sdd/contracts/behavior/CON-0165-cli-gruppen-entfernt.md` (mit ID-Präfix).
6. **Geerbte Ambiguität:** Die Subcommand-Liste mischt `pattern-suggest` (Top-Level) mit `pattern accept/reject/list` (Gruppe). Beide Formen sind faktisch entfernt und im CHANGELOG separat gelistet — der Contract muss das explizit machen. Zudem setzt er implizit den Hard-Cut, obwohl Spec-Frage 9.4 (Deprecation-Aliases) offen ist: Frage schließen oder Hard-Cut im Contract benennen.

## LLM Review Notes

Die Substanz ist korrekt und die Implementierung erfüllt die Garantien bereits (verifiziert: `pattern`/`dev` fehlen in `cli.commands`; `obsidian` = `{export, import, watch}`, `pwa` = `{start}` sind registriert; `from sdd_cli.dev_container import DevContainerManager` funktioniert; `CHANGELOG.md` hat eine `### Removed`-Sektion mit beiden Migrationshinweisen inkl. `pattern-suggest` und `implement`). Abnahmefähig ist der Contract dennoch nicht:

1. **Status-Widerspruch:** Frontmatter `status: approved` vs. Body-Header `**Status:** draft`. Genau eine Angabe darf gelten — bei `approved` den Body nachziehen.
2. **Traceability gebrochen:** SPEC-0044 listet unter `contracts:` nur CON-0169/CON-0170, unter `tests:` nur TST-0201/TST-0202. `.sdd/contracts/behavior/CON-0165-cli-gruppen-entfernt.md` und `.sdd/tests/integration/TST-0193-cli-gruppen-entfernt.md` existieren, fehlen aber in der Spec-Frontmatter → `sdd trace` bricht. Beide IDs eintragen.
3. **Falsche Assertion im Gherkin:** `And die Fehlermeldung enthält "unbekannter Befehl"` ist gegen die Implementierung falsch. Verifiziert liefert Click `Error: No such command 'pattern'.` bei **Exit-Code 2**. Das Szenario wäre garantiert rot. Auf Exit-Code 2 + `"No such command"` umformulieren oder implementierungsnah auf `"pattern" not in cli.commands` abstrahieren.
4. **Unmessbare Garantien ohne Szenario:**
   - „`obsidian`/`pwa` bleiben *vollständig funktionsfähig*" — für `pwa` existiert kein Szenario; „vollständig" ist kein prüfbares Kriterium. Subcommand-Listen einfrieren: `obsidian` = `{export, import, watch}`, `pwa` = `{start}`.
   - „`DevContainerManager` bleibt interne Dependency" — kein Szenario; als Import-Assertion auf `sdd_cli.dev_container` formulieren.
   - „`CHANGELOG.md` enthält den Text `dev`" — triviales Substring-Match, „im Kontext einer Entfernung" ist nicht operationalisiert. Pflicht auf eine `### Removed`-Sektion mit den Literalen `sdd pattern` und `sdd dev` (so faktisch bereits umgesetzt).
   - Invariante „Obsidian- und PWA-Tests bleiben grün" nennt keine Testdateien/Testpfade.
5. **Artefakt-Pfad falsch:** Frontmatter sagt `contracts/behavior/cli-gruppen-entfernt.md`, die Datei liegt unter `.sdd/contracts/behavior/CON-0165-cli-gruppen-entfernt.md` (mit ID-Präfix).
6. **Geerbte Ambiguität:** Die Subcommand-Liste mischt `pattern-suggest` (Top-Level) mit `pattern accept/reject/list` (Gruppe). Beide Formen sind faktisch entfernt und im CHANGELOG separat gelistet — der Contract muss das explizit machen. Zudem setzt er implizit den Hard-Cut, obwohl Spec-Frage 9.4 (Deprecation-Aliases) offen ist: Frage schließen oder Hard-Cut im Contract benennen.
