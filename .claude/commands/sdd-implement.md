<!-- skill: sdd-implement | version: 0.4.1 | sdd-blueprint: true | updated: 2026-06-03 -->

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

## Schritt 1b: Auto-Approve + Container starten

**Approve (automatisch, wenn noch nicht in-progress):**
Falls `status` ≠ `in-progress`, führe automatisch aus:
```bash
sdd spec approve $ARGUMENTS
```
`▶ sdd spec approve $ARGUMENTS`

Falls der Befehl fehlschlägt: zeige Fehler-Output und abbrechen mit:
"✗ Approve fehlgeschlagen – Contracts oder Tests fehlen vermutlich. Prüfe '/sdd-review $ARGUMENTS'."

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

## Schritt 2: Kontext laden (Allowlist – kein Holdout)
Lese folgende Dateien (und NUR diese):
1. `.sdd/specs/$ARGUMENTS-*.md` – vollständiger Spec-Inhalt
2. Alle CON-IDs aus `contracts:`-Frontmatter → zugehörige Contract-Dateien in `.sdd/contracts/`
3. `.sdd/patterns/$ARGUMENTS-patterns.json` – falls vorhanden
4. `AGENTS.md` – falls vorhanden (zeige [WARN] wenn fehlend)
5. Test-Stub-Dateien: `tests/**/test_tst_*.py` oder Dateien aus TST-`artifact`-Feldern

**Nicht lesen:** `.sdd/holdout/` – nie, unter keinen Umständen.

Fasse den geladenen Kontext kurz zusammen:
- Spec: Titel, Status, N Contracts, M Test-Stubs
- Contracts: [CON-IDs]
- Pattern-Register: [Pattern-Namen falls vorhanden]

## Schritt 3: Implementierungsplan via Decompose laden
```bash
sdd decompose $ARGUMENTS --yes
```
`▶ sdd decompose $ARGUMENTS`

Falls die Task-Liste leer ist (0 Tasks):
"✗ Keine Tasks gefunden – prüfe Spec-Inhalt." und abbrechen.

**Sub-Agenten-Delegation (Claude-Provider):**
Falls der aktive Provider Claude ist (`llm.ai_routes.provider: claude-cli` oder `anthropic`):
```bash
sdd implement $ARGUMENTS
```
`▶ sdd implement $ARGUMENTS` — startet Sub-Agenten-Loop (SPEC-0035).
Falls `sdd implement` mit `[Fallback: Single-Context-Mode]` antwortet oder nicht verfügbar ist:
weiter mit manuellem TDD-Zyklus (Schritt 4).

**Nicht-Claude-Provider oder manueller Modus:**
Die Tasks aus dem Decompose-Plan werden sequenziell als Implementierungsplan genutzt
(kein `sdd distribute` — das bleibt `sdd orchestrate` vorbehalten).

Zeige den Plan und starte sofort mit der Implementierung — keine Bestätigung erforderlich.

## Schritt 4: TDD-Zyklus

Code wird auf dem Host-Filesystem geschrieben (Read/Edit/Write-Tools).

**CONTAINER_MODE=container:** Tests laufen im Container via `sdd dev exec` — isoliert.
**CONTAINER_MODE=host:** Tests laufen direkt auf dem Host — kein Container nötig.

Für jede logische Einheit im Plan:

1. Schreibe Implementierungscode (auf Basis von Spec + Contracts, NICHT Holdout)
2. Führe Tests aus:
   - Container-Modus:
     ```bash
     sdd dev exec $ARGUMENTS pytest tests/ -x --tb=short
     ```
   - Host-Modus:
     ```bash
     pytest tests/ -x --tb=short
     ```
3. Bei Fehler: analysiere den Traceback, korrigiere den Code, wiederhole
4. Bei >3 Iterationen ohne Fortschritt: stoppe mit Fehlerbericht (was versucht wurde, was fehlschlägt) — kein User-Prompt
5. Bei grünen Tests: weiter zur nächsten logischen Einheit

Zyklus endet wenn alle Test-Stubs ohne `NotImplementedError` durchlaufen.

**Hinweis (nur Container-Modus):** `sdd dev exec` benötigt pip-Setup nur beim ersten Aufruf.
Wenn der Container neu ist, einmalig ausführen:
```bash
sdd dev exec $ARGUMENTS bash -c "pip install -q --no-user --no-cache-dir -e '/workspace/' -e '/workspace/tool/[dev]'"
```

## Schritt 5: Finalisierung

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

## Schritt 6: Holdout-Evaluation

Nach erfolgreichem `sdd finalize` die Holdout-Szenarien evaluieren.

**CONTAINER_MODE=container:** `sdd evaluate` läuft im Dev-Container (API-Key wurde beim Start übergeben).
```bash
sdd dev exec $ARGUMENTS bash -c \
  "pip install -q --no-user --no-cache-dir -e '/workspace/tool/[evaluate]' > /dev/null && \
   sdd evaluate --base-url $SDD_EVAL_BASE_URL --spec $ARGUMENTS"
```

**CONTAINER_MODE=host:** `sdd evaluate` läuft direkt auf dem Host.
```bash
pip install -q -e './tool/[evaluate]' > /dev/null && \
sdd evaluate --base-url $SDD_EVAL_BASE_URL --spec $ARGUMENTS
```

**Retry-Loop (max 3 Versuche, beide Modi):**

| Versuch | Ergebnis | Aktion |
|---------|----------|--------|
| 1–2 | fehlgeschlagen | Traceback analysieren, Code korrigieren, `sdd finalize` + erneut evaluieren |
| 3 | fehlgeschlagen | `--final-attempt` setzen → Status → `evaluation-failed`, Bericht anzeigen, Nutzer informieren |
| beliebig | bestanden | Fertig |

Beim 3. fehlgeschlagenen Versuch `--final-attempt` anhängen (jeweils passend zum Modus).

Der Nutzer sieht dann einen Fehlerbericht und entscheidet ob die Spec überarbeitet
oder die Holdout-Kriterien angepasst werden sollen.

## Konventionen
- Keine Kommentare außer wenn WHY nicht offensichtlich
- SOLID-Regeln aus Pattern-Register beachten
- Keine neuen Tests schreiben – nur vorhandene Stubs implementieren
- Kein automatisches git commit
