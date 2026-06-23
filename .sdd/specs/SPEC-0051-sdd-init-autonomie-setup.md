---
id: SPEC-0051
title: sdd init Autonomie-Setup – Guardrail standardmäßig, opt-in Bypass, Guardrail-Härtung
type: feature
status: in-progress
owner: Boris
created: 2026-06-23
updated: '2026-06-23'
version: 0.1.0
priority: medium
tags:
- sdd-init
- blueprint
- autonomy
- guardrail
- security
depends_on: []
contracts:
- CON-0188
- CON-0189
tests:
- TST-0214
- TST-0215
fr_test_map:
  FR-01:
  - TST-0214
  FR-02:
  - TST-0214
  FR-03:
  - TST-0214
  FR-04:
  - TST-0215
  FR-05:
  - TST-0215
  FR-06:
  - TST-0215
  FR-07:
  - TST-0215
  FR-08:
  - TST-0215
started_at: '2026-06-23T16:02:52Z'
---
# sdd init Autonomie-Setup – Guardrail standardmäßig, opt-in Bypass, Guardrail-Härtung

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Diese Session hat den autonomen Spec→PR-Flow etabliert: `permissions.defaultMode: bypassPermissions`
(Auto-Approve) plus ein `PreToolUse`/`Bash`-Guardrail-Hook, der katastrophale Kommandos blockt
(auch unter Bypass). Beides existiert aber **nur im sdd-framer-Projekt selbst**, nicht im Blueprint,
den `sdd init` in neue Projekte kopiert:

- `merge_claude_settings()` (`tool/sdd_cli/init.py`) merged ausschließlich `permissions.allow` aus
  `blueprint/templates/agents-md/providers/claude/settings.json` – **kein** `hooks`, **kein** `defaultMode`.
- Der Guardrail-Script `autonomous-guardrail.sh` liegt nicht im Blueprint.
- `sdd init` hat keinen Autonomie-Flag.

Zusätzlich **über-blockt der aktuelle Guardrail** (beim Dogfooding belegt):
1. Er unterscheidet *ausführen* vs. *erwähnen* nicht – eine Commit-Message mit `rm -rf /`-Text wurde blockiert.
2. Das Force-Flag-Regex `-[a-z]*f[a-z]*` ist zu breit – es matcht `--body-file` und hielt `gh pr create` für einen Force-Push.
3. Zusammengesetzte Kommandos kreuz-triggern – `git push … ; gh pr create --base main` wirkt wie Force-Push auf main.

Ohne Härtung würde dieser Über-Blocker in **jedes** init-Projekt ausgerollt.

## 2. Zielsetzung

**Primärziel:** `sdd init` rüstet neue Projekte sicher für autonomes Arbeiten aus – Guardrail
immer, Bypass nur auf ausdrücklichen Wunsch und nur persönlich (nie für Clones erzwungen) – und
der Guardrail blockt nur noch echte Gefahren.

**Erfolgskriterien (messbar):**
- [ ] `sdd init` legt `.claude/hooks/autonomous-guardrail.sh` im Zielprojekt an (aus Blueprint).
- [ ] `sdd init` merged den `PreToolUse`/`Bash`-Guardrail-Hook idempotent in `.claude/settings.json`
  (kein Doppeleintrag bei erneutem init), ohne die bestehende `allow`-Merge-Logik zu verändern.
- [ ] `sdd init --autonomous` schreibt `permissions.defaultMode: "bypassPermissions"` in
  `.claude/settings.local.json` und trägt `settings.local.json` in `.gitignore` ein; **ohne** Flag
  wird kein `defaultMode` gesetzt und keine committed-Datei verändert.
- [ ] Der Guardrail wertet jedes Kommando-**Segment** einzeln (Split an `;`, `&&`, `||`, `|`) und
  prüft das führende Kommando-Token – Erwähnungen in `-m`/`echo`/Argumenten lösen nicht mehr aus.
- [ ] Force-Push-Erkennung matcht nur echte Force-Flags (`--force`, `--force-with-lease`, isoliertes `-f`),
  nicht beliebige Flags mit „f" (`--body-file`, `--diff-filter`).
- [ ] Die geblockte Gefahren-Menge bleibt funktional unverändert; Alltagskommandos + die drei
  Dogfooding-False-Positives laufen jetzt durch.

**Nicht-Ziele (explizit):**
- Kein `bypassPermissions` in committed `.claude/settings.json` (bewusst nur `settings.local.json`).
- Keine Änderung am bypassPermissions-Mechanismus von Claude Code.
- Keine neuen Blockregeln im Guardrail – nur Härtung der bestehenden.
- Keine Änderung an den vom Blueprint gemergten `permissions.allow`-Einträgen.

## 3. Architektur-Entscheidungen & Design Patterns

### 3.1 Strategy Pattern (Behavioral)
**Anwendung:** Die Guardrail-Blockregeln werden als geordnete Liste unabhängiger Prüf-Einheiten
strukturiert (eine Funktion je Gefahrenklasse: force-push, remote-delete, rm-rf, disk-wipe,
net-pipe, chmod-root). Jede prüft ein Kommando-Segment und liefert optional einen Block-Grund.

**Begründung:** Neue/angepasste Regeln (z. B. die präzisere Force-Flag-Erkennung) lassen sich
isoliert testen und ändern, ohne die anderen anzufassen (OCP) – genau die Schwäche, die zum
Über-Blocken führte. Konsistent mit der Strategy-Nutzung in `routing.py`/`llm_probe.py`.

**Alternative:** Eine monolithische Regex-Kaskade (Status quo) – abgelehnt, weil ein zu breites
Teilmuster (`-[a-z]*f[a-z]*`) das Gesamtverhalten verfälscht und schwer testbar ist.

Quelle: https://refactoring.guru/design-patterns/strategy

### 3.2 Wiederverwendung der Merge-Mechanik (SOLID/DRY)
**Anwendung:** Der Hook-Merge erweitert die bestehende `merge_claude_settings()` um einen
zusätzlichen, additiv-idempotenten Abschnitt (`hooks`), statt eine zweite Settings-Schreibroutine
einzuführen. Die `--autonomous`-Logik schreibt isoliert in `settings.local.json`.

**Begründung:** Eine einzige Stelle bleibt für das Settings-Merging zuständig (SRP); die
Idempotenz-/Dedup-Garantie gilt einheitlich für `allow` und `hooks` (DRY).

**Alternative:** Separate Schreibpfade pro Settings-Abschnitt – abgelehnt (Duplikation, divergierende
Merge-Semantik).

Quelle: https://refactoring.guru/design-patterns/template-method

### 3.3 Facade Pattern (Structural)
**Anwendung:** `sdd init` (bzw. `sdd init --autonomous`) ist die eine Schnittstelle, hinter der das
mehrschrittige Autonomie-Setup orchestriert wird — Blueprint-Copy, Hook-Merge, optionaler
Local-Override. Die Subsysteme bleiben entkoppelt und einzeln testbar.

**Begründung:** Der Nutzer braucht ein Kommando, nicht das Wissen über drei Setup-Schritte (SRP für
den Aufrufer). Konsistent mit der akzeptierten Facade-Nutzung (SPEC-0049/0050).

**Alternative:** Command-Objekte je Setup-Schritt – abgelehnt, da weder Undo/Audit noch
Serialisierung gebraucht werden und das die lineare init-Sequenz unnötig verkompliziert.

Quelle: https://refactoring.guru/design-patterns/facade

### 3.4 Guardrail als testbares Modul (löst die DIP-Spannung, OQ-03)
Die Guardrail-Block-Policy wandert aus dem Bash-Script in ein `sdd_cli`-Modul (`guard.py`): die
Block-Regeln sind Strategy-Einheiten, ihre geordnete „erste-passende-Regel-gewinnt"-Auswertung ist
eine **Chain of Responsibility**. Der Hook wird ein dünner Wrapper (`sdd guard check`). Damit hängt
das High-Level-Verhalten (testbare Regeln) nicht mehr an einem Low-Level-Bash-Regex (DIP), und die
Subprocess-Abhängigkeit wird durch echte Unit-Tests ersetzt. Trade-off: der Hook braucht ein
verfügbares `sdd` (FR-08 regelt die sichere Degradierung).

Quelle: https://refactoring.guru/design-patterns/chain-of-responsibility

## 4. Funktionale Anforderungen

- **FR-01:** `sdd init` kopiert `autonomous-guardrail.sh` aus dem Blueprint nach
  `.claude/hooks/autonomous-guardrail.sh` (ausführbar) des Zielprojekts.
- **FR-02:** `merge_claude_settings()` merged den `PreToolUse`/`Bash`-Guardrail-Hook additiv und
  idempotent in `.claude/settings.json` (Dedup über das Hook-Command/Script), ohne die `allow`-Merge-
  Logik zu verändern.
- **FR-03:** `sdd init --autonomous` setzt `permissions.defaultMode: "bypassPermissions"` in
  `.claude/settings.local.json` (Datei anlegen falls fehlend) und ergänzt `settings.local.json` in
  `.gitignore`. Ohne Flag bleibt `settings.local.json`/`defaultMode` unangetastet.
- **FR-04:** Der Guardrail zerlegt das Kommando an `;`, `&&`, `||`, `|` in Segmente und bewertet je
  Segment das führende Kommando-Token; Gefahrenmuster in Argumenten/Strings (`-m`, `echo`, Doku)
  lösen keinen Block aus.
- **FR-05:** Die Force-Push-Regel matcht ausschließlich echte Force-Flags (`--force`,
  `--force-with-lease`, isoliertes `-f`), nicht beliebige „f"-haltige Flags.
- **FR-06:** Die geblockte Gefahren-Menge (force-push main/master, remote-main löschen, `rm -rf`
  auf Root/Home/Parent, Disk-Wipe, Net-Pipe-to-Shell, `chmod/chown -R /`) bleibt unverändert;
  Alltags- und Erwähnungs-Kommandos laufen durch.
- **FR-07:** Die Guardrail-Logik liegt in einem testbaren `sdd_cli`-Modul (Block-Regeln als
  Strategy, geordnete Auswertung als Chain of Responsibility). Der `.claude/hooks/`-Hook ist ein
  dünner Wrapper, der das Modul aufruft (z. B. `sdd guard check`) und dessen Block-Entscheidung
  als `permissionDecision` weiterreicht.
- **FR-08:** Ist das Modul/`sdd` für den Hook nicht erreichbar, degradiert der Wrapper **sicher
  sichtbar**: er erlaubt das Kommando (bricht die Shell nicht), gibt aber einen `[WARN] Guardrail
  inaktiv`-Hinweis aus — der Nutzer hat Bypass bewusst gewählt, ein Hard-Block aller Kommandos wäre
  schlimmer als der temporäre Schutzverlust.

## 5. User Stories

| ID    | Als ...        | möchte ich ...                                                           | um ...                                                  |
|-------|----------------|----------------------------------------------------------------------------|----------------------------------------------------------|
| US-01 | Projekt-Setup  | dass `sdd init` den Sicherheits-Guardrail automatisch mitbringt            | autonome Läufe ohne manuelles Setup abzusichern          |
| US-02 | Solo-Entwickler| mit `sdd init --autonomous` mein Projekt persönlich hands-off schalten     | ohne Clones/Teammates ungefragt in Bypass zu zwingen     |
| US-03 | Entwickler:in  | dass der Guardrail nur echte Gefahren blockt                              | nicht bei Commit-Messages/`gh pr create` ausgebremst zu werden |

## 6. Contracts

> Werden in `/sdd-review SPEC-0051` ergänzt (api: `sdd init --autonomous` + erzeugte Settings;
> behavior: Guardrail-Segment-/Flag-Semantik; behavior: idempotenter Hook-Merge).

## 7. Tests

> Werden nach Contract-Approval ergänzt (init-Merge idempotent + `--autonomous` schreibt local;
> Guardrail-Matrix block/allow/mention via Subprocess gegen das Script).

## 8. Implementierungsreihenfolge

1. Guardrail-Modul (`sdd_cli/guard.py`): Block-Regeln (Strategy) + geordnete Auswertung
   (Chain of Responsibility) + Segment-Split + präzise Force-Flags. Unit-Tests (block/allow/mention,
   inkl. der 3 Dogfooding-Fälle).
2. `sdd guard check`-Subcommand (liest Hook-stdin-JSON, gibt `permissionDecision` aus).
3. Dünner Hook-Wrapper `autonomous-guardrail.sh` (ruft `sdd guard check`, FR-07; Fail-Safe FR-08).
4. Blueprint-Assets: Hook-Wrapper unter `blueprint/.claude/hooks/` + `hooks`-Block in
   `blueprint/templates/agents-md/providers/claude/settings.json`.
5. `init.py`: Hook-Wrapper kopieren (FR-01) + `merge_claude_settings()` um Hook-Merge erweitern (FR-02).
6. `sdd init --autonomous`-Flag + `settings.local.json`-Schreiben + `.gitignore`-Eintrag (FR-03).
7. `.claude/commands/sdd-*`-Doku/Hinweis auf das Autonomie-Setup aktualisieren.

## 9. Offene Fragen

| # | Frage | Verantwortlich | Deadline |
|---|-------|----------------|----------|
| OQ-01 | ✅ Bypass committed oder nur lokal? **Antwort:** Nur `settings.local.json` via `--autonomous`; Guardrail immer committed. | Boris | geklärt |
| OQ-02 | ✅ Guardrail-False-Positive-Fix Teil dieser SPEC? **Antwort:** Ja (FR-04/FR-05). | Boris | geklärt |
| OQ-03 | ✅ Guardrail in Bash oder als Python-Modul? **Antwort:** Python-Modul mit dünnem Hook-Wrapper (FR-07/FR-08) — voll unit-testbares Strategy/Chain-of-Responsibility, löst die DIP-Warnung. | Boris | geklärt |
| OQ-04 | ✅ SOLID-Review flaggt SRP (init-Provisioning + Guardrail-Härtung gebündelt). Splitten? **Antwort:** Nein — bewusst kombiniert; die Teile sind durch „Guardrail vor der Verteilung härten" narrativ gekoppelt, ein Durchlauf/PR. SRP-Warnung akzeptiert. | Boris | geklärt |

## 10. Änderungshistorie

| Version | Datum      | Änderung           |
|---------|------------|---------------------|
| 0.1.0   | 2026-06-23 | Initiale Erstellung |
