---
scope: spec-evaluation
---
<!-- skill: sdd-holdout | version: 0.1.0 | sdd-blueprint: true | updated: 2026-05-19 -->

# /sdd-holdout – Holdout-Szenarien generieren

## Aufgabe
Generiere Holdout-Szenarien für die angegebene SPEC — vollständig isoliert vom
Implementierungskontext. `$ARGUMENTS` enthält die SPEC-ID (z.B. SPEC-0020).

⚠️ SICHERHEITS-INVARIANTEN (alle zwingend):
1. **Kein Sourcecode lesen** — nie `tool/`, `web/`, `*.py`, `tests/`, `vscode-extension/`
2. **Kein bestehendes Holdout lesen** — `.sdd/holdout/` bleibt ungelesen (Bias-Vermeidung)
3. **Nie ohne Bestätigung schreiben** — erst nach explizitem "ja" / "ok" / "speichern"
4. **Kein Implementierungsdetail** — Szenarien beschreiben Verhalten, nie Implementierung

## Schritt 1: Vorbedingungen prüfen

- Existiert `.sdd/config.yaml`? Falls nicht: Fehlermeldung und abbrechen.
- Lese Frontmatter der Spec: `.sdd/specs/$ARGUMENTS-*.md`
  - `status` muss `approved` oder `in-progress` sein (nicht `draft`)
  - Extrahiere: `title`, `contracts: [CON-IDs]`
- Falls keine Contracts verknüpft: "Erstelle zuerst Contracts mit `/sdd-new contract`."

## Schritt 2: Kontext laden (strikte Allowlist)

Lese **ausschließlich** diese Dateien:

1. `.sdd/specs/$ARGUMENTS-*.md` — Spec-Inhalt (Motivation, User Stories, Erfolgskriterien)
2. Alle CON-IDs aus `contracts:` → `.sdd/contracts/**/<CON-ID>-*.md` (Garantien, Invarianten, Szenarien)

**Nicht lesen (absolutes Verbot):**
- `tool/`, `web/`, `vscode-extension/`, `tests/` — Sourcecode
- `.sdd/holdout/` — bestehende Holdouts (erzeugt Bias)
- `*.py`, `*.ts`, `*.js` — Implementierungsdetails

Fasse den geladenen Kontext zusammen:
- Spec: Titel, N Contracts
- Contracts: [CON-IDs + Typen]

## Schritt 3: Szenarien ableiten

Für jeden Contract: leite 2–4 Holdout-Szenarien ab.

**Grundregeln für gute Holdouts:**

- **Plain English** — kein Code, keine HTTP-Details, keine internen Variablen
- **Nutzer-Perspektive** — "Ein Nutzer schickt X und erwartet Y"
- **Grenzfälle einschließen** — Happy Path + mindestens 1 Fehlerfall pro Contract
- **Messbar** — das erwartete Ergebnis muss eindeutig prüfbar sein
- **Unabhängig vom Implementierungsweg** — nicht "die Funktion gibt X zurück", sondern "das System antwortet mit X"

**Szenario-Struktur (pro Holdout):**

```
Contract: CON-XXXX
Titel: [prägnant, max. 60 Zeichen]
Beschreibung: [1–2 Sätze, was getestet wird]
Schritte:
  1. [Aktion des Nutzers / Systems]
  2. ...
Erwartetes Ergebnis:
  - [konkret und prüfbar]
Randbedingungen:
  - [Vorbedingungen falls nötig]
```

## Schritt 4: Szenarien zur Bestätigung vorlegen

Zeige **alle** generierten Szenarien übersichtlich — gruppiert nach Contract.
Warte auf eine der folgenden Antworten:

- "ja" / "ok" / "speichern" → alle speichern
- "speichere 1, 3, 5" → nur die genannten speichern
- Nummerierter Kommentar ("Szenario 2: lieber X statt Y") → anpassen, erneut vorlegen
- "abbrechen" → nichts speichern

**Nie speichern ohne explizite Bestätigung.**

## Schritt 5: Szenarien speichern

Für jedes bestätigte Szenario:

```bash
sdd new holdout \
  --contract CON-XXXX \
  --spec $ARGUMENTS \
  --title "Titel des Szenarios"
```

Dann die erzeugte Datei mit dem vollständigen Inhalt befüllen (Beschreibung,
Schritte, Erwartetes Ergebnis, Randbedingungen).

Zeige abschließend:
- Liste aller angelegten HOL-IDs mit Dateinamen
- Hinweis: "Holdouts sind für den Implementierungsagenten nicht sichtbar."
- Nächster Schritt: `sdd start $ARGUMENTS`

## Konventionen

- Szenarien in Deutsch (wie der Rest der SDD-Dokumente)
- Titel als Imperativ: "Nutzer meldet sich an", nicht "Login-Test"
- Kein "sollte" oder "könnte" — Holdouts beschreiben definiertes Verhalten
