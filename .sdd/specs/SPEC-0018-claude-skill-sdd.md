---
id: SPEC-0018
project: PRJ-0001
title: "Claude Skill für SDD – /sdd Slash-Commands für geführten Spec-Zyklus in Claude Code"
status: implemented
owner: Boris
created: 2026-05-16
updated: 2026-05-16
version: 0.1.0
priority: high
tags:
  - claude-code
  - skill
  - workflow
  - developer-experience
  - blueprint
depends_on:
  - SPEC-0001
  - SPEC-0005
  - SPEC-0008
  - SPEC-0010
  - SPEC-0014
  - SPEC-0015
contracts:
  - CON-0057
  - CON-0058
  - CON-0059
tests:
  - TST-0063
  - TST-0064
  - TST-0065
adrs: []
---

# Claude Skill für SDD – /sdd Slash-Commands für geführten Spec-Zyklus in Claude Code

> **Status:** implemented · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Der SDD-Workflow umfasst heute eine CLI (`sdd`), eine Web UI und eine VS Code Extension.
Alle drei erfordern, dass der Entwickler die Struktur und Konventionen bereits kennt:
welche Felder ein SPEC-Frontmatter braucht, welcher Lifecycle-Status gültig ist, welche
Contract-Typen existieren und wie man eine vollständige Feature-Spezifikation schreibt,
die das Execution Gate passiert.

**Das Problem:** Neues Feature → leeres Textdokument. Kein geführter Einstieg.
Der Entwickler muss sich die Conventions aus bestehenden Specs erschließen oder
`sdd new spec` aufrufen, das nur ein leeres Template erzeugt.

**Claude Code** bietet mit *Custom Skills* (Slash-Commands in `.claude/commands/`) eine
natürliche Lösung: Claude kann interaktiv Fragen stellen, Kontext aus dem Projekt lesen
(bestehende Specs, Contracts, Config) und ein vollständiges, valides Dokument generieren –
ohne dass der Entwickler ein einziges Feld manuell ausfüllen muss.

Diese SPEC definiert eine Familie von **`/sdd`-Skills**, die als Markdown-Dateien im
Blueprint-Verzeichnis leben und bei `sdd init` in jedes neue Projekt kopiert werden.

---

## 2. Zielsetzung

**Primärziel:**
Entwickler können den gesamten SDD-Dokument-Zyklus (Spec erstellen → Contract ableiten
→ Test anlegen → validieren → reviewen) direkt in Claude Code starten, ohne das Terminal
oder Dokumentation zu konsultieren.

**Erfolgskriterien (messbar):**

- [ ] `/sdd` zeigt eine Übersicht aller verfügbaren SDD-Skills + Kurzstatus des Projekts
      (Anzahl Specs nach Status, offene Validation-Fehler)
- [ ] `/sdd-new` führt durch die Erstellung eines SPEC inkl. automatischer ID-Vergabe,
      Frontmatter und aller Pflichtabschnitte; erzeugt valides Dokument laut JSON-Schema
- [ ] `/sdd-validate` ruft `sdd validate` auf, parst den Output und erklärt jeden Fehler
      auf Deutsch mit konkretem Lösungsvorschlag
- [ ] `/sdd-review` führt durch den Contract-Review-Prozess: zeigt Review-Ergebnis,
      erklärt SOLID-Verletzungen und schlägt Pattern-Anpassungen mit Refactoring-Guru-Link vor
- [ ] `/sdd-status` zeigt Lifecycle-Status aller Specs/Contracts + Blocking-Issues
      (vergleichbar `sdd status-check`)
- [ ] Alle Skill-Dateien sind Teil des `sdd init`-Blueprints (`.claude/commands/`)
- [ ] Skill-Dateien sind idempotent: mehrfaches `sdd init` überschreibt sie nicht,
      wenn lokal modifiziert (Konflikt-Warnung statt blindem Überschreiben)

**Nicht-Ziele (explizit):**
- Kein Ersatz für die CLI – die Skills rufen `sdd`-Befehle auf, duplizieren keine Logik
- Keine eigene LLM-API-Integration – Claude Code selbst ist das LLM
- Kein automatisches Commit/Push nach Erstellung
- Keine Skill-Unterstützung für `sdd obsidian` (separates Workflow-Thema)
- Kein interaktives Formular in VS Code WebView – nur Terminal/Chat-Interface

---

## 3. Architektur & Dateistruktur

### 3.1 Skill-Dateien im Blueprint

```
sdd-framer/
└── .sdd/
    └── templates/
        └── agents-md/
            └── commands/           ← NEU: Claude-Skill-Templates
                ├── sdd.md
                ├── sdd-new.md
                ├── sdd-validate.md
                ├── sdd-review.md
                └── sdd-status.md
```

Bei `sdd init` kopiert `init.py` den Inhalt von `agents-md/commands/` nach
`.claude/commands/` im Ziel-Projekt (analog zur bestehenden `CLAUDE.md`-Kopier-Logik).

### 3.2 Skill-Datei-Format (Claude Code Custom Commands)

Jede Skill-Datei ist ein Markdown-Dokument, das Claude als Instruktionsset interpretiert,
wenn der zugehörige Slash-Command eingegeben wird. Das Format folgt der Claude-Code-
Konvention:

```markdown
# /sdd-new – Neuen SDD-Spec erstellen

## Aufgabe
[Klare Beschreibung was Claude bei diesem Command tun soll]

## Schritte
1. ...
2. ...

## Konventionen
[Projektspezifische Regeln die Claude einhalten muss]

## Beispiel-Output
[Ein Beispiel des erwarteten Ergebnisses]
```

### 3.3 Design Patterns

#### 3.3.1 Template Method Pattern (Behavioral) — Skill-Ablauf

**Anwendung:** Jeder Skill folgt demselben Grundablauf:
`Kontext lesen → Fragen stellen → Dokument generieren → Validieren → Speichern`.
Der abstrakte Ablauf ist in der Basis-Skill-Struktur definiert; konkrete Skills
überschreiben nur die inhaltlichen Schritte.

**Begründung:** Einheitliche UX über alle Skills (OCP). Neue Skills folgen demselben
Muster ohne die Basis-Logik zu duplizieren.

#### 3.3.2 Facade Pattern (Structural) — CLI-Kapselung

**Anwendung:** Die Skills kapseln alle `sdd`-CLI-Aufrufe hinter einfachen,
beschreibenden Instruktionen. Claude führt `sdd validate`, `sdd review-contract` etc.
aus und übersetzt die Ausgabe in verständliche Aktionen.

**Begründung:** Der Entwickler interagiert nur mit dem Skill (Hochsprache), nicht
direkt mit der CLI-Schnittstelle. Die CLI bleibt austauschbar.

#### 3.3.3 Strategy Pattern (Behavioral) — ID-Ermittlung

**Anwendung:** `/sdd-new` ermittelt die nächste freie ID entweder via
`sdd new spec --dry-run` (wenn verfügbar) oder durch direktes Zählen der
vorhandenen Dateien. Die Strategie ist auswechselbar ohne Änderung am Skill.

**Begründung:** Robustheit wenn die CLI nicht installiert ist oder sich die
ID-Logik ändert.

---

## 4. Skill-Definitionen

### 4.1 `/sdd` – Projekt-Übersicht & Help

**Auslöser:** `/sdd` ohne Argumente

**Ablauf:**
1. Claude liest `.sdd/config.yaml` und alle Spec-Frontmatter (Status-Felder)
2. Zeigt kompakte Status-Tabelle: `SPEC-XXXX | Titel | Status`
3. Listet verfügbare Skills mit Kurzbeschreibung
4. Zeigt offene Blockaden (Specs in `draft` seit > 7 Tagen, fehlende Contracts)

**Output-Format:**
```
## SDD Projektübersicht – <Projektname>

| Spec     | Titel                    | Status      |
|----------|--------------------------|-------------|
| SPEC-0001 | User Login               | implemented |
| SPEC-0017 | VS Code Full Flow        | draft       |

**Verfügbare Skills:**
- /sdd-new       – Neuen Spec/Contract/Test erstellen
- /sdd-validate  – Projekt validieren + Fehler erklären
- /sdd-review    – Contract reviewen (SOLID + Pattern)
- /sdd-status    – Lifecycle-Status und Blocking-Issues

**Offene Punkte:** 2 Specs in draft, 0 Validation-Fehler
```

### 4.2 `/sdd-new` – Geführte Dokument-Erstellung

**Auslöser:** `/sdd-new [spec|contract|test|adr]`

**Ablauf:**
1. Fragt nach Dokumenttyp (wenn nicht als Argument übergeben)
2. **Für SPEC:**
   - Stellt maximal 6 Fragen:
     1. Welches Feature/Problem wird gelöst? (Titel + Kontext)
     2. Wer ist betroffen? (User Stories, 1–3 Sätze)
     3. Was ist der messbare Erfolg? (Erfolgskriterien)
     4. Was ist explizit **nicht** im Scope? (Nicht-Ziele)
     5. Welche bestehenden Specs hängen davon ab? (depends_on)
     6. Welche Priority? (high/medium/low)
   - Liest bestehende Specs um Pattern zu verstehen (Abschnitte, Tiefe)
   - Generiert vollständiges SPEC-Dokument mit:
     - Nächster freier ID (via `ls .sdd/specs/ | sort | tail -1`)
     - Heutigem Datum als `created` und `updated`
     - Pflichtabschnitten: Kontext, Zielsetzung, Architektur, FR, NFR, User Stories, Contracts-Platzhalter, Tests-Platzhalter, Implementierungsreihenfolge
     - Design-Pattern-Vorschlägen (mindestens 2, mit Begründung und Alternative)
   - Speichert nach Bestätigung als `.sdd/specs/SPEC-XXXX-<slug>.md`
3. **Für CONTRACT:** Fragt nach verknüpftem SPEC, Typ (api/behavior/data/performance),
   was garantiert wird; generiert Contract aus passendem Template
4. **Für TEST:** Fragt nach verknüpftem SPEC/Contract, Teststufe (unit/contract/acceptance),
   was geprüft wird; generiert Test-Stub

**Qualitätssicherung:**
- Nach Generierung läuft `sdd validate --file <neues-dokument>` automatisch
- Bei Fehlern: Claude erklärt Fehler und korrigiert das Dokument
- Speichern erst nach erfolgreicher Validierung

### 4.3 `/sdd-validate` – Validierung mit Erklärungen

**Auslöser:** `/sdd-validate [--file SPEC-XXXX|--all]`

**Ablauf:**
1. Führt `sdd validate` (oder `sdd validate --file X`) aus
2. Parst den Rich-Output
3. Für jeden Fehler:
   - Zeigt betroffene Datei + Zeile
   - Erklärt **warum** das ein Fehler ist (Regel + Konsequenz)
   - Schlägt konkreten Fix vor (inkl. Code-Snippet wenn nötig)
   - Fragt ob Fix sofort angewendet werden soll
4. Zeigt Zusammenfassung: N Fehler gefunden, M behoben

**Fehler-Erklärungstiefe:**
- Schema-Fehler → zeigt erlaubte Werte aus JSON-Schema
- Referenzielle Integrität → zeigt welches Dokument fehlt
- Lifecycle-Fehler (FR-10/FR-11) → erklärt erlaubte Status-Übergänge

### 4.4 `/sdd-review` – Contract-Review mit SOLID-Analyse

**Auslöser:** `/sdd-review [CON-XXXX|--pending]`

**Ablauf:**
1. Bei `--pending`: zeigt alle Contracts mit `status: draft`, User wählt einen aus
2. Liest den Contract + verknüpften SPEC
3. Führt inhaltlichen Review durch:
   - Ist die Garantie messbar und testbar?
   - Gibt es SOLID-Verletzungen im beschriebenen Design?
   - Welche Design Patterns würden passen? (mit Refactoring-Guru-Link)
4. Schreibt Review-Ergebnis in `.sdd/evaluations/<CON-ID>-review.md` (analog `lifecycle.py`)
5. Fragt ob Contract-Status auf `approved` gesetzt werden soll

**SOLID-Prüfung (analog SPEC-0015):**
- SRP: Hat der Contract eine einzige Verantwortlichkeit?
- OCP: Kann die garantierte Schnittstelle erweitert werden ohne Breaking Change?
- LSP: Wenn Vererbung im Design – sind Subtypen vollständig austauschbar?
- ISP: Sind die beschriebenen Interfaces schlank genug?
- DIP: Hängt das Design von Abstraktionen, nicht Konkretionen ab?

### 4.5 `/sdd-status` – Lifecycle-Status und Blocker

**Auslöser:** `/sdd-status [--spec SPEC-XXXX|--all]`

**Ablauf:**
1. Ruft `sdd status-check` auf
2. Gruppiert Ausgabe in:
   - **Blockiert:** Specs die nicht weiter können (fehlende Contracts/Tests)
   - **In Arbeit:** Specs in `draft` oder `in-review`
   - **Bereit für Execution Gate:** `status: approved` + alle Contracts `approved`
   - **Abgeschlossen:** `implemented`
3. Für jeden Blocker: konkreter nächster Schritt (z. B. "Erstelle Contract mit `/sdd-new contract`")

---

## 5. Funktionale Anforderungen

### 5.1 Blueprint-Integration

**FR-01** `sdd init` kopiert alle Dateien aus `.sdd/templates/agents-md/commands/`
nach `.claude/commands/` im Ziel-Projekt.

**FR-02** Existiert `.claude/commands/<datei>.md` bereits (lokal modifiziert),
wird sie **nicht** überschrieben. `sdd init` zeigt eine Warnung:
`[WARN] .claude/commands/sdd-new.md bereits vorhanden – übersprungen`.

**FR-03** `sdd init --force-skills` überschreibt Skill-Dateien explizit
(Opt-in für Blueprint-Updates).

### 5.2 Skill-Datei-Qualität

**FR-04** Jede Skill-Datei beginnt mit einem YAML-ähnlichen Kommentarblock:
```markdown
<!-- skill: sdd-new | version: 0.1.0 | sdd-blueprint: true -->
```
Dieser Block ermöglicht `sdd validate` zu prüfen ob die Skill-Version aktuell ist.

**FR-05** Skill-Dateien referenzieren keine absoluten Pfade. Alle Pfade sind
relativ zum Projekt-Root (`.sdd/`, `specs/`, `.claude/`).

**FR-06** Skill-Dateien enthalten keinen hardkodierten Projekt-Namen oder
Spec-IDs aus dem Blueprint-Projekt.

### 5.3 Laufzeit-Verhalten

**FR-07** `/sdd-new` prüft vor der ID-Vergabe, ob `sdd` CLI verfügbar ist
(`which sdd`). Bei fehlendem CLI: Fallback auf Datei-Zählung + Warnung.

**FR-08** `/sdd-validate` läuft immer `sdd validate` – kein Caching.

**FR-09** `/sdd-review` schreibt Review-Ergebnis nur wenn `sdd` CLI verfügbar.
Ohne CLI: Review-Text wird angezeigt aber nicht persistent gespeichert
(Warnung an User).

**FR-10** Alle Skills prüfen zu Beginn ob `.sdd/config.yaml` existiert. Wenn nicht:
Fehlermeldung `Kein SDD-Projekt gefunden. Führe zuerst 'sdd init' aus.`

---

## 6. Nicht-funktionale Anforderungen

| Attribut | Anforderung |
|---|---|
| Skill-Datei-Größe | < 200 Zeilen pro Datei (Claude-Kontext-Effizienz) |
| Ladezeit | Kein Setup außer Dateilesen – sofort einsatzbereit |
| Sprache | Skill-Dateien auf Deutsch (Konvention des Projekts) |
| Wartbarkeit | Skill-Version im Kommentarblock; `sdd validate` kann Veralterung erkennen |
| Portabilität | Keine Shell-spezifischen Features; Bash-Befehle laufen in Claude Code Bash-Tool |
| Idempotenz | `sdd init` ist sicher mehrfach ausführbar (FR-02) |

---

## 7. User Stories

| ID    | Als …       | möchte ich …                                                                 | damit …                                                        |
|-------|-------------|------------------------------------------------------------------------------|----------------------------------------------------------------|
| US-01 | Entwickler  | `/sdd-new spec` eingeben und geführt einen neuen Spec erstellen               | ich keine Vorlage suchen oder Felder erraten muss              |
| US-02 | Entwickler  | nach der Spec-Erstellung automatisch Contracts vorgeschlagen bekommen         | ich direkt im Flow bleiben kann                                |
| US-03 | Reviewer    | `/sdd-review CON-0057` aufrufen und eine SOLID-Analyse bekommen               | ich Qualitätsprobleme früh erkenne                             |
| US-04 | Entwickler  | `/sdd-validate` aufrufen und jeden Fehler erklärt bekommen                    | ich nicht selbst die Schema-Docs nachschlagen muss             |
| US-05 | Tech Lead   | `/sdd-status` sehen und auf einen Blick erkennen was blockiert                | ich priorisieren kann ohne alle Dateien zu öffnen              |
| US-06 | Entwickler  | nach `sdd init` sofort `/sdd` in Claude Code nutzen können                    | kein manuelles Einrichten nötig ist                            |
| US-07 | Maintainer  | Skill-Dateien im Blueprint aktualisieren ohne bestehende Projekte zu brechen  | ich Breaking Changes kontrolliert ausliefern kann              |

---

## 8. Datenmodell – Skill-Datei-Metadaten

### Skill-Header (Kommentarblock am Dateianfang)
```
<!-- skill: <name> | version: <semver> | sdd-blueprint: true | updated: <ISO-datum> -->
```

### Blueprint-Manifest-Erweiterung (`.sdd/config.yaml`)
```yaml
skills:
  version: "0.1.0"
  commands:
    - name: sdd
      file: .claude/commands/sdd.md
    - name: sdd-new
      file: .claude/commands/sdd-new.md
    - name: sdd-validate
      file: .claude/commands/sdd-validate.md
    - name: sdd-review
      file: .claude/commands/sdd-review.md
    - name: sdd-status
      file: .claude/commands/sdd-status.md
```

---

## 9. Contracts

| Contract-ID | Typ       | Was wird garantiert?                                                         |
|-------------|-----------|------------------------------------------------------------------------------|
| CON-0057    | behavior  | Gherkin-Szenarien: `/sdd-new spec` – Pflichtfelder, ID-Vergabe, Validierung  |
| CON-0058    | data      | JSON Schema: Skill-Header-Format + config.yaml-Erweiterung (`skills`-Block)  |
| CON-0059    | behavior  | `sdd init`-Verhalten: Kopieren, Idempotenz, `--force-skills` Flag            |

---

## 10. Tests

| Test-ID  | Level      | Was prüft der Test?                                                                        |
|----------|------------|--------------------------------------------------------------------------------------------|
| TST-0063 | unit       | `init.py`: Skill-Dateien werden kopiert; Idempotenz bei vorhandenen Dateien; `--force-skills` überschreibt |
| TST-0064 | contract   | Skill-Dateien im Blueprint: Header vorhanden, kein absoluter Pfad, < 200 Zeilen           |
| TST-0065 | acceptance | Gherkin aus CON-0057: `/sdd-new spec` erzeugt valides SPEC-Dokument in Sandbox-Projekt    |

---

## 11. Implementierungsreihenfolge

```
Phase A: Blueprint-Verzeichnis + Skill-Dateien erstellen
  └─ .sdd/templates/agents-md/commands/sdd.md
  └─ .sdd/templates/agents-md/commands/sdd-new.md
  └─ .sdd/templates/agents-md/commands/sdd-validate.md
  └─ .sdd/templates/agents-md/commands/sdd-review.md
  └─ .sdd/templates/agents-md/commands/sdd-status.md

Phase B: init.py erweitern
  └─ Neue Kopierfunktion: copy_skill_files(target_dir, force=False)
  └─ Idempotenz-Logik: prüfe ob Zieldatei existiert und weiche ab
  └─ --force-skills Flag in sdd init command
  └─ config.yaml-Erweiterung: skills-Block schreiben

Phase C: validate.py erweitern
  └─ Skill-Header-Prüfung: ist version: vorhanden und aktuell?
  └─ Neue Issue-Kategorie: SKILL_OUTDATED (Warning, kein Error)

Phase D: Contracts + Tests
  └─ CON-0057 (Gherkin sdd-new spec)
  └─ CON-0058 (JSON Schema Skill-Header)
  └─ CON-0059 (Gherkin sdd init Skill-Kopieren)
  └─ TST-0063 (unit init.py)
  └─ TST-0064 (contract Skill-Datei-Qualität)
  └─ TST-0065 (acceptance Sandbox)
```

---

## 12. Offene Fragen

- [ ] Sollen Skill-Dateien auch in Englisch bereitgestellt werden?
      → Erste Version Deutsch; Mehrsprachigkeit via `sdd init --lang en` als optionales Upgrade
- [ ] Wie wird Skill-Versions-Drift erkannt, wenn Projekte den Blueprint-Stand einfrieren?
      → Vorschlag: `sdd validate` zeigt `[WARN] Skill sdd-new ist veraltet (v0.1.0 vs. v0.2.0)`
- [ ] Sollen Skill-Dateien den vollen `.sdd`-Pfad-Kontext via `sdd config show` laden?
      → Ja, als erste Aktion jedes Skills; ermöglicht projektspezifische Anpassungen
- [ ] Kann `/sdd-new` Specs direkt committen (mit Git-Hook-Prüfung)?
      → Nicht in v0.1.0; nur Datei schreiben, kein automatisches `git add`

---

## 13. Änderungshistorie

| Datum      | Version | Autor | Änderung            |
|------------|---------|-------|---------------------|
| 2026-05-16 | 0.1.0   | Boris | Initiale Erstellung |
