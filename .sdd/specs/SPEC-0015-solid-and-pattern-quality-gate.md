---
id: SPEC-0015
project: PRJ-0001
title: SOLID & Design Pattern Quality Gate – Architekturprüfung in Spec- und Contract-Workflow
status: implemented
owner: Boris
created: 2026-05-15
updated: 2026-05-15
version: 0.1.0
priority: high
tags:
- solid
- design-patterns
- architecture
- quality-gate
- refactoring-guru
- llm-integration
depends_on:
- SPEC-0014
- SPEC-0008
contracts:
- CON-0045
- CON-0046
- CON-0047
- CON-0048
tests:
- TST-0060
- TST-0061
- TST-0062
- TST-0063
adrs: []
---
# SOLID & Design Pattern Quality Gate – Architekturprüfung in Spec- und Contract-Workflow

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Das SDD-System unterstützt aktuell Qualitätskontrollen auf Ebene von Vollständigkeit, Konsistenz
und Contract-Konflikten. Es fehlt jedoch eine **architekturelle Qualitätsebene**: Weder wird
geprüft, ob Spezifikationen und Implementierungen die SOLID-Prinzipien einhalten, noch werden
Design Patterns systematisch vorgeschlagen oder dokumentiert.

Das führt zu drei konkreten Problemen:

1. **Architektur-Drift:** Jeder Contract und jede SPEC kann unbemerkt gegen SOLID verstoßen –
   z. B. indem eine Klasse mehrere Verantwortlichkeiten bündelt (SRP-Verstoß) oder ein
   Behavior-Contract eine Schnittstelle beschreibt, die Clients zu viel wissen lässt (ISP-Verstoß).
2. **Blinde Pattern-Entscheidungen:** Patterns werden ad hoc gewählt ohne Begründung.
   Ein Reviewer kann nicht nachvollziehen, warum z. B. ein Strategy-Pattern statt eines
   Template-Method-Patterns gewählt wurde.
3. **Fehlende LLM-Architekturperspektive:** Beim Schreiben von Contracts und SPECs betrachtet
   das LLM bisher nur Vollständigkeit und Konflikte – nicht ob die vorgeschlagene Architektur
   bekannte Pattern-Lösungen elegant nutzt oder unnötige Komplexität erzeugt.

Diese SPEC definiert einen **SOLID & Pattern Quality Gate**, der in den bestehenden
Spec/Contract-Review-Workflow (SPEC-0014) integriert wird:

- Der LLM analysiert bei jedem `sdd spec review` und `sdd contract review` automatisch
  SOLID-Konformität und schlägt passende Design Patterns mit Begründung vor.
- Eine eigenständige `sdd solid-check`-Phase kann manuell oder als Gate ausgeführt werden.
- Alle Pattern-Entscheidungen werden in einem Pattern-Register dokumentiert mit Verweis
  auf die Refactoring Guru-Quelle (https://refactoring.guru/).

## 2. Zielsetzung

**Primärziel:**
Jede SPEC und jeder Contract durchläuft eine LLM-gestützte SOLID-Prüfung und erhält
strukturierte Pattern-Vorschläge mit Begründung, bevor die Execute-Phase freigegeben wird.

**Erfolgskriterien (messbar):**
- [ ] `sdd spec review <ID>` enthält einen Abschnitt "SOLID Analysis" mit Findings pro Prinzip
- [ ] `sdd contract review <ID>` enthält Pattern-Vorschläge mit Begründung und Refactoring-Guru-Link
- [ ] `sdd solid-check <ID>` gibt strukturiertes JSON mit SOLID-Findings aus (0 = konform)
- [ ] Jeder Pattern-Vorschlag enthält: Pattern-Name, Kategorie (Creational/Structural/Behavioral),
  Begründung (warum hier passend), Alternative (was stattdessen möglich wäre und warum nicht)
- [ ] Pattern-Vorschläge werden im Pattern-Register (`.sdd/patterns/<SPEC-ID>.json`) persistiert
- [ ] SOLID-Violations blockieren nicht automatisch die Execution (Warnungen, kein Hard-Gate),
  können aber als explizites Gate konfiguriert werden (`.sdd/config.yaml: solid_gate: warn|block`)
- [ ] SOLID-Analyse läuft in < 15 s pro SPEC/Contract (Streaming-Feedback)

**Nicht-Ziele (explizit):**
- Statische Code-Analyse (SOLID-Prüfung bezieht sich auf Spec/Contract-Ebene, nicht Python-Code)
- Automatisches Refactoring von SPECs oder Contracts
- Vollständige GoF-Pattern-Bibliothek (nur Patterns mit klarem Nutzen im Kontext werden vorgeschlagen)
- Erzwingen eines bestimmten Patterns (Vorschlag + Begründung, Entscheidung beim Autor)
- Integration in `sdd execute` als Hard-Gate (in v0.1.0 nur als Warnung)

## 3. Architektur-Entscheidungen & Design Patterns

> Diese SPEC definiert nicht nur, DASS Patterns verwendet werden, sondern dokumentiert hier
> exemplarisch, WELCHE Patterns für die Implementierung dieser SPEC selbst gewählt werden und WARUM.
> Quelle: https://refactoring.guru/design-patterns

### 3.1 Strategy Pattern (Behavioral)
**Anwendung:** Jedes der 5 SOLID-Prinzipien wird als eigenständige `SolidChecker`-Strategy
implementiert (`SrpChecker`, `OcpChecker`, `LspChecker`, `IspChecker`, `DipChecker`).

**Begründung:** Jedes Prinzip hat eine andere Analysemethode (SRP prüft Verantwortlichkeiten,
DIP prüft Abhängigkeitsrichtungen). Eine Strategy-Hierarchie erlaubt es, Checker unabhängig
zu testen, auszutauschen und um neue Prinzipien zu erweitern, ohne die aufrufende Logik
zu ändern (OCP für den Checker selbst).

**Alternative:** Template Method – abgelehnt, weil die Checker keine gemeinsame Algorithmus-
Struktur teilen; nur das Interface ist gemeinsam.

```python
class SolidChecker(Protocol):
    def check(self, artifact: SpecOrContract) -> list[SolidFinding]: ...

class SrpChecker:
    def check(self, artifact: SpecOrContract) -> list[SolidFinding]: ...

class SolidAnalyzer:
    def __init__(self, checkers: list[SolidChecker]) -> None: ...
    def analyze(self, artifact: SpecOrContract) -> SolidReport: ...
```

### 3.2 Chain of Responsibility (Behavioral)
**Anwendung:** Die 5 SOLID-Checker werden in einer Kette ausgeführt. Jeder Checker kann
Findings hinzufügen und gibt das akkumulierte Ergebnis weiter.

**Begründung:** Die Checker sind unabhängig voneinander (SRP-Violations beeinflussen nicht
die OCP-Analyse). Eine Kette statt einer Schleife erlaubt es, einzelne Checker ein- oder
auszuschalten und die Reihenfolge zu kontrollieren – insbesondere für Performance-Optimierung
(teure LLM-Checker zuletzt).

**Alternative:** Decorator – abgelehnt, weil Decorator strukturelle Erweiterung eines Objekts
meint; hier geht es um sequentielle Verarbeitung mit gemeinsamem Ergebnisobjekt.

### 3.3 Decorator Pattern (Structural)
**Anwendung:** `sdd spec review` und `sdd contract review` werden mit einem `SolidDecorator`
und einem `PatternSuggesterDecorator` erweitert, ohne die bestehenden Review-Funktionen
zu verändern.

**Begründung:** Die bestehenden Review-Implementierungen (SPEC-0014) sollen unverändert
bleiben (OCP). Ein Decorator fügt SOLID-Analyse und Pattern-Vorschläge transparent hinzu.
Das Ergebnis-Objekt (`ReviewReport`) wird mit den neuen Abschnitten angereichert.

**Alternative:** Direkte Erweiterung der Review-Funktionen – abgelehnt, weil dies SRP verletzt
(eine Funktion analysiert dann Vollständigkeit UND SOLID UND Patterns).

### 3.4 Registry Pattern (nicht GoF, aber etabliert)
**Anwendung:** Ein Pattern-Register (`.sdd/patterns/<SPEC-ID>.json`) speichert alle
Pattern-Entscheidungen für einen SPEC-Kontext mit Begründung und Quelle.

**Begründung:** Pattern-Entscheidungen sollen nachvollziehbar und für Folge-SPECs zugänglich
sein. Ein Registry erlaubt es, bei einem neuen Contract zu prüfen, welche Patterns im
selben SPEC-Kontext bereits genutzt werden (Konsistenzsicherung).

### 3.5 Null Object Pattern (Behavioral)
**Anwendung:** Ein `NullSolidChecker` wird verwendet, wenn SOLID-Checking in der Config
deaktiviert ist (`solid_gate: off`). Er gibt immer eine leere Finding-Liste zurück.

**Begründung:** Verhindert `if solid_gate_enabled:` Checks im aufrufenden Code (SRP, OCP).
Der Aufrufer muss nicht wissen, ob SOLID-Checking aktiv ist.

## 4. SOLID-Prüfung auf Spec/Contract-Ebene

### 4.1 Was auf SPEC-Ebene geprüft wird

| Prinzip | Prüfung auf SPEC-Ebene | Beispiel-Violation |
|---------|------------------------|-------------------|
| **S** – Single Responsibility | Hat die SPEC genau einen fachlichen Fokus? Sind mehrere unabhängige Features gebündelt? | SPEC beschreibt Login UND Passwort-Reset UND 2FA in einer SPEC |
| **O** – Open/Closed | Sind Erweiterungspunkte beschrieben? Muss für neue Use Cases die SPEC grundlegend geändert werden? | SPEC beschreibt eine switch-case-Logik ohne Plugin-Schnittstelle |
| **L** – Liskov Substitution | Sind Subtypen/Varianten konsistent mit dem Basisverhalten? | SPEC definiert eine spezialisierte Version, die Felder des Basis-Contracts ignoriert |
| **I** – Interface Segregation | Sind Schnittstellen in der SPEC zu breit? Müssen Konsumenten Methoden implementieren, die sie nicht benötigen? | Ein einziger API-Contract mit 15 Endpunkten für sehr unterschiedliche Clients |
| **D** – Dependency Inversion | Hängen High-Level-Konzepte der SPEC von Low-Level-Details ab? | SPEC referenziert direkt `SQLite` statt eine abstrakte `StorageAdapter`-Schnittstelle |

### 4.2 Was auf CONTRACT-Ebene geprüft wird

| Prinzip | Prüfung auf Contract-Ebene | Beispiel-Violation |
|---------|---------------------------|-------------------|
| **S** | Contract beschreibt genau eine Verantwortlichkeit | Behavior-Contract deckt Auth + Billing ab |
| **O** | Contract-Endpunkte/Schemas sind erweiterbar (z. B. via `additionalProperties: true` mit Versionierung) | Schema mit `additionalProperties: false` ohne Versionierungsstrategie |
| **L** | Response-Schema-Varianten sind kompatibel (keine Felder entfernt in v2) | `v2/users` gibt `email` nicht mehr zurück, obwohl es in v1 Pflichtfeld war |
| **I** | API-Contract ist für seinen Konsumentenkreis zugeschnitten | Alle Clients müssen Felder mitschicken, die nur Admin-Clients benötigen |
| **D** | Contract referenziert abstrakte Typen, nicht konkrete Implementierungen | Contract erzwingt `type: sqlite_connection_string` statt `type: database_url` |

### 4.3 LLM-Prompt-Struktur für SOLID-Analyse

Das LLM erhält beim `solid-check` folgende Kontextstruktur:

```
System: Du bist ein Software-Architekt der SOLID-Prinzipien prüft.
        Analysiere das folgende Artefakt (SPEC oder Contract) auf Einhaltung
        der 5 SOLID-Prinzipien. Gib für jedes Prinzip ein strukturiertes
        Finding aus. Sei konkret: zitiere den Artefakt-Abschnitt, der das
        Problem verursacht. Schlage eine Verbesserung vor.

User:   ARTEFAKT-TYP: {spec|contract}
        ARTEFAKT-ID: {id}
        INHALT:
        {artefakt_volltext}

        AUSGABE-FORMAT (JSON):
        {
          "solid_findings": [
            {
              "principle": "S|O|L|I|D",
              "severity": "info|warn|violation",
              "location": "Abschnitt/Zeile im Artefakt",
              "description": "Was genau verletzt wird",
              "suggestion": "Konkrete Verbesserung"
            }
          ],
          "overall_solid_score": "compliant|warn|violation",
          "summary": "Ein-Satz-Zusammenfassung"
        }
```

## 5. Pattern-Vorschlag-Workflow

### 5.1 Wann wird ein Pattern vorgeschlagen?

Pattern-Vorschläge werden in zwei Situationen generiert:

1. **Beim `sdd spec review`:** Nach der SOLID-Analyse prüft das LLM, welche GoF-Patterns
   oder architekturellen Patterns (aus dem Refactoring Guru Katalog) auf den fachlichen
   Kontext der SPEC passen. Vorgeschlagen werden **2–4 Patterns**, nicht mehr.
2. **Beim `sdd contract review`:** Das LLM analysiert, ob der Contract-Aufbau (Endpunkte,
   Schema-Struktur, Behavior-Szenarien) durch ein bekanntes Pattern eleganter gestaltet
   werden könnte.

### 5.2 Format eines Pattern-Vorschlags

```json
{
  "pattern_suggestions": [
    {
      "pattern_name": "Strategy",
      "category": "Behavioral",
      "refactoring_guru_url": "https://refactoring.guru/design-patterns/strategy",
      "applies_to": "SPEC-0015 / SolidChecker-Implementierung",
      "rationale": "Jedes SOLID-Prinzip ist ein unabhängiger Algorithmus mit gleichem Interface. Strategy erlaubt unabhängiges Testen und Austauschen ohne Änderung am Aufrufer.",
      "alternative": "Template Method – abgelehnt: Checker teilen keine gemeinsame Algorithmus-Struktur",
      "effort": "low|medium|high",
      "priority": "recommended|optional|consider"
    }
  ]
}
```

### 5.3 Pattern-Register-Persistenz

Pattern-Entscheidungen werden nach Bestätigung durch den Autor in das Pattern-Register geschrieben:

```
.sdd/patterns/
  SPEC-0015-patterns.json   ← Pattern-Vorschläge + Entscheidungen für diese SPEC
  _catalog.json             ← Aggregierter Überblick: welche Patterns wo im Projekt verwendet
```

```json
// SPEC-0015-patterns.json
{
  "spec_id": "SPEC-0015",
  "generated_at": "2026-05-15T...",
  "patterns": [
    {
      "pattern_name": "Strategy",
      "status": "accepted",    // accepted | rejected | under-review
      "accepted_at": "2026-05-15T...",
      "rejection_reason": null
    }
  ]
}
```

## 6. Integration in bestehenden Gate-Workflow (SPEC-0014)

### 6.1 Erweiterung des Phasenprozesses

Die SOLID-Analyse wird als **optionale Sub-Phase von Phase 2 (SPEC-Review)** und
**Phase 5 (Contracts-Review)** eingefügt. Sie blockiert nicht als eigene Gate-Phase,
sondern ergänzt den bestehenden Review-Output:

```
Phase 2: SPEC-Review
  ↳ 2a: Vollständigkeits- und Ambiguitätsprüfung (bestehend, SPEC-0014)
  ↳ 2b: SOLID-Analyse [NEU – SPEC-0015]
  ↳ 2c: Pattern-Vorschläge [NEU – SPEC-0015]

Phase 5: Contracts-Review
  ↳ 5a: Konflikt-Analyse (bestehend, SPEC-0014)
  ↳ 5b: SOLID-Analyse auf Contract-Ebene [NEU – SPEC-0015]
  ↳ 5c: Pattern-Vorschläge für Contract-Struktur [NEU – SPEC-0015]
```

### 6.2 Konfiguration in `.sdd/config.yaml`

```yaml
solid_gate:
  enabled: true
  mode: warn          # warn | block
  # 'warn': SOLID-Violations erscheinen im Review-Output, blockieren nicht
  # 'block': SOLID-Violations mit severity 'violation' blockieren den Gate-Übergang

pattern_suggestions:
  enabled: true
  max_suggestions: 4
  source: refactoring-guru   # Katalog-Referenz für Pattern-Links
```

### 6.3 CLI-Erweiterungen

```bash
# SOLID-Analyse für eine SPEC (standalone)
sdd solid-check SPEC-0015
sdd solid-check SPEC-0015 --json           # Maschinenlesbare Ausgabe
sdd solid-check SPEC-0015 --principle S    # Nur SRP prüfen

# Pattern-Vorschläge für eine SPEC oder einen Contract (standalone)
sdd pattern-suggest SPEC-0015
sdd pattern-suggest CON-0045

# Pattern-Entscheidung dokumentieren
sdd pattern-accept SPEC-0015 Strategy --reason "Unabhängige Checker-Algorithmen"
sdd pattern-reject SPEC-0015 TemplateMethod --reason "Keine gemeinsame Basisstruktur"

# Pattern-Register einsehen
sdd pattern-list                           # Alle Patterns im Projekt
sdd pattern-list SPEC-0015                 # Patterns für eine SPEC
```

### 6.4 Beispiel-CLI-Output `sdd spec review SPEC-0015`

```
SPEC-0015 · SOLID & Pattern Quality Gate

── Vollständigkeit ─────────────────────────────────────────────────────────
  ✓ Alle Pflichtfelder vorhanden
  ✓ Erfolgskriterien messbar
  ! OQ-01 noch offen (kein Deadline-Datum)

── SOLID-Analyse (2b) ──────────────────────────────────────────────────────
  ✓ S – Single Responsibility: SPEC hat einen klar abgegrenzten Fokus
  ✓ O – Open/Closed: solid_gate.mode als Konfiguration ist erweiterbar
  ✓ L – Liskov Substitution: keine Subtypen-Inkonsistenz erkannt
  ! I – Interface Segregation [WARN]
    → Abschnitt 6.3: `sdd solid-check` hat 3 optionale Flags (--json, --principle).
      Erwäge separate Subcommands für maschinenlesbare und gefilterte Ausgabe.
  ✓ D – Dependency Inversion: Abstraktion über SolidChecker Protocol korrekt

── Pattern-Vorschläge (2c) ─────────────────────────────────────────────────
  [1] Strategy (Behavioral) – EMPFOHLEN
      Warum: SolidChecker-Algorithmen sind unabhängig und austauschbar
      Quelle: https://refactoring.guru/design-patterns/strategy
  [2] Null Object (Behavioral) – EMPFOHLEN
      Warum: Vermeidet if-Checks wenn solid_gate.enabled=false
      Quelle: https://refactoring.guru/design-patterns/null-object
  [3] Decorator (Structural) – OPTIONAL
      Warum: Erweiterung von spec review / contract review ohne Änderung am Kern
      Quelle: https://refactoring.guru/design-patterns/decorator

  → Entscheiden mit: sdd pattern-accept SPEC-0015 <PatternName>
```

## 7. User Stories

| ID    | Als ...       | möchte ich ...                                                       | um ...                                                    |
|-------|---------------|----------------------------------------------------------------------|----------------------------------------------------------|
| US-01 | SPEC-Autor    | beim spec review automatisch SOLID-Feedback erhalten                 | Architektur-Probleme früh zu erkennen                    |
| US-02 | SPEC-Autor    | 2–4 konkrete Pattern-Vorschläge mit Begründung sehen                 | informierte Architektur-Entscheidungen treffen zu können  |
| US-03 | SPEC-Autor    | Pattern-Entscheidungen mit Begründung dokumentieren können           | Folge-SPECs von der Begründung profitieren               |
| US-04 | Tech Lead     | SOLID-Checking als Hard-Gate konfigurieren können                    | Architektur-Qualität projektübergreifend zu erzwingen    |
| US-05 | Tech Lead     | im Pattern-Register sehen, welche Patterns im Projekt verwendet werden | Architektur-Konsistenz zu wahren                       |
| US-06 | SPEC-Autor    | Pattern-Vorschläge ablehnen und Begründung dokumentieren             | bewusste Abweichungen transparent zu machen              |
| US-07 | Reviewer      | im Contract-Review sehen, ob SOLID-Prinzipien verletzt sind         | Code-Reviews effizienter führen zu können                |

## 8. Funktionale Anforderungen

- **FR-01:** `sdd spec review <ID>` führt nach der Vollständigkeitsprüfung automatisch
  eine SOLID-Analyse (2b) und eine Pattern-Suggestion (2c) durch, sofern `solid_gate.enabled: true`.
- **FR-02:** `sdd contract review <ID>` führt nach der Konflikt-Analyse automatisch
  eine SOLID-Analyse (5b) und eine Pattern-Suggestion (5c) durch.
- **FR-03:** `sdd solid-check <ID>` ist ein eigenständiger Befehl für SOLID-only-Analyse
  (ohne Vollständigkeitsprüfung und ohne Konflikt-Analyse).
- **FR-04:** `sdd pattern-suggest <ID>` ist ein eigenständiger Befehl für Pattern-only-Vorschläge.
- **FR-05:** `sdd pattern-accept <SPEC-ID> <PatternName> --reason "<text>"` speichert die
  Entscheidung im Pattern-Register.
- **FR-06:** `sdd pattern-reject <SPEC-ID> <PatternName> --reason "<text>"` speichert die
  Ablehnung mit Begründung im Pattern-Register.
- **FR-07:** `sdd pattern-list [<SPEC-ID>]` zeigt das Pattern-Register tabellarisch an.
- **FR-08:** Im `mode: block` blockiert mindestens eine SOLID-Finding mit `severity: violation`
  den Übergang von Phase 2 → 3 (für SPECs) bzw. Phase 5 → 6 (für Contracts).
- **FR-09:** Pattern-Vorschläge enthalten immer: Pattern-Name, Kategorie, Refactoring-Guru-URL,
  Begründung, Alternative mit Ablehnungsgrund.
- **FR-10:** Der LLM-Prompt für Pattern-Vorschläge verwendet den Refactoring Guru Katalog
  als Referenzrahmen und verlinkt die entsprechende Katalog-Seite.
- **FR-11:** Das Pattern-Register unter `.sdd/patterns/_catalog.json` aggregiert alle
  akzeptierten Patterns projektübergreifend.

## 9. Nicht-funktionale Anforderungen

| Kategorie       | Anforderung                                                                                     |
|-----------------|-------------------------------------------------------------------------------------------------|
| Performance     | SOLID-Analyse + Pattern-Suggestion in < 15 s pro Artefakt (Streaming-Feedback)                 |
| Erweiterbarkeit | Neue SOLID-Checker können ohne Änderung am `SolidAnalyzer` registriert werden (OCP)            |
| Erweiterbarkeit | Pattern-Katalog ist konfigurierbar (Refactoring Guru als Standard, anpassbar)                   |
| Konfigurierbarkeit | `solid_gate.mode: warn|block` und `pattern_suggestions.enabled` steuerbar per config.yaml   |
| Observability   | Jede SOLID-Analyse und jede Pattern-Entscheidung wird im strukturierten Log festgehalten        |
| Nachvollziehbarkeit | Pattern-Register ist menschenlesbar (JSON, aber mit erklärenden Feldern) und git-versionierbar |

## 10. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: SOLID & Design Pattern Quality Gate

  Scenario: SOLID-Analyse im spec review
    Given SPEC-0015 hat status "draft"
    And solid_gate.enabled ist true
    When "sdd spec review SPEC-0015" ausgeführt wird
    Then enthält der Output einen Abschnitt "SOLID-Analyse"
    And für jedes der 5 Prinzipien (S, O, L, I, D) existiert ein Eintrag
    And jeder Eintrag hat severity "info", "warn" oder "violation"

  Scenario: Pattern-Vorschlag enthält Refactoring-Guru-Link
    Given SPEC-0015 hat status "draft"
    When "sdd pattern-suggest SPEC-0015" ausgeführt wird
    Then enthält jeder Vorschlag eine URL die mit "https://refactoring.guru/" beginnt
    And jeder Vorschlag enthält ein "rationale"-Feld (nicht leer)
    And jeder Vorschlag enthält ein "alternative"-Feld mit Ablehnungsgrund

  Scenario: SOLID-Violation blockiert Gate im block-Modus
    Given solid_gate.mode ist "block"
    And "sdd solid-check SPEC-0015" gibt einen Finding mit severity "violation" zurück
    When "sdd spec review SPEC-0015" ausgeführt wird
    Then ist der Exit-Code 2
    And der Output enthält "SOLID-Violation blockiert Phasenübergang"

  Scenario: SOLID-Violation gibt nur Warnung im warn-Modus
    Given solid_gate.mode ist "warn"
    And "sdd solid-check SPEC-0015" gibt einen Finding mit severity "violation" zurück
    When "sdd spec review SPEC-0015" ausgeführt wird
    Then ist der Exit-Code 0
    And der Output enthält "[WARN] SOLID-Violation"
    And der Output enthält NICHT "blockiert Phasenübergang"

  Scenario: Pattern-Entscheidung wird im Register persistiert
    Given SPEC-0015 hat Pattern-Vorschlag "Strategy"
    When "sdd pattern-accept SPEC-0015 Strategy --reason 'Unabhängige Algorithmen'" ausgeführt wird
    Then existiert ".sdd/patterns/SPEC-0015-patterns.json"
    And die Datei enthält ein Eintrag mit pattern_name "Strategy" und status "accepted"
    And die Datei enthält die angegebene reason

  Scenario: Pattern-Ablehnung mit Begründung dokumentiert
    Given SPEC-0015 hat Pattern-Vorschlag "TemplateMethod"
    When "sdd pattern-reject SPEC-0015 TemplateMethod --reason 'Keine gemeinsame Struktur'" ausgeführt wird
    Then enthält ".sdd/patterns/SPEC-0015-patterns.json" einen Eintrag mit status "rejected"
    And das Feld "rejection_reason" ist nicht leer

  Scenario: Null Object Checker wenn solid_gate deaktiviert
    Given solid_gate.enabled ist false
    When "sdd spec review SPEC-0015" ausgeführt wird
    Then enthält der Output KEINEN Abschnitt "SOLID-Analyse"
    And der Befehl gibt Exit-Code 0 zurück
```

## 11. Offene Fragen

| # | Frage | Verantwortlich | Deadline |
|---|-------|----------------|----------|
| OQ-01 | Soll der Pattern-Vorschlag auch ADRs vorschlagen (Architecture Decision Records) oder nur Pattern-Register-Einträge? | Boris | vor Contract-Schreiben |
| OQ-02 | Werden SOLID-Findings pro Artefakt gecacht (wie Contract-Extraktion in SPEC-0014) oder immer neu berechnet? | Boris | Architekturentscheidung |
| OQ-03 | Soll `sdd pattern-list` auch Patterns zeigen, die in anderen SPECs im Projekt abgelehnt wurden (Warn-Hinweis)? | Boris | UX-Entscheidung |
| OQ-04 | Welcher Pattern-Katalog-Umfang ist sinnvoll? Nur GoF-23 oder auch Enterprise Patterns (Martin Fowler)? | Boris | vor LLM-Prompt-Design |
