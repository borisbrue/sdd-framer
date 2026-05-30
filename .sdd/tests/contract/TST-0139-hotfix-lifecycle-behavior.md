---
id: TST-0139
project: ""                # PRJ-XXXX
title: "Hotfix Lifecycle Behavior"
level: contract
spec: SPEC-0031
contract: CON-0120
status: planned
framework: "behave"
artifact: "tests/contract/test_tst_0139_hotfix_lifecycle_behavior.feature"
tags: []
---

# Test: Hotfix Lifecycle Behavior

> **Level:** contract · **Spec:** SPEC-0031 · **Contract:** CON-0120 · **Status:** planned

## Was wird geprüft?

Ob die vier Hotfix-CLI-Kommandos (`start`, `finalize`, `abort`, `list`) die
Zustandsübergänge und Seiteneffekte aus CON-0120 korrekt einhalten: keine
LLM-Calls beim Start, korrekter Commit-Hash nach finalize, Schutz vor
Doppel-finalize, unveränderter Git-Index nach abort.

## Vorbedingungen

- `sdd` CLI im PATH verfügbar
- Git-Repository mit sauberem Working Tree vorhanden (Temp-Repo als Fixture)
- Mindestens eine staged Änderung für finalize-Tests

## Ablauf

1. `sdd hotfix start "Falscher Defaultwert"` ausführen, Zeit messen
2. Record-Datei lesen, Status und Felder prüfen
3. Änderung stagen, `sdd hotfix finalize HF-XXXX` ausführen
4. Record-Datei erneut lesen, Git-Log prüfen
5. `sdd hotfix finalize HF-XXXX` ein zweites Mal aufrufen (Doppel-finalize)
6. Neuen offenen Record anlegen, `sdd hotfix abort HF-XXXX` ausführen
7. Git-Index vor und nach abort vergleichen
8. `sdd hotfix list` aufrufen und Ausgabe prüfen

## Erwartetes Ergebnis

- Schritt 1: Befehl schließt in < 3 Sekunden ab; kein LLM-Call (kein API-Request)
- Schritt 2: Record hat `status: open`, `commit: ""`, alle 5 Pflichtfelder gesetzt
- Schritt 3: Record hat `status: done`, `commit` = 40-Zeichen-Hash des neuen Commits
- Schritt 4: Git-Log zeigt genau einen neuen Commit mit den gestagten Änderungen
- Schritt 5: Exit-Code 1; Record bleibt `status: done`; kein zweiter Commit
- Schritt 6: Record hat `status: aborted`; kein neuer Commit
- Schritt 7: Git-Index identisch vor und nach abort
- Schritt 8: Nur offene Records (status: open) erscheinen in der Ausgabe

## Negativfälle / Edge Cases

- `sdd hotfix finalize` ohne gestagter Änderung → Exit-Code 1, kein leerer Commit
- `sdd hotfix finalize` auf abgebrochenen Record → Exit-Code 1
- `sdd hotfix abort` auf bereits abgeschlossenem Record → Exit-Code 1
- Unbekannte HF-ID → Exit-Code 1 mit verständlicher Fehlermeldung

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0120:

- [ ] INV-01: start < 3 Sekunden, kein LLM-Aufruf, kein Container-Start
- [ ] INV-02: finalize auf done/aborted → Exit-Code 1
- [ ] INV-03: Nach finalize: Commit-Hash im Record, status: done, nur gestagter Inhalt
- [ ] INV-04: abort: status: aborted, kein Commit, Git-Index unverändert
- [ ] INV-05: list zeigt nur offene Records

## Hinweise zur Implementierung

Framework: `behave` (BDD, passend zum Gherkin-Artifact).
Fixture: Temp-Git-Repo mit `.sdd/`-Struktur; nach jedem Szenario zurücksetzen.
LLM-Calls überwachen: Netzwerk-Intercept oder `ANTHROPIC_API_KEY=""` setzen und
prüfen ob kein HTTP-Request ausgeht.
