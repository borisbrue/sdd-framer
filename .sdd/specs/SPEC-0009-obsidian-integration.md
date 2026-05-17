---
id: SPEC-0009
project: PRJ-0001
title: Obsidian-Integration – Bidirektionale Vault-Synchronisation für LLM-freies Arbeiten
status: implemented
owner: Boris
created: 2026-05-14
updated: 2026-05-14
version: 1.0.0
priority: medium
tags:
- obsidian
- sync
- offline
- markdown
- vault
depends_on: []
contracts:
- CON-0034
- CON-0035
- CON-0036
tests:
- TST-0043
- TST-0044
- TST-0045
- TST-0046
- TST-0047
adrs: []
---
# Obsidian-Integration – Bidirektionale Vault-Synchronisation für LLM-freies Arbeiten

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Das SDD-System erzeugt und verwaltet Specs, Contracts, Tests und ADRs als Markdown-Dateien
mit YAML-Frontmatter. Wenn kein LLM verfügbar ist (offline, kein API-Key, Kostenbudget
ausgeschöpft), kann der Entwickler diese Artefakte nicht mit dem gewohnten Tooling bearbeiten.

Obsidian ist ein lokal-first Markdown-Editor mit mächtiger Verlinkung (Wiki-Links, Graph-View)
und funktioniert vollständig offline. Eine Obsidian-Vault-Synchronisation erlaubt:
- Manuelles Editieren von Specs/Contracts in einer angenehmen Oberfläche ohne LLM
- Navigation über ID-basierte Wiki-Links (z. B. `[[SPEC-0001]]` → `[[CON-0001]]`)
- Rückschreiben der Änderungen in das SDD-Projekt, sodass sie beim nächsten LLM-Einsatz
  korrekt aufgegriffen werden

Außerdem legt die Integration die Basis für SPEC-0012 (Nachrichtenserver): Obsidian kann als
Kommunikations-Frontend zum SDD-System dienen.

## 2. Zielsetzung

**Primärziel:**
SDD-Artefakte werden in einen Obsidian-Vault exportiert und nach manuellen Edits
(Frontmatter, Body) wieder in das Projekt importiert, ohne Datenverlust und ohne LLM.

**Erfolgskriterien (messbar):**
- [ ] `sdd obsidian export` legt alle Specs/Contracts/Tests/ADRs als Obsidian-kompatible
      `.md`-Dateien im konfigurierten Vault-Pfad ab
- [ ] Wiki-Links zwischen Artefakten (`[[SPEC-0001]]`) werden beim Export automatisch erzeugt
- [ ] `sdd obsidian import` liest geänderte Dateien aus dem Vault und schreibt sie ins Projekt zurück;
      Conflicts (beide Seiten geändert) werden gemeldet, nicht still überschrieben
- [ ] `sdd obsidian watch` beobachtet den Vault auf Dateiänderungen und importiert automatisch (inotify/polling)
- [ ] YAML-Frontmatter bleibt nach Export→Edit→Import integer; kein Verlust von Pflichtfeldern
- [ ] Vault-Pfad ist über `.sdd/config.yaml` konfigurierbar

**Nicht-Ziele (explizit):**
- Kein Obsidian-Plugin (reine Filesystem-Synchronisation über die offizielle Vault-Struktur)
- Kein Sync von `.sdd/`-Konfigurationsdateien oder Python-Quellcode
- Kein automatisches Erstellen von Specs/Contracts aus Obsidian (nur Bearbeitung bestehender)
- Kein Remote-Sync (iCloud, Obsidian Sync) – ausschließlich lokales Filesystem

## 3. User Stories

| ID    | Als ...    | möchte ich ...                                                         | um ...                                                           |
|-------|------------|------------------------------------------------------------------------|------------------------------------------------------------------|
| US-01 | Entwickler | alle SDD-Artefakte in meinen Obsidian-Vault exportieren                | offline in einer angenehmen Oberfläche weiterzuarbeiten           |
| US-02 | Entwickler | einen Spec in Obsidian bearbeiten und die Änderungen zurückschreiben   | ohne LLM Frontmatter und Beschreibung pflegen zu können          |
| US-03 | Entwickler | per Wiki-Link von einem Spec zu seinen Contracts navigieren            | Zusammenhänge im Graph-View zu verstehen                         |
| US-04 | Entwickler | Konflikte beim Import gemeldet bekommen                                | keine versehentlichen Überschreibungen zu riskieren              |
| US-05 | Entwickler | den Vault-Pfad in config.yaml eintragen                                | Integration einmalig konfigurieren und dann ohne Flags nutzen    |

## 4. Funktionale Anforderungen

### Export

- **FR-01:** `sdd obsidian export [--vault PATH]` schreibt alle Artefakte aus `specs/`, `contracts/`, `tests/`, `docs/adr/` in Unterordner des Vault: `SDD/specs/`, `SDD/contracts/`, `SDD/tests/`, `SDD/adrs/`. Existierende Vault-Dateien werden nur überschrieben wenn die Projekt-Version neuer ist (Vergleich über `updated:`-Frontmatter-Feld).
- **FR-02:** Beim Export werden alle referenzierten IDs im Body (`SPEC-XXXX`, `CON-XXXX`, `TST-XXXX`, `ADR-XXXX`) in Wiki-Links umgewandelt: `SPEC-0001` → `[[SPEC-0001-user-login]]` (Dateiname ohne `.md`-Erweiterung).
- **FR-03:** Eine Obsidian-Indexdatei `SDD/index.md` wird erzeugt mit einer formatierten Übersicht aller Artefakte als Wiki-Link-Liste, gruppiert nach Typ.
- **FR-04:** `sdd obsidian export --dry-run` zeigt an, welche Dateien angelegt/aktualisiert würden, ohne zu schreiben.

### Import

- **FR-05:** `sdd obsidian import [--vault PATH]` liest alle `.md`-Dateien aus `SDD/` im Vault, parst YAML-Frontmatter und Body, und schreibt sie in die entsprechenden Projekt-Verzeichnisse zurück.
- **FR-06:** Vor dem Überschreiben einer Projekt-Datei prüft Import: wenn beide Seiten (Vault und Projekt) seit dem letzten Export geändert wurden, wird die Datei als Conflict markiert und **nicht** überschrieben. Conflicts werden in `.sdd/obsidian-conflicts.yaml` festgehalten.
- **FR-07:** Import akzeptiert nur Dateien, deren `id:`-Frontmatterfeld mit dem erwarteten Muster (`SPEC-\d{4}`, `CON-\d{4}`, `TST-\d{4}`, `ADR-\d{4}`) übereinstimmt. Unbekannte IDs → Warnung, kein Import.
- **FR-08:** Wiki-Links im importierten Body werden zurück in reine IDs konvertiert (`[[SPEC-0001-user-login]]` → `SPEC-0001`).

### Watch

- **FR-09:** `sdd obsidian watch [--vault PATH] [--interval SECS]` startet eine Polling-Schleife (Default: 5 Sekunden), die geänderte Vault-Dateien automatisch importiert. Konflikte werden geloggt (nicht automatisch aufgelöst).
- **FR-10:** `watch` reagiert auf `SIGINT` (Ctrl+C) mit sauberem Shutdown.

### Konfiguration

- **FR-11:** `.sdd/config.yaml` erhält eine neue Sektion:
  ```yaml
  obsidian:
    vault_path: "~/Documents/MyVault"   # Pflicht, wenn nicht via --vault übergeben
    subfolder: "SDD"                    # Optionaler Unterordner im Vault; Default "SDD"
    watch_interval_secs: 5              # Default für `sdd obsidian watch`
    auto_wiki_links: true               # Wiki-Links beim Export erzeugen; Default true
  ```

## 5. Nicht-funktionale Anforderungen

| Kategorie     | Anforderung                                                                                      |
|---------------|--------------------------------------------------------------------------------------------------|
| Portabilität  | Ausschließlich Standard-Library + `watchdog`-Paket für Watch-Modus; kein Obsidian-API-Zugriff   |
| Korrektheit   | YAML-Frontmatter nach Import muss schema-valide sein (`sdd validate` muss grün bleiben)         |
| Sicherheit    | Nur Dateien innerhalb des konfigurierten `vault_path` werden gelesen/geschrieben (kein Traversal)|
| Performance   | Export von 100 Artefakten in < 2 Sekunden                                                       |
| Idempotenz    | Mehrfaches `sdd obsidian export` ohne zwischenzeitliche Änderungen erzeugt identische Dateien   |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Obsidian Vault Synchronisation

  Scenario: Export aller Artefakte in einen Vault
    Given ein SDD-Projekt mit SPEC-0001 und CON-0001
    And ein konfigurierter Vault-Pfad in config.yaml
    When der Entwickler `sdd obsidian export` ausführt
    Then existieren SDD/specs/SPEC-0001-user-login.md und SDD/contracts/CON-0001-*.md im Vault
    And SPEC-0001 enthält Wiki-Link [[CON-0001-*]] für jede referenzierte Contract-ID
    And SDD/index.md enthält Links auf alle exportierten Artefakte

  Scenario: Import nach manuellem Edit ohne Conflict
    Given SPEC-0001 wurde exportiert und danach im Vault bearbeitet
    And das Projekt-SPEC-0001 wurde seit dem Export nicht verändert
    When der Entwickler `sdd obsidian import` ausführt
    Then wird specs/SPEC-0001-user-login.md mit dem Vault-Inhalt überschrieben
    And das `updated:`-Feld enthält das heutige Datum

  Scenario: Conflict-Erkennung bei beidseitiger Änderung
    Given SPEC-0001 wurde exportiert
    And SPEC-0001 wurde sowohl im Vault als auch im Projekt verändert
    When der Entwickler `sdd obsidian import` ausführt
    Then wird SPEC-0001 nicht überschrieben
    And .sdd/obsidian-conflicts.yaml enthält SPEC-0001 als Conflict-Eintrag
    And der Exit-Code ist 1

  Scenario: Watch-Modus importiert automatisch
    Given `sdd obsidian watch` läuft
    When eine Vault-Datei geändert wird
    Then wird die Änderung innerhalb von `watch_interval_secs` ins Projekt importiert

  Scenario: Fehlender Vault-Pfad
    Given kein `obsidian.vault_path` in config.yaml und kein --vault Flag
    When `sdd obsidian export` ausgeführt wird
    Then wird ein Fehler "obsidian.vault_path nicht konfiguriert" ausgegeben
    And der Exit-Code ist 2
```

## 7. Edge Cases & Fehlerfälle

- **E-01:** Vault-Verzeichnis existiert nicht → Fehlermeldung mit Pfad, Exit-Code 2.
- **E-02:** Vault-Datei hat ungültiges YAML-Frontmatter → Warnung, Datei wird beim Import übersprungen.
- **E-03:** Obsidian hat die Vault-Datei gesperrt (Dateisperre) → Retry nach 1 Sekunde, dann Warnung.
- **E-04:** `id:` im Vault stimmt nicht mit Dateiname überein → Warnung, kein Import, Eintrag in `.sdd/obsidian-warnings.log`.
- **E-05:** `vault_path` zeigt auf Unterverzeichnis des SDD-Projekts → `ValueError` (Cycle-Prevention).

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert?                                      |
|-------------|----------|-----------------------------------------------------------|
| TBD         | behavior | Export-Dateistruktur und Wiki-Link-Format                 |
| TBD         | behavior | Import-Conflict-Erkennung und `.sdd/obsidian-conflicts.yaml`-Schema |
| TBD         | data     | Schema der `obsidian`-Konfigurationssektion               |

## 9. Tests (wie wird verifiziert)

| Test-ID | Level    | Was prüft der Test?                                                             |
|---------|----------|---------------------------------------------------------------------------------|
| TBD     | unit     | Wiki-Link-Konvertierung: ID → `[[slug]]` und zurück                             |
| TBD     | unit     | Conflict-Erkennung: beide Seiten geändert → Conflict; nur eine Seite → kein Conflict |
| TBD     | unit     | Import überspringt Dateien mit ungültigem `id:`-Muster                          |
| TBD     | unit     | Path-Traversal-Schutz: Vault-Pfad außerhalb des konfigurierten Ordners → ValueError |
| TBD     | unit     | Idempotenz: zweiter Export ohne Änderungen erzeugt identische Dateien            |
| TBD     | acceptance | Gherkin-Szenarien aus §6 vollständig durchgespielt                            |

## 10. Offene Fragen

- [ ] Soll `sdd obsidian export` auch Template-Metadaten (z.B. Obsidian-Properties via `---`) ergänzen, damit der Graph-View ID-basierte Verlinkung versteht?
- [ ] Soll die Obsidian-`index.md` auch eine Traceability-Matrix als Tabelle enthalten (wie `docs/traceability.md`)?
- [ ] Sync-Strategie für umbenannte Dateien: wenn ein Spec-Titel geändert wird, ändert sich der Dateiname – wie werden alte Vault-Dateien aufgeräumt?
- [ ] Integration mit SPEC-0012 (Nachrichtenserver): Vault-Änderungen als Events publizierten?

## 11. Änderungshistorie

| Datum      | Version | Autor | Änderung              |
|------------|---------|-------|-----------------------|
| 2026-05-14 | 0.1.0   | Boris | Initiale Erstellung   |
