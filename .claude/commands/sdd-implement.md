---
scope: tdd-implementation
---
<!-- skill: sdd-implement | version: 0.7.0 | sdd-blueprint: true | updated: 2026-06-09 -->

# /sdd-implement – TDD-Implementierungsphase

## Aufgabe
Implementiere das Feature für die angegebene SPEC vollständig nach TDD.
`$ARGUMENTS` enthält die SPEC-ID (z.B. SPEC-0020).

⚠️ KRITISCH: `.sdd/holdout/` wird NIEMALS gelesen. Kein Holdout-Inhalt darf
in den Implementierungskontext einfließen. Dies sichert die Evaluator-Isolation.

## Schritt 1: Vorbedingungen prüfen

- Existiert `.sdd/config.yaml`? Falls nicht: "Kein SDD-Projekt. 'sdd init' zuerst." und abbrechen.
- Prüfe ob sdd CLI verfügbar: `which sdd`
- Lese Frontmatter der Spec. Falls `status == deprecated`:
  "✗ Spec ist deprecated – Implementierung nicht möglich." und abbrechen.

## Schritt 1b: Auto-Review + Approve + Container starten

**Approve-Pfad (abhängig vom aktuellen Status):**

Lese `status` aus dem Frontmatter der Spec.

**Falls `status == draft` oder `status == review`:**
Spawne einen Subagenten (Agent-Tool) für das vollständige automatische Review:

> Führe das vollständige Review für $ARGUMENTS autonom durch:
>
> 1. `sdd solid-check $ARGUMENTS` — SOLID-Analyse ausgeben; Warnings loggen, keine Blockade
> 2. `sdd pattern-suggest $ARGUMENTS` — sinnvolle Patterns automatisch annehmen (`sdd pattern accept`), alle anderen überspringen
> 3. `sdd regression-check $ARGUMENTS` — bei Severity `error`: Abbruch mit detailliertem Bericht; bei `warning`/`info`: weiter
> 4. Alle Contracts der Spec mit `status: draft` sequenziell reviewen:
>    - Prüfe Messbarkeit, Vollständigkeit, Atomarität, Widersprüche
>    - Setze `status: approved` im Frontmatter wenn inhaltlich ok (Edit-Tool)
>    - Kein interaktiver Bestätigungsschritt — autonom entscheiden
> 5. `sdd spec approve $ARGUMENTS` — nur wenn alle Contracts approved sind
>
> Kein Warten auf Nutzereingabe. Bei Regression-Konflikt (error): Abbruch.

Falls Review-Subagent mit Fehler endet (Regression-Konflikt, fehlende Contracts o.ä.):
Zeige Fehlerbericht und abbrechen mit:
"✗ Automatisches Review fehlgeschlagen – prüfe den Bericht oben und führe '/sdd-review $ARGUMENTS' manuell aus."

**Falls `status == approved`:** führe direkt aus:
```bash
sdd spec approve $ARGUMENTS
```
`▶ sdd spec approve $ARGUMENTS`

Falls der Befehl fehlschlägt: zeige Fehler-Output und abbrechen mit:
"✗ Approve fehlgeschlagen – Contracts oder Tests fehlen vermutlich. Prüfe '/sdd-review $ARGUMENTS'."

**Falls `status == in-progress`:** kein Approve-Schritt nötig.

**Container-Runtime diagnostizieren:**
Lese den konfigurierten Runtime-Namen aus `.sdd/config.yaml` (`docker.runtime`, Standard: `docker`).
Prüfe dann:
```bash
<runtime> info 2>&1 | head -5
```

Falls der Check fehlschlägt, analysiere die Fehlerausgabe:

- Enthält sie `shared libraries` oder `cannot open shared object file`:
  ```
  ✗ Container-Runtime nicht nutzbar: fehlende System-Bibliothek.

  Ursache: Die VS Code Flatpak-Sandbox exponiert Host-Binaries (z.B. podman über
  /run/host/usr/bin/) ohne deren nativen Shared-Library-Pfad. Dadurch schlägt
  'podman info' mit einem Library-Fehler fehl, auch wenn podman installiert ist.

  Optionen:
    A) Claude Code aus einem nativen Terminal starten (empfohlen):
       Konsole/foot/Alacritty öffnen → 'claude' dort starten → podman funktioniert korrekt.
    B) Container-losen Modus aktivieren (Tests laufen direkt auf dem Host):
       Weiter mit --no-container (kein 'sdd dev exec', kein Container nötig).
  ```
  → Frage den Nutzer: "Container-los weitermachen? [J/n]"
  - Bei J (oder Enter): setze **CONTAINER_MODE=host** und weiter mit `sdd start $ARGUMENTS --no-container`
  - Bei n: Abbruch

- Enthält sie `permission denied` oder `connect`:
  ```
  ✗ Container-Runtime nicht erreichbar: Socket-Verbindung fehlgeschlagen.

  Starte den Daemon und versuche erneut:
    systemctl --user start podman.socket   # für Podman (rootless)
    sudo systemctl start docker            # für Docker
  ```
  → Abbruch. Nutzer soll Runtime starten und '/sdd-implement $ARGUMENTS' erneut ausführen.

- Sonstiger Fehler: Fehlertext anzeigen und abbrechen.

Falls der Check erfolgreich ist: setze **CONTAINER_MODE=container** und weiter.

**Container starten (automatisch, nur bei CONTAINER_MODE=container):**
Falls `status` ≠ `in-progress` (wurde gerade approved):
```bash
sdd start $ARGUMENTS
```
`▶ sdd start $ARGUMENTS` (Status → in-progress, Container startet)

Falls `status` bereits `in-progress`: prüfe ob Container läuft:
```bash
<runtime> inspect --format '{{.State.Status}}' sdd-dev-$(echo $ARGUMENTS | tr '[:upper:]' '[:lower:]')
```
Falls nicht `running`: führe ebenfalls `sdd start $ARGUMENTS` aus (Neustart des Containers).

**Container-Ready verifizieren (nur bei CONTAINER_MODE=container):**
Warte 5 Sekunden nach `sdd start`, dann prüfe:
```bash
<runtime> inspect --format '{{.State.Status}}' sdd-dev-$(echo $ARGUMENTS | tr '[:upper:]' '[:lower:]')
```
Falls nicht `running`: nochmals 10 Sekunden warten, erneut prüfen (max. 2 Versuche gesamt).
Falls danach immer noch nicht `running`:
```
✗ Container konnte nicht gestartet werden.
  Diagnose: '<runtime> ps -a' für laufende Container prüfen.
  Manuell starten: 'sdd start $ARGUMENTS'
  Oder container-los: 'sdd start $ARGUMENTS --no-container' → dann Tests auf dem Host ausführen.
```
→ Abbruch.

**Container-loser Start (CONTAINER_MODE=host):**
```bash
sdd start $ARGUMENTS --no-container
```
`▶ sdd start $ARGUMENTS --no-container` (Status → in-progress, kein Container)
Zeige Hinweis: "[WARN] Container-loser Modus aktiv – Tests laufen direkt auf dem Host."

## Schritt 1c: Feature-Branch erstellen
```bash
git checkout -b feat/$ARGUMENTS 2>/dev/null || git checkout feat/$ARGUMENTS
```
`▶ Branch feat/$ARGUMENTS` erstellt oder ausgecheckt (kein Fehler wenn bereits vorhanden).

## Schritt 1.5: Holdout-Szenarien sicherstellen

Prüfe ob HOL-Dateien für diese Spec bereits existieren:
```bash
grep -rl "^spec: $ARGUMENTS" .sdd/holdout/ 2>/dev/null | wc -l
```

Falls **0 Holdouts** gefunden: spawne einen Subagenten (Agent-Tool) zur Generierung.

**Subagent-Auftrag (vollständiger Prompt):**

> Generiere Holdout-Szenarien für $ARGUMENTS.
>
> Lies ausschließlich:
> 1. `.sdd/specs/$ARGUMENTS-*.md` — Spec-Inhalt
> 2. Alle CON-IDs aus `contracts:`-Frontmatter → `.sdd/contracts/**/<CON-ID>-*.md`
>
> Lies nicht: `tool/`, `web/`, `tests/`, `.sdd/holdout/`, `*.py`, `*.ts`, `*.js`
>
> Leite pro Contract 2–4 Szenarien ab (Happy Path + mindestens 1 Fehlerfall).
> Jedes Szenario beschreibt Verhalten aus Nutzerperspektive — kein Implementierungsdetail, kein Code.
>
> Für jedes Szenario:
> ```bash
> sdd new holdout --contract <CON-ID> --spec $ARGUMENTS --title "<Titel>"
> ```
> Befülle die erzeugte Datei sofort mit:
> - `## Input` — Was eingegeben / ausgelöst wird
> - `## Expected` — Was das System zurückgeben / tun muss (konkret, prüfbar)
> - `## Evaluation Hint` — Aufzählung der Prüfpunkte für den Evaluator
>
> Kein Bestätigungsschritt — direkt schreiben.

Nach Abschluss des Subagenten: zeige Anzahl der angelegten HOL-IDs.

Falls Subagent fehlschlägt oder 0 HOL-Dateien erzeugt wurden:
`[WARN] Holdout-Generierung fehlgeschlagen — Schritt 5.5 wird keine Szenarien evaluieren.`

Falls Holdouts bereits existieren: kurz ausgeben wie viele, dann weiter.

---

## Schritt 2: Kontext laden (Allowlist – kein Holdout)
Lese folgende Dateien (und NUR diese):
1. `.sdd/specs/$ARGUMENTS-*.md` – vollständiger Spec-Inhalt
2. Alle CON-IDs aus `contracts:`-Frontmatter → zugehörige Contract-Dateien in `.sdd/contracts/`
3. `.sdd/patterns/$ARGUMENTS-patterns.json` – falls vorhanden
4. `AGENTS.md` – falls vorhanden (zeige [WARN] wenn fehlend)
5. Vorhandene Test-Dateien aus TST-`artifact`-Feldern in `.sdd/tests/`

**Nicht lesen:** `.sdd/holdout/` – nie, unter keinen Umständen.

Fasse den geladenen Kontext kurz zusammen:
- Spec: Titel, Status, N Contracts, M Tests
- Contracts: [CON-IDs]
- Pattern-Register: [Pattern-Namen falls vorhanden]

## Schritt 3: Task-Plan via Decompose laden

```bash
sdd decompose $ARGUMENTS --yes
```
`▶ sdd decompose $ARGUMENTS`

Falls die Task-Liste leer ist (0 Tasks):
"✗ Keine Tasks gefunden – prüfe Spec-Inhalt." und abbrechen.

**Task-Plan anzeigen und validieren:**
Gib für jeden Task aus:
```
[N] <title> (type: code|test|…)
    Test: <test_file> via <test_command>
    Abhängigkeiten: [<dep1>, <dep2>] oder "keine"
```

Prüfe: Hat jeder `type=code`-Task ein `test_file` und `test_command`?
Falls nicht: erweitere den Task manuell um ein sinnvolles `test_file`/`test_command`
(nach denselben Konventionen wie im Decompose-System-Prompt) bevor du weitermachst.

Zeige den Plan und starte sofort – keine Bestätigung erforderlich.

## Schritt 4: Per-Task TDD-Zyklus

⚠️ **KERNREGEL: Jeder `type=code`-Task durchläuft zwingend RED → GREEN.**
Ein Task gilt erst als abgeschlossen wenn sein Test grün ist.
Tasks ohne grünen Test werden NICHT als erledigt markiert.

Code wird auf dem Host-Filesystem geschrieben (Read/Edit/Write-Tools).
Tests laufen je nach CONTAINER_MODE:
- **host**: direkt auf dem Host
- **container**: via `sdd dev exec $ARGUMENTS <cmd>`

### Für JEDEN `type=code`-Task (in Abhängigkeitsreihenfolge):

#### 4a: Test-Datei erstellen (falls noch nicht vorhanden)

Lese `task.test_file`. Falls die Datei noch nicht existiert:

**Erstelle eine ECHTE fehlschlagende Test-Datei** — KEIN `pytest.skip()`, KEIN `pass`.

Der Test muss:
- Die zu implementierende Funktion/Klasse/Modul direkt importieren
- Mindestens eine konkrete Assertion über das erwartete Verhalten machen
- FEHLSCHLAGEN weil der importierte Code noch nicht existiert

Beispiele:

Python (pytest):
```python
# tests/unit/test_connection_monitor.py
from sdd_cli.hub.connection_monitor import ConnectionMonitor

def test_initial_state_unknown():
    m = ConnectionMonitor()
    assert m.state == "unknown"

def test_two_failures_trigger_offline():
    m = ConnectionMonitor()
    m.record_failure()
    m.record_failure()
    assert m.state == "offline"
```

TypeScript (deno) – reine Logik-Extraktion:
```typescript
// web/pwa/src/__tests__/connection_monitor.test.ts
import { ConnectionMonitor, OFFLINE_THRESHOLD } from "../hubLogic.ts";
import { assertEquals } from "https://deno.land/std/assert/mod.ts";

Deno.test("initial state is unknown", () => {
  const m = new ConnectionMonitor();
  assertEquals(m.state, "unknown");
});

Deno.test("two failures trigger offline", () => {
  const m = new ConnectionMonitor();
  m.recordFailure();
  m.recordFailure();
  assertEquals(m.state, "offline");
});
```

**Wichtig für TypeScript/React-Tasks:**
Falls der Task eine React-Komponente betrifft, extrahiere die reine Logik zuerst
in ein separates Modul (z.B. `*Logic.ts` oder `*Store.ts`) und teste dieses Modul.
React-Komponenten ohne DOM-Setup sind schwer testbar — die Logik darunter ist es nicht.

#### 4b: Test RED verifizieren

Führe `task.test_command` aus:

- Host-Modus: direkt ausführen
- Container-Modus: `sdd dev exec $ARGUMENTS <test_command>`

**Erwartetes Ergebnis: Test MUSS fehlschlagen** (ImportError, NameError, AssertionError usw.)

Falls der Test **unerwartet grün** ist: prüfe ob die Test-Datei wirklich das
zu implementierende Modul importiert. Ein grüner Test ohne Implementierung
bedeutet der Test prüft nichts — überarbeite ihn bis er rot ist.

Falls der Test rot ist: ✓ Fortfahren mit 4c.

#### 4c: Implementierung schreiben

Schreibe den Implementierungscode für diesen Task (Spec + Contracts als Grundlage).
Halte den Code minimal — nur was nötig ist damit der Test grün wird.

#### 4d: Test GREEN verifizieren

Führe `task.test_command` erneut aus.

Falls grün: ✓ Task abgeschlossen — weiter mit dem nächsten Task.

Falls rot:
- Analysiere den Traceback
- Korrigiere den Implementierungscode
- Wiederhole 4d (max. 3 Iterationen)
- Nach 3 Iterationen ohne Fortschritt: Fehlerbericht ausgeben und pausieren

#### 4e: Regression-Check

Nach jedem grünen Task: Führe die vollständige Test-Suite aus um Regressionen auszuschließen.

- Host, Python: `pytest tests/ -x --tb=short`
- Host, TypeScript: `npm test` (im jeweiligen Package-Verzeichnis)
- Container: `sdd dev exec $ARGUMENTS pytest tests/ -x --tb=short`

Bei Regression: repariere bevor du zum nächsten Task übergehst.

### Tasks vom type "test", "config", "doc"

Diese Tasks haben kein RED-GREEN-Gate. Führe sie durch und dokumentiere kurz was
erstellt/geändert wurde.

## Schritt 5: Fortschritts-Zusammenfassung

Nach Abschluss aller Tasks:
```
✓ N/N Tasks abgeschlossen
  Task 1: <title> → [test_file] grün
  Task 2: <title> → [test_file] grün
  ...
```

Falls Tasks fehlen (N < Gesamt): liste sie auf und erkläre warum sie blockiert sind.

## Schritt 5.5: Holdout-Gate (Blocker vor Finalize)

Alle Tasks grün — jetzt werden die Holdout-Szenarien tier-spezifisch geprüft.
`sdd finalize` wird erst aufgerufen wenn alle Tiers bestehen.

### 5.5a: Critical-Tier

**CONTAINER_MODE=container:**
```bash
sdd dev exec $ARGUMENTS bash -c \
  "pip install -q --no-user --no-cache-dir -e '/workspace/tool/[evaluate]' > /dev/null && \
   sdd evaluate --base-url $SDD_EVAL_BASE_URL --spec $ARGUMENTS --tier critical"
```

**CONTAINER_MODE=host:**
```bash
pip install -q -e './tool/[evaluate]' > /dev/null && \
sdd evaluate --base-url $SDD_EVAL_BASE_URL --spec $ARGUMENTS --tier critical
```

| Versuch | Ergebnis | Aktion |
|---------|----------|--------|
| 1–2 | fehlgeschlagen | Traceback analysieren, Code korrigieren → zurück zu Schritt 4; Container neu starten |
| 3 | fehlgeschlagen | `--final-attempt` anhängen → Status `evaluation-failed`, Bericht ausgeben, **Abbruch** |
| beliebig | bestanden | → weiter mit 5.5b |

### 5.5b: Normal-Tier

```bash
sdd evaluate --base-url $SDD_EVAL_BASE_URL --spec $ARGUMENTS --tier normal
```
(Gleiches Container/Host-Muster wie 5.5a.)

| Versuch | Ergebnis | Aktion |
|---------|----------|--------|
| 1–2 | fehlgeschlagen | Code korrigieren → zurück zu Schritt 4 |
| 3 | fehlgeschlagen | `--final-attempt` → **Abbruch** |
| beliebig | bestanden | → weiter mit 5.5c |

### 5.5c: Edge-Case-Tier

```bash
sdd evaluate --base-url $SDD_EVAL_BASE_URL --spec $ARGUMENTS --tier edge-case
```

| Versuch | Ergebnis | Aktion |
|---------|----------|--------|
| 1–2 | fehlgeschlagen | Code korrigieren → zurück zu Schritt 4 |
| 3 | fehlgeschlagen | `--final-attempt` → **Abbruch** |
| beliebig | bestanden | → weiter mit Schritt 6 |

---

## Schritt 6: Finalisierung

Führe zuerst `sdd validate` aus und behebe alle Fehler.

⚠️ **`sdd finalize` erstellt automatisch einen Git-Commit** — kein manuelles
`git add` / `git commit` danach nötig. Der `FinalizeReport` enthält den Commit-Hash.

**CONTAINER_MODE=container:**

`sdd finalize` erwartet einen laufenden Container. Falls keiner läuft:
"✗ Dev-Container nicht gefunden – starte ihn mit 'sdd start $ARGUMENTS'"

Versuch 1 und 2:
```bash
sdd finalize $ARGUMENTS
```
Bei fehlgeschlagenen Container-Tests: Traceback analysieren, Code korrigieren,
erneut im Container testen (Schritt 4), dann `sdd finalize $ARGUMENTS` wiederholen.

Dritter fehlgeschlagener Versuch (Container-Fehler) → automatisch:
```bash
sdd finalize $ARGUMENTS --skip-container
```
⚠ Container-Tests wurden übersprungen — Commit und PR laufen normal durch.

**CONTAINER_MODE=host:**

```bash
sdd finalize $ARGUMENTS --skip-container
```
`▶ sdd finalize $ARGUMENTS --skip-container` (kein Container vorhanden – erwartet)

Zeige den `FinalizeReport` (Branch, Commit-Hash, PR-URL oder lokaler PR-Pfad).

## Schritt 6b: FR-Vollständigkeits-Check + PR erstellen

Nach erfolgreichem `sdd finalize`: prüfe ob jedes FR aus der Spec tatsächlich
implementiert ist, bevor der PR erstellt wird.

### 6b-1: FRs aus Spec extrahieren

Lese `.sdd/specs/$ARGUMENTS-*.md`, Abschnitt `## N. Funktionale Anforderungen`.
Extrahiere alle `FR-XX`-Bezeichner mit ihrer Beschreibung.

### 6b-2: Implementierung pro FR prüfen

Für jedes FR: lese die relevanten Code-Dateien (orientiere dich an Contracts,
Task-Beschreibungen und dem Implementierungsabschnitt der Spec) und prüfe ob
das beschriebene Verhalten nachweislich implementiert ist.

Gib eine Tabelle aus:
```
FR-Check: $ARGUMENTS
───────────────────────────────────────────────────────────
FR-01  ✅  FrCoverageSpecification extrahiert FR-IDs  compliance.py:42
FR-02  ✅  Task-Mapping via test_ids                  compliance.py:78
FR-03  ⚠️  TypeAwareTestChecker — stufe-Feld prüft 'stufe', Schema sagt 'level'
FR-04  ✅  RouteRegistrationChecker grep-basiert      compliance.py:190
...
FR-08  ❌  sdd install-hooks installiert Regressions-Hook nicht
───────────────────────────────────────────────────────────
Ergebnis: N/M FRs vollständig implementiert
```

Bewertungskriterien:
- ✅ Code vorhanden, Verhalten entspricht Spec + Contracts
- ⚠️ Implementiert, aber Abweichung vom Spec-Text (Nebenbefund, kein Blocker)
- ❌ FR fehlt oder weicht so stark ab dass das Ziel nicht erreicht wird

### 6b-3: Entscheidung

**Alle FRs ✅ oder ⚠️ (kein ❌):** Fahre mit 6b-4 (PR erstellen) fort.

**Mindestens ein ❌:** Kehre zu Schritt 4 zurück — implementiere die fehlenden
FRs im TDD-Zyklus, dann erneut `sdd finalize` + Schritt 6b.

### 6b-4: PR erstellen

```bash
gh pr create \
  --base main \
  --title "feat($ARGUMENTS): <spec-titel>" \
  --body "$(cat .sdd/prs/PR-$ARGUMENTS.md 2>/dev/null || echo 'Implementierung von $ARGUMENTS')"
```

Falls `.sdd/prs/PR-$ARGUMENTS.md` nicht existiert, nutze dieses Template:

```
## Summary
- Implementiert $ARGUMENTS gemäß Spec und Contracts
- N/M FRs vollständig abgedeckt (alle Tests grün)

## FR-Abdeckung
<FR-Tabelle aus 6b-2 einfügen>

## Test plan
- [ ] `sdd validate` — 0 Fehler
- [ ] Alle Unit-Tests grün
- [ ] sdd finalize erfolgreich

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

Zeige die PR-URL nach erfolgreichem `gh pr create`.


## Konventionen
- Keine Kommentare außer wenn WHY nicht offensichtlich
- SOLID-Regeln aus Pattern-Register beachten
- Tests MÜSSEN vor der Implementierung existieren und rot sein (RED → GREEN ist nicht optional)
- Für jeden `type=code`-Task muss am Ende ein grüner Test existieren
- Reine Logik immer aus React-Komponenten extrahieren bevor Tests geschrieben werden
- Kein automatisches git commit