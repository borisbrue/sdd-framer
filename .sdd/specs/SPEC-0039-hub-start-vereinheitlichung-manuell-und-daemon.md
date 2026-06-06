---
id: SPEC-0039
title: Hub-Start-Vereinheitlichung — sdd hub start als manueller Pfad, sdd hub install
  als Daemon-Pfad
type: feature
status: implemented
owner: borisbrue
created: 2026-06-06
updated: '2026-06-06'
version: 0.1.0
priority: medium
tags:
- hub
- cli
- refactoring
- daemon
- systemd
depends_on:
- SPEC-0003
- SPEC-0038
contracts:
- CON-0144
- CON-0145
- CON-0146
tests:
- TST-0167
- TST-0168
- TST-0169
adrs: []
started_at: '2026-06-06T14:48:48Z'
---
# Hub-Start-Vereinheitlichung — sdd hub start als manueller Pfad, sdd hub install als Daemon-Pfad

## 1. Kontext & Motivation

SPEC-0038 hat einen neuen Hub-Daemon eingeführt (`hub/app.py`) mit
File-based Registry, Start/Stop-Control und SSE-Streams. Dieser neue Hub
wird über `sdd hub run` gestartet — ein Befehlsname, der nach internem
Werkzeug klingt und primär für den systemd-ExecStart gedacht ist.

Parallel existiert `sdd hub start` weiterhin — dieser Befehl startet
jedoch die **alte** Hub-Implementierung (`web/api/main.py`, In-Memory-Registry,
Auto-Register-Protokoll). Ergebnis: zwei Befehle, zwei unterschiedliche
Implementierungen, zwei unterschiedliche API-Oberflächen.

Das führt zu Verwirrung:
- Ein Nutzer der `sdd hub start` aufruft erhält nicht den neuen Hub aus SPEC-0038
- Ein Nutzer der `sdd hub run` aufruft denkt, er startet etwas Internes
- Manueller Betrieb (ohne systemd) und Daemon-Betrieb nutzen unterschiedlichen Code

Ziel ist eine klare, symmetrische Struktur: `sdd hub start` für manuellen
Vordergrundbetrieb, `sdd hub install` für den systemd-Daemon — beide über
dieselbe `hub/app.py`.

## 2. Zielsetzung

**Primärziel:**
`sdd hub start` und der systemd-Daemon nutzen dieselbe Implementierung
(`hub/app.py`). Der Nutzer wählt nur zwischen zwei Betriebsmodi — manuell
oder dauerhaft — nicht zwischen zwei unterschiedlichen Hub-Varianten.

**Erfolgskriterien (messbar):**
- [ ] `sdd hub start` startet `hub/app.py` im Vordergrund auf Port 4711
      (Standard), blockiert bis Strg+C, identisches Verhalten zum Daemon
- [ ] `sdd hub install` installiert den systemd-User-Service und bleibt
      der einzige Einstiegspunkt für dauerhaften Betrieb
- [ ] `sdd hub run` bleibt erhalten als interner Befehl für systemd
      ExecStart — erscheint nicht im primären Help-Text (`hidden=True`)
- [ ] Die alte `start_hub()`-Funktion (web/api) wird nicht mehr über
      einen Hub-Befehl exponiert; `sdd ui` kann sie intern weiter nutzen
- [ ] `sdd hub start --help` zeigt Port 4711 als Default

**Nicht-Ziele:**
- Keine Änderungen an `web/api/routes/hub.py` (alte In-Memory-Registry
  bleibt für den `sdd ui` Auto-Register-Flow erhalten)
- Keine neuen Features im Hub selbst (Start/Stop/SSE/WebUI bleiben wie in
  SPEC-0038 definiert)
- Kein Umbau des `sdd ui` → Hub Auto-Register-Protokolls
- Kein Entfernen von `sdd hub run` (systemd-Unit-Datei referenziert ihn)

## 3. Architektur & Design Patterns

### Facade Pattern
[Refactoring Guru – Facade](https://refactoring.guru/design-patterns/facade)

`sdd hub start` und `sdd hub run` sind Fassaden über dieselbe
`create_app()`-Fabrik aus `hub/app.py`. Der Nutzer sieht zwei
intentionsbezogene Einstiegspunkte (manuell / systemd), dahinter liegt
ein einziger uvicorn-Start. Bisher war `hub start` eine Fassade über eine
andere, veraltete Implementierung — das wird korrigiert.

### Strategy Pattern
[Refactoring Guru – Strategy](https://refactoring.guru/design-patterns/strategy)

Der Hub kennt zwei Betriebsstrategien: **Foreground** (Strg+C, kein
Restart) und **Daemon** (systemd, Restart=on-failure). Die Strategie
bestimmt nur den Lebenszyklusrahmen — die Hub-Logik (`hub/app.py`) ist
identisch. `hub_start()` implementiert die Foreground-Strategie,
systemd übernimmt die Daemon-Strategie.

## 4. Funktionale Anforderungen

**FR-01 — sdd hub start startet neuen Hub im Vordergrund**
`sdd hub start [--port INTEGER] [--no-browser]` startet `hub/app.py`
via uvicorn im aufrufenden Terminal. Der Prozess blockiert; Strg+C
fährt ihn sauber herunter. Standard-Port: 4711. Vor dem Start prüft
der Befehl ob Port 4711 bereits belegt ist; falls ja, wird eine Warnung
ausgegeben (kein Hard-Stop — der Nutzer kann mit einem anderen Port
fortfahren oder den Konflikt selbst auflösen).

**FR-02 — sdd hub start öffnet Browser (optional)**
Ohne `--no-browser` öffnet der Befehl nach erfolgreichem Start
automatisch die Hub-WebUI im Standardbrowser (`/hub/`-Route).

**FR-03 — sdd hub run bleibt hidden**
`sdd hub run` behält seine bisherige Signatur und Funktion, wird aber
mit `hidden=True` in Click markiert, damit er nicht im primären
`sdd hub --help` erscheint. Die systemd-Unit-Datei referenziert ihn weiter.

**FR-04 — sdd hub install bleibt unverändert**
`sdd hub install` bleibt der einzige Einstiegspunkt für dauerhaften
Betrieb (systemd-User-Service anlegen, aktivieren, starten).

**FR-05 — Alte start_hub() nicht mehr über Hub-Befehle erreichbar**
Die Funktion `start_hub()` aus `ui.py` wird nicht mehr von einem
`sdd hub`-Befehl aufgerufen. Sie bleibt im Code erhalten, da `sdd ui`
sie intern für den Auto-Register-Flow weiterverwendet.

## 5. User Stories

**Story 1 — Manueller Hub-Start (Entwicklung / Test)**
*Als Entwickler möchte ich den Hub schnell im Terminal starten können,
ohne einen systemd-Service einzurichten, damit ich Projekte ad-hoc
kontrollieren kann.*

Akzeptanzkriterium: `sdd hub start` startet den Hub, zeigt die URL,
öffnet den Browser. Strg+C beendet sauber.

**Story 2 — Konsistenz zwischen manuellem und Daemon-Betrieb**
*Als Nutzer möchte ich, dass `sdd hub start` und der systemd-Daemon
dieselbe API-Oberfläche und dasselbe Verhalten zeigen, damit ich beim
Wechsel zwischen den Modi keine Unterschiede bemerke.*

Akzeptanzkriterium: Ein mit `sdd hub start` gestarteter Hub antwortet
auf `/hub/projects`, `/hub/projects/{id}/start`, `/hub/projects/stream`
identisch zum Daemon.

## 6. Contracts

*(werden nach Review angelegt)*

## 7. Tests

*(werden nach Contract-Approval angelegt)*

## 8. Implementierungsreihenfolge

1. `main.py` — `hub_start()` auf `hub/app.py`-Start umstellen (uvicorn
   direkt, nicht mehr `start_hub()` aus `ui.py`)
2. `main.py` — `hub_run()` mit `hidden=True` markieren
3. Browser-Öffnen nach Hub-Start implementieren (analog zu `sdd ui`)
4. Tests anpassen / ergänzen

## 9. Offene Fragen

- [x] Soll `sdd hub start` beim Start prüfen ob der systemd-Service bereits
      läuft, und den Nutzer warnen (Port-Konflikt auf 4711)? → Warnung ausgeben,
      kein Hard-Stop; der Nutzer entscheidet selbst ob er fortfährt.
- [x] Soll `--no-browser` auch beim Daemon (`sdd hub install`) relevant
      sein, oder nur beim manuellen Start? → Nur beim manuellen `sdd hub start`.

## 10. Änderungshistorie

| Version | Datum      | Änderung        |
|---------|------------|-----------------|
| 0.1.0   | 2026-06-06 | Initiale Version |
