---
id: SPEC-0011
project: PRJ-0001
title: Token-Kostenschätzung – Implementierungsaufwand pro Spec auf Basis gelernter Daten
status: implemented
owner: Boris
created: 2026-05-14
updated: 2026-05-14
version: 1.0.0
priority: medium
tags:
- cost-estimation
- tokens
- telemetry
- analytics
- budgeting
- llm
depends_on:
- SPEC-0008
contracts:
- CON-0041
- CON-0042
- CON-0043
- CON-0044
tests:
- TST-0055
- TST-0056
- TST-0057
- TST-0058
- TST-0059
adrs: []
---
# Token-Kostenschätzung – Implementierungsaufwand pro Spec auf Basis gelernter Daten

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Die Implementierung eines Specs durch LLM-gestützte Tools (Orchestrator, AI-Routes, Evaluator)
verbraucht Tokens, die direkt in Kosten übersetzt werden. Im aktuellen System werden Token-Counts
zwar teilweise erfasst (via `usage_store` in AI-Routes), aber nicht zur Vorhersage genutzt.

Entwickler und Teams haben konkrete Bedürfnisse:
- **Budgetplanung:** „Was kostet es, diese 3 Specs zu implementieren?"
- **Priorisierung:** Welche Specs sind „teure" und welche „günstige" Implementierungen?
- **Überraschungsschutz:** Vor dem Start einer LLM-gestützten Implementierung eine Warnung,
  wenn die Schätzung das konfigurierte Budget überschreitet.

Das System soll aus historischen Token-Daten (gespeichert in `.sdd/evaluations.db`) lernen und
für neue Specs eine Kostenschätzung liefern, ohne das LLM für die Schätzung selbst zu nutzen
(rein datenbasiert → kein Henne-Ei-Problem).

## 2. Zielsetzung

**Primärziel:**
Vor der LLM-gestützten Implementierung eines Specs wird eine Token-Kostenschätzung ausgegeben,
die auf historischen Daten vergleichbarer Specs basiert.

**Erfolgskriterien (messbar):**
- [ ] `sdd estimate SPEC-XXXX` gibt eine Schätzung in Tokens und geschätzten USD-Kosten aus
- [ ] Die Schätzung basiert auf mindestens einem der Merkmale: Spec-Größe (Zeichen), Anzahl Contracts, Anzahl User Stories, Tags
- [ ] Bei < 3 historischen Datenpunkten wird eine Warnung "Wenig Daten – Schätzung unzuverlässig" ausgegeben
- [ ] `sdd estimate --all` schätzt alle Specs ohne Implementations-Status und gibt eine Gesamtsumme aus
- [ ] Ein konfigurierbarer `budget_alert_usd`-Schwellwert löst eine Warnung aus wenn die Schätzung ihn überschreitet
- [ ] Token-Verbrauch jeder LLM-Komponente wird in `.sdd/evaluations.db` gespeichert (als Grundlage für zukünftige Schätzungen)

**Nicht-Ziele (explizit):**
- Kein LLM-Einsatz für die Schätzung selbst (rein statistisch/heuristisch)
- Keine Echtzeit-Preisaktualisierung (Preistabelle ist statisch in config.yaml konfiguriert)
- Keine Schätzung für Nicht-LLM-Implementierungsschritte (Build-Zeit, manuelle Entwicklung)
- Kein maschinelles Lernen mit externen Modellen – ausschließlich interne Heuristiken

## 3. User Stories

| ID    | Als ...           | möchte ich ...                                                           | um ...                                                              |
|-------|-------------------|--------------------------------------------------------------------------|---------------------------------------------------------------------|
| US-01 | Entwickler        | vor der Implementierung die erwarteten Token-Kosten sehen               | mein monatliches API-Budget nicht zu überschreiten                  |
| US-02 | Tech Lead         | den Gesamtaufwand aller ausstehenden Specs schätzen                     | die Sprint-Kapazität für LLM-gestützte Implementierungen zu planen  |
| US-03 | Entwickler        | eine Warnung erhalten wenn ein Spec das Budget-Limit überschreiten würde | frühzeitig zu entscheiden ob ich lokal (LM Studio) arbeite          |
| US-04 | Entwickler        | die Schätzgenauigkeit über Zeit verbessern                              | durch automatisch gesammeltes historisches Datenmaterial            |

## 4. Schätzmodell

### 4.1 Feature-Extraktion

Folgende Merkmale werden aus einem Spec extrahiert (ohne LLM):

| Merkmal               | Berechnung                                                      |
|-----------------------|-----------------------------------------------------------------|
| `body_chars`          | Zeichenanzahl Body (ohne Frontmatter)                           |
| `contract_count`      | Anzahl Einträge in `contracts:` Frontmatter                     |
| `test_count`          | Anzahl Einträge in `tests:` Frontmatter                         |
| `user_story_count`    | Anzahl Zeilen mit `| US-` im Body                               |
| `fr_count`            | Anzahl Zeilen mit `**FR-` im Body                               |
| `dependency_count`    | Anzahl Einträge in `depends_on:`                                |
| `priority_weight`     | `critical=4, high=3, medium=2, low=1`                           |

### 4.2 Schätzmethode (v1: Nearest-Neighbor-Heuristik)

1. Alle historischen Datenpunkte aus `.sdd/evaluations.db` (Tabelle `token_usage`) laden
2. Feature-Vektor des Ziel-Specs berechnen
3. Euklidischen Abstand zu allen historischen Specs berechnen (normalisierte Features)
4. Gewichteter Durchschnitt der Token-Counts der k=3 nächsten Nachbarn
5. Konfidenz-Level basierend auf Anzahl verfügbarer Datenpunkte:
   - `< 3 Punkte` → `LOW` (Warnung)
   - `3–9 Punkte` → `MEDIUM`
   - `≥ 10 Punkte` → `HIGH`

### 4.3 Kostentabelle (konfigurierbar)

```yaml
# .sdd/config.yaml
cost_estimation:
  model_prices:
    claude-haiku-4-5-20251001:
      input_per_million: 0.80
      output_per_million: 4.00
      cache_write_per_million: 1.00
      cache_read_per_million: 0.08
    claude-sonnet-4-6:
      input_per_million: 3.00
      output_per_million: 15.00
    default:
      input_per_million: 3.00
      output_per_million: 15.00
  budget_alert_usd: 5.00      # Warnung wenn Schätzung > 5 USD
  default_model: claude-haiku-4-5-20251001
```

## 5. Funktionale Anforderungen

### Schätzung

- **FR-01:** `sdd estimate SPEC-XXXX` gibt aus: geschätzte Input-Tokens, Output-Tokens,
  berechnete Kosten (USD), Konfidenz-Level, und die k=3 nächsten historischen Vergleichspunkte
  (Spec-ID, tatsächliche Tokens, Ähnlichkeit).
- **FR-02:** `sdd estimate --all [--status draft|review]` schätzt alle Specs mit dem
  angegebenen Status und gibt eine Gesamttabelle mit Summen-Zeile aus.
- **FR-03:** Wenn die geschätzte USD-Summe `budget_alert_usd` überschreitet, wird eine
  farbige `WARNING`-Box mit dem Betrag ausgegeben (kein Exit-Code-Fehler).
- **FR-04:** `sdd estimate SPEC-XXXX --json` gibt das Ergebnis als maschinenlesbares JSON aus.
- **FR-05:** `sdd estimate SPEC-XXXX --model MODEL-ID` überschreibt das Preismodell für diese Schätzung.

### Datenpersistenz

- **FR-06:** Jede LLM-Komponente (Evaluator, Orchestrator, Analyzer, AI-Routes) schreibt
  nach einem Aufruf den tatsächlichen Token-Verbrauch in `.sdd/evaluations.db` (Tabelle
  `token_usage`) mit folgenden Spalten:
  `(id, timestamp, spec_id, component, model, input_tokens, output_tokens, cache_read_tokens,
   cache_write_tokens, duration_ms)`.
  `spec_id` ist `NULL` wenn kein Kontext-Spec bekannt.
- **FR-07:** `sdd token-history [SPEC-XXXX]` zeigt alle gespeicherten Token-Verbräuche
  für eine Spec (oder alle Specs wenn kein Argument) als formatierte Tabelle.
- **FR-08:** `sdd token-history --export CSV-DATEI` exportiert alle Datenpunkte als CSV.

### Kalibrierung

- **FR-09:** Nach Abschluss einer LLM-gestützten Implementierung kann `sdd calibrate SPEC-XXXX`
  die tatsächlichen Tokens aus der `token_usage`-Tabelle zusammenfassen und als
  "Abschluss-Datenpunkt" für die Nearest-Neighbor-Berechnung markieren.

## 6. Nicht-funktionale Anforderungen

| Kategorie     | Anforderung                                                                               |
|---------------|-------------------------------------------------------------------------------------------|
| Performance   | `sdd estimate SPEC-XXXX` in < 200 ms (nur DB-Lesen, kein Netzwerk)                      |
| Genauigkeit   | Schätzung liegt bei HIGH-Konfidenz innerhalb ±50 % des tatsächlichen Werts (Ziel v1)    |
| Portabilität  | Ausschließlich SQLite (`evaluations.db`) und Standard-Library Math – keine ML-Frameworks |
| Transparenz   | Ausgabe enthält immer die k Vergleichspunkte (nachvollziehbar, keine Blackbox)           |
| Privatsphäre  | Historische Token-Daten verlassen nie das lokale Filesystem (kein Cloud-Upload)           |

## 7. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Token-Kostenschätzung

  Scenario: Schätzung mit genügend historischen Daten
    Given mindestens 3 historische Token-Datenpunkte in evaluations.db
    When `sdd estimate SPEC-0005` ausgeführt wird
    Then wird eine Schätzung mit Konfidenz MEDIUM oder HIGH ausgegeben
    And die 3 nächsten Vergleichs-Specs werden angezeigt

  Scenario: Schätzung bei wenig Daten
    Given weniger als 3 historische Token-Datenpunkte in evaluations.db
    When `sdd estimate SPEC-0005` ausgeführt wird
    Then wird die Schätzung mit Konfidenz LOW und Warnung ausgegeben

  Scenario: Budget-Alarm
    Given budget_alert_usd ist auf 2.00 konfiguriert
    And die Schätzung für SPEC-0005 ergibt 3.50 USD
    When `sdd estimate SPEC-0005` ausgeführt wird
    Then wird eine WARNING-Box "Schätzung überschreitet Budget (3.50 USD > 2.00 USD)" angezeigt

  Scenario: Token-Verbrauch wird gespeichert
    Given eine laufende LLM-Komponente (z.B. AI-Routes)
    When eine Spec-Generierung abgeschlossen wird
    Then wird ein Eintrag in token_usage mit spec_id, component und token_counts gespeichert

  Scenario: Estimate --all ohne Daten
    Given ein leeres evaluations.db
    When `sdd estimate --all` ausgeführt wird
    Then wird für alle Specs Konfidenz LOW ausgegeben
    And die Gesamtsumme ist als Schätzung markiert
```

## 8. Edge Cases & Fehlerfälle

- **E-01:** `evaluations.db` fehlt (Erstlauf) → leere Tabelle, alle Schätzungen mit LOW-Konfidenz.
- **E-02:** Spec hat 0 Contracts und 0 User Stories → Feature-Vektor ist minimal; Schätzung basiert auf reiner `body_chars`-Ähnlichkeit mit LOW-Konfidenz.
- **E-03:** Model-ID nicht in `cost_estimation.model_prices` → Fallback auf `default`-Preis mit Hinweis in der Ausgabe.
- **E-04:** DB korrupt oder gesperrt → Fehlermeldung, `sdd estimate` gibt Fallback-Schätzung (Durchschnitt aller bekannten Specs) mit Warnung.
- **E-05:** `budget_alert_usd` nicht konfiguriert → kein Alert (Warnung ist optional).

## 9. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert?                                                |
|-------------|----------|---------------------------------------------------------------------|
| TBD         | data     | Schema der `token_usage`-Tabelle in `evaluations.db`               |
| TBD         | behavior | Schätzmethode: k=3 Nearest Neighbor, normalisierte Features         |
| TBD         | data     | Schema des `estimate --json`-Outputs                                |
| TBD         | data     | Schema der `cost_estimation`-Konfigurationssektion                  |

## 10. Tests (wie wird verifiziert)

| Test-ID | Level    | Was prüft der Test?                                                                    |
|---------|----------|----------------------------------------------------------------------------------------|
| TBD     | unit     | Feature-Extraktion: korrekte Zählung von US-, FR-, Contract-, Test-Einträgen           |
| TBD     | unit     | Nearest-Neighbor: k=3 nächste aus bekanntem Datensatz (exakte Kontrollrechnung)        |
| TBD     | unit     | Konfidenz-Level: < 3 Punkte → LOW, 3–9 → MEDIUM, ≥ 10 → HIGH                         |
| TBD     | unit     | Budget-Alert wird ausgegeben wenn Schätzung > `budget_alert_usd`                       |
| TBD     | unit     | Token-Persistenz: nach LLM-Aufruf ist Eintrag in `token_usage` gespeichert            |
| TBD     | unit     | `estimate --json` gibt schema-valides JSON aus                                          |
| TBD     | acceptance | Gherkin-Szenarien aus §7 vollständig durchgespielt                                  |

## 11. Offene Fragen

- [ ] Sollen auch Cache-Read-Tokens separat in die USD-Berechnung einfließen?
- [ ] Welches Gewicht sollen die einzelnen Features in der Nearest-Neighbor-Berechnung erhalten (gleiche Gewichtung vs. gelernte Gewichte)?
- [ ] Soll `sdd estimate` auch die geschätzte Dauer (basierend auf historischen `duration_ms`) ausgeben?
- [ ] Integration mit SPEC-0012 (Nachrichtenserver): Kostenschätzung auf Anfrage über den Message-Kanal liefern?

## 12. Änderungshistorie

| Datum      | Version | Autor | Änderung              |
|------------|---------|-------|-----------------------|
| 2026-05-14 | 0.1.0   | Boris | Initiale Erstellung   |
