---
id: SPEC-0021
project: PRJ-0001
title: Isolierte Docker-Entwicklungsumgebung pro Spec
status: implemented
owner: Boris
created: 2026-05-16
updated: '2026-05-16'
version: 0.1.0
priority: medium
tags:
- docker
- isolation
- git
- development-environment
- ci
depends_on: []
contracts:
- CON-0065
- CON-0066
- CON-0067
- CON-0068
tests:
- TST-0074
- TST-0075
- TST-0076
- TST-0077
- TST-0078
adrs: []
started_at: '2026-05-16T21:21:32Z'
---
# Isolierte Docker-Entwicklungsumgebung pro Spec

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Aktuell wird jede Spec direkt im Haupt-Arbeitsverzeichnis entwickelt. Das führt zu:

- **Umgebungskontamination:** Abhängigkeiten eines Features beeinflussen andere Specs
  oder den stabilen Codestand
- **Regressionsgefahr:** Änderungen im Working Tree können unbemerkt andere Bereiche
  brechen, bevor die Spec validiert ist
- **Keine echte Isolation:** `sdd dev start` erzeugt einen Git-Branch, aber keine isolierte
  Laufzeitumgebung — Tests laufen gegen die lokale Entwicklungsumgebung, nicht gegen
  eine reproduzierbare Umgebung

**Die Lösung:** Jede Spec bekommt beim Start automatisch einen Docker-Container.
Der Container enthält das Projekt in einem isolierten Git-Branch. Tests laufen
ausschließlich im Container. Erst wenn alle Contracts erfüllt, alle Tests grün und
keine Regression gegen main vorliegt, wird ein lokaler PR erstellt.

Das Setup der Container-Umgebung selbst (Dockerfile, Base-Image, Netzwerk-Konfiguration)
ist bewusst **nicht** Teil dieser Spec — eine lauffähige Umgebung wird vorausgesetzt.

---

## 2. Zielsetzung

**Primärziel:**
`sdd dev start SPEC-XXXX` startet automatisch einen Docker-Container, richtet einen
isolierten Git-Branch ein und stellt die Entwicklungsumgebung bereit.
Nach grünen Tests + Validierung erstellt `sdd dev pr SPEC-XXXX` einen lokalen PR.

**Erfolgskriterien (messbar):**

- [ ] `sdd dev start SPEC-XXXX` startet Docker-Container + Git-Branch `dev/SPEC-XXXX` atomar
- [ ] Projekt ist im Container via Volume-Mount verfügbar
- [ ] Alle Test-Läufe (`pytest` etc.) werden ausschließlich im Container ausgeführt
- [ ] `sdd dev pr SPEC-XXXX` nach grünen Tests + sauberer Validierung:
      PR-Dokument + Merge-Anleitung (lokal)
- [ ] Alle Contracts erfüllt, alle Tests grün, keine Regression gegen main
- [ ] Container wird nach `sdd dev close SPEC-XXXX` gestoppt und entfernt
- [ ] CI-System kann dieselben `sdd`-Befehle nutzen wie der Entwickler

**Nicht-Ziele:**
- Kein Setup der Container-Umgebung (Dockerfile, Base-Image) — vorausgesetzt
- Keine GitHub-Integration in v0.1 — nur lokales Git-Repository
- Kein Multi-Container-Setup (Services, Datenbanken)
- Kein automatisches `git push` ohne explizite Nutzerbestätigung
- Keine Verwaltung von Container-Registries oder Image-Builds

---

## 3. Architektur & Design

### 3.1 Container-Lifecycle

```
sdd dev start SPEC-XXXX
  ├─ Git: Branch "dev/SPEC-XXXX" aus main erzeugen (lokal)
  ├─ Docker: Container "sdd-dev-spec-xxxx" starten
  │    ├─ Volume: $(pwd) → /workspace (rw)
  │    └─ Env: SPEC_ID=SPEC-XXXX, GIT_BRANCH=dev/SPEC-XXXX
  └─ Status: in-progress

[Entwicklung im Container via /sdd-implement oder sdd dev exec]
  └─ sdd dev exec SPEC-XXXX pytest tests/ -x --tb=short

sdd dev pr SPEC-XXXX
  ├─ Regression-Check: git diff main..dev/SPEC-XXXX
  ├─ sdd validate --file .sdd/specs/SPEC-XXXX-*.md
  ├─ PR-Dokument: .sdd/prs/PR-SPEC-XXXX.md
  └─ Merge-Anleitung ausgeben

sdd dev close SPEC-XXXX
  ├─ docker stop sdd-dev-spec-xxxx && docker rm sdd-dev-spec-xxxx
  └─ Status: implemented | abandoned
```

### 3.2 Design Patterns

#### Facade Pattern (Structural)
**Anwendung:** Die SDD-CLI kapselt alle Docker-Kommandos (`docker run`, `docker exec`,
`docker stop`, `docker rm`) hinter einfachen Befehlen (`sdd dev start`, `sdd dev exec`,
`sdd dev close`). Weder Entwickler noch CI müssen Docker-Details kennen.

**Begründung:** Ohne Facade müsste jeder Nutzer Volume-Mounts, Env-Variablen und
Container-Namen manuell verwalten. Die Facade macht den Workflow reproduzierbar
(OCP: neue Runtimes wie Podman können hinter derselben CLI-Facade ergänzt werden).

**Refactoring Guru:** https://refactoring.guru/design-patterns/facade

#### Strategy Pattern (Behavioral)
**Anwendung:** Die PR-Erstellung ist eine austauschbare Strategie:
- `LocalGitStrategy` (v0.1): Branch + PR-Dokument + Merge-Befehl
- `GitHubStrategy` (v0.2): `gh pr create` — zukünftige Erweiterung

Der Lifecycle-Manager kennt nur das Interface `PRStrategy.create(spec_id)`.

**Begründung:** "Später auf GitHub gehen" ist klassisch Strategy. Das Interface
wird jetzt definiert — OCP: keine Änderung am Core-Code nötig wenn GitHub kommt.

**Refactoring Guru:** https://refactoring.guru/design-patterns/strategy

### 3.3 Git-Isolation

```
main (stabil)
  └─ dev/SPEC-0021  ← sdd dev start erzeugt diesen Branch
       ├─ Volume-Mount im Container: rw
       ├─ Alle Commits landen auf diesem Branch
       └─ sdd dev pr: Merge-Kandidat nach main
```

### 3.4 Namenskonventionen (deterministisch, CI-kompatibel)

```
Container-Name: sdd-{spec-id-lowercase}  →  sdd-dev-spec-0021
Branch-Name:    spec/{SPEC-ID}           →  dev/SPEC-0021
PR-Dokument:    .sdd/prs/PR-SPEC-0021.md
```

---

## 4. Funktionale Anforderungen

**FR-01** `sdd dev start SPEC-XXXX` erzeugt Branch `dev/SPEC-XXXX` aus main und startet
Container `sdd-dev-spec-xxxx` atomar (beide oder keiner — Rollback bei Fehler).

**FR-02** Container-Start mit: `-v $(pwd):/workspace -e SPEC_ID=... -e GIT_BRANCH=...`
Base-Image konfigurierbar in `.sdd/config.yaml` (`docker.image: sdd-dev:latest`).

**FR-03** `sdd dev exec SPEC-XXXX <befehl>` führt Befehl im laufenden Container aus
(`docker exec sdd-dev-spec-xxxx <befehl>`). `/sdd-implement` nutzt intern diesen Mechanismus.

**FR-04** Alle Test-Läufe laufen ausschließlich via `sdd dev exec` im Container.
Direktes `pytest` auf dem Host ist kein Teil des SDD-Workflows.

**FR-05** `sdd dev pr SPEC-XXXX` führt aus:
1. Uncommitted-Changes-Check (Warnung, kein Auto-Commit)
2. `git diff main..dev/SPEC-XXXX --stat` (Regression-Check)
3. `sdd validate` + alle verlinkten Contracts prüfen
4. PR-Dokument `.sdd/prs/PR-SPEC-XXXX.md` generieren
5. Merge-Anleitung ausgeben

**FR-06** `sdd dev close SPEC-XXXX` stoppt + entfernt Container.
`--delete-branch` löscht zusätzlich den Git-Branch.

**FR-07** Idempotenz: `sdd dev start` mit bereits aktivem Container → Warnung + Abbruch,
kein zweiter Container. Gestoppter Container wird wieder gestartet.

**FR-08** PR-Strategie konfigurierbar in `.sdd/config.yaml`:
```yaml
pr_strategy: local   # Optionen: local | github (v0.2)
docker:
  image: sdd-dev:latest
```

---

## 5. User Stories

| ID | Als … | möchte ich … | damit … |
|---|---|---|---|
| US-01 | Entwickler | mit `sdd dev start SPEC-XXXX` automatisch einen isolierten Container starten | ich sofort in einer reproduzierbaren Umgebung entwickeln kann |
| US-02 | Entwickler | Tests ausschließlich im Container ausführen | lokale Umgebungsunterschiede keine Rolle spielen |
| US-03 | Entwickler | mit `sdd dev pr SPEC-XXXX` einen lokalen PR erstellen | der Code erst nach vollständiger Validierung in main gemerged wird |
| US-04 | CI-System | dieselben `sdd`-Befehle wie der Entwickler nutzen | CI-Lauf und lokale Entwicklung identisch sind |
| US-05 | Entwickler | mit `sdd dev close SPEC-XXXX` aufräumen | keine verwaisten Container das System belasten |

---

## 6. Contracts

_(werden in eigenen CON-Dokumenten ausgearbeitet)_

| Contract-ID | Typ | Was wird garantiert? |
|---|---|---|
| CON-0065 | behavior | `sdd dev start/exec/close` – atomarer Lifecycle, Idempotenz, Volume-Mount |
| CON-0066 | behavior | `sdd dev pr` – Validierungsgatter (Tests grün + validate sauber) vor PR-Erstellung |
| CON-0067 | data | PR-Dokument-Schema: Pflichtfelder spec_id, branch, test_result, merge_command |
| CON-0068 | performance | Container-Start < 30 s (Image vorhanden), p95 < 20 s |

---

## 7. Tests

_(werden in eigenen TST-Dokumenten ausgearbeitet)_

| Test-ID | Level | Was prüft der Test? |
|---|---|---|
| TST-0074 | contract | `sdd dev start/exec/close` – alle CON-0065 Garantien (8 Testfälle) |
| TST-0075 | contract | `sdd dev pr` Validierungsgatter – alle CON-0066 Garantien (5 Testfälle) |
| TST-0076 | contract | PR-Dokument Schema-Validierung – CON-0067 Invarianten |
| TST-0077 | acceptance | Vollständiger Flow: start → exec pytest → pr → close |
| TST-0078 | performance | Container-Start < 30 s über 10 Runs (CON-0068) |

---

## 8. Implementierungsreihenfolge

```
Phase A: sdd dev start – Docker + Git
  └─ Container starten + Volume-Mount
  └─ Git-Branch erzeugen
  └─ Idempotenz-Check

Phase B: sdd dev exec – docker exec Wrapper

Phase C: sdd dev pr – LocalGitStrategy
  └─ Regression-Check + Validierung
  └─ PR-Dokument generieren

Phase D: sdd dev close – Container stoppen + entfernen

Phase E: config.yaml – docker.image + pr_strategy

Phase F: Contracts + Tests (eigene Dokumente)

Phase G (v0.2): GitHubStrategy – gh pr create
```

---

## 9. Offene Fragen

- [ ] Soll `sdd dev start` einen gestoppten Container wieder starten oder immer neu erstellen?
      → Vorschlag: gestoppten Container wieder starten (kein erneuter Image-Pull)
- [ ] Wie wird mit Merge-Konflikten umgegangen (main hat sich weiterentwickelt)?
      → v0.1: nur aus aktuellem main branchen; Rebase-Strategie in v0.2
- [ ] Soll `sdd dev pr` automatisch committen wenn uncommitted changes vorliegen?
      → Vorschlag: Warnung ausgeben, kein Auto-Commit

---

## 10. Änderungshistorie

| Datum | Version | Autor | Änderung |
|---|---|---|---|
| 2026-05-16 | 0.1.0 | Boris | Initiale Erstellung |
