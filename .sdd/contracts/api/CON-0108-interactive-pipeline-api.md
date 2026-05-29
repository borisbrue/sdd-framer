---
id: CON-0108
project: PRJ-0001
title: Interactive Pipeline KI-Aktionen API
type: api
format: markdown
spec: SPEC-0028
version: 0.1.0
status: approved
tests:
- TST-0128
---
# Contract: Interactive Pipeline KI-Aktionen API

## Garantie

Alle KI-Aktions-Endpunkte (`/review`, `/propose-contracts`, `/generate-holdouts`, `/run-tests`) antworten synchron mit `{"ok": bool, "output": str}`. Bei `ok: true` ist die Aktion abgeschlossen und das Ergebnis persistent gespeichert. Bei `ok: false` enthält `output` eine menschenlesbare Fehlermeldung.

## Endpunkte

### POST /api/specs/{spec_id}/review

- Ruft den konfigurierten LLM-Provider auf
- Speichert Ergebnis in `.sdd/reviews/{spec_id}-review.md`
- Markiert Gate-Phase `spec-review` als abgeschlossen
- Response: `{ok, output, summary, issues[], suggestions[]}`

### POST /api/specs/{spec_id}/propose-contracts

- LLM schlägt Contracts vor (max. 6)
- Schreibt `.sdd/contracts/{type}/{CON-XXXX}-{slug}.md`
- Verknüpft CON-IDs im Spec-Frontmatter (`contracts:`)
- Markiert Gate-Phase `contracts-proposed` als abgeschlossen
- Response: `{ok, output, contracts[]}`

### POST /api/specs/{spec_id}/generate-holdouts

- LLM erhält ausschließlich Contract-Inhalt — kein Sourcecode
- Schreibt `.sdd/holdout/{HOL-XXXX}-{slug}.md`
- Response: `{ok, output, holdouts[]}`

### POST /api/specs/{spec_id}/run-tests

- Setzt `pytest tests/ -x --tb=short -q` im laufenden Dev-Container ab
- Gibt `{ok, output}` zurück; `ok: false` wenn Container nicht läuft oder rc != 0

## Fehlerbedingungen

| Bedingung | HTTP-Code | ok |
|-----------|-----------|-----|
| Spec nicht gefunden | 404 | – |
| LLM-Provider-Fehler | 200 | false |
| Container nicht gestartet | 200 | false |
| Keine Contracts vorhanden (Holdout) | 200 | false |

### Response-Schemata

#### `issues[]` (in `/review`-Response)

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | `string` | Eindeutige ID, z. B. `"ISS-001"` |
| `severity` | `"error" \| "warning" \| "info"` | Schweregrad des Problems |
| `message` | `string` | Menschenlesbare Beschreibung |
| `section` | `string \| null` | Betroffener Abschnitt im Spec (optional) |

#### `suggestions[]` (in `/review`-Response)

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | `string` | Eindeutige ID, z. B. `"SUG-001"` |
| `message` | `string` | Konkrete Verbesserungsempfehlung |
| `section` | `string \| null` | Betroffener Abschnitt im Spec (optional) |

#### `contracts[]` (in `/propose-contracts`-Response)

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | `string` | Contract-ID, z. B. `"CON-0001"` |
| `slug` | `string` | URL-freundlicher Kurzname, z. B. `"user-auth"` |
| `type` | `string` | Contract-Typ, z. B. `"api"`, `"data"`, `"behavior"` |
| `title` | `string` | Lesbarer Titel des Contracts |
| `path` | `string` | Relativer Pfad der geschriebenen Datei, z. B. `".sdd/contracts/api/CON-0001-user-auth.md"` |

#### `holdouts[]` (in `/generate-holdouts`-Response)

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | `string` | Holdout-ID, z. B. `"HOL-0001"` |
| `slug` | `string` | URL-freundlicher Kurzname |
| `title` | `string` | Lesbarer Titel des Holdout-Tests |
| `contract_id` | `string` | ID des zugrundeliegenden Contracts |
| `path` | `string` | Relativer Pfad der geschriebenen Datei, z. B. `".sdd/holdout/HOL-0001-user-auth.md"` |

### Verhalten bei wiederholtem Aufruf

Wird ein Endpunkt erneut aufgerufen, obwohl bereits ein Ergebnis persistent gespeichert ist, gilt folgendes Verhalten:

| Endpunkt | Verhalten bei Wiederholung |
|----------|---------------------------|
| `POST /review` | Überschreibt `.sdd/reviews/{spec_id}-review.md` mit dem neuen Ergebnis; Gate-Phase bleibt abgeschlossen |
| `POST /propose-contracts` | Legt **neue** Contract-Dateien mit neuen CON-IDs an; bestehende Contracts werden **nicht** gelöscht; das Spec-Frontmatter (`contracts:`) wird um die neuen CON-IDs ergänzt |
| `POST /generate-holdouts` | Legt **neue** Holdout-Dateien mit neuen HOL-IDs an; bestehende Holdouts werden **nicht** gelöscht |
| `POST /run-tests` | Führt Tests immer neu aus; kein persistenter Zustand, der überschrieben werden könnte |

> **Hinweis:** Wiederholte Aufrufe von `/propose-contracts` und `/generate-holdouts` akkumulieren Artefakte. Soll ein sauberer Neustart erfolgen, müssen bestehende Dateien manuell entfernt oder der Endpunkt `DELETE /api/specs/{spec_id}/contracts` (bzw. `holdouts`) aufgerufen werden, sofern vorhanden.

### Container-Identifikation für `run-tests`

Der laufende Dev-Container wird anhand folgender Strategie ermittelt (Priorität absteigend):

1. **Umgebungsvariable `SDD_DEV_CONTAINER`** – wenn gesetzt, wird der Wert direkt als Container-Name oder -ID verwendet.
2. **Spec-Konfiguration** – wenn im Spec-Frontmatter `dev_container:` angegeben ist, wird dieser Name verwendet.
3. **Konventionsbasierter Name** – Docker-Container mit dem Label `sdd.spec_id={spec_id}` oder dem Namen `sdd-{spec_id}-dev`.

**Verhalten bei mehreren laufenden Containern:**

| Situation | Verhalten |
|-----------|----------|
| Genau ein Container matched | Wird verwendet |
| Mehrere Container matchen | `ok: false`, `output` enthält die Liste der gefundenen Container-IDs und die Aufforderung, `SDD_DEV_CONTAINER` zu setzen |
| Kein Container matched | `ok: false`, `output`: `"Kein passender Dev-Container gefunden"` |

**Beispiel-Frontmatter:**
```yaml
dev_container: mein-projekt-dev
```

### POST /api/specs/{spec_id}/generate-holdouts

- LLM erhält ausschließlich Contract-Inhalt — kein Sourcecode
- Schreibt `.sdd/holdout/{HOL-XXXX}-{slug}.md`
- **Vorbedingung:** Gate-Phase `contracts-proposed` muss abgeschlossen sein (d. h. `/propose-contracts` wurde erfolgreich aufgerufen)
- Markiert Gate-Phase `holdouts-generated` als abgeschlossen
- Response: `{ok, output, holdouts[]}`

### POST /api/specs/{spec_id}/run-tests

- Setzt `pytest tests/ -x --tb=short -q` im laufenden Dev-Container ab
- **Vorbedingung:** Gate-Phase `holdouts-generated` muss abgeschlossen sein (d. h. `/generate-holdouts` wurde erfolgreich aufgerufen)
- Markiert Gate-Phase `tests-passed` als abgeschlossen (nur bei `ok: true`, d. h. rc == 0)
- Gibt `{ok, output}` zurück; `ok: false` wenn Container nicht läuft oder rc != 0

#### ID-Vergabe für `CON-XXXX` und `HOL-XXXX`

- IDs werden **global fortlaufend** vergeben — unabhängig vom Spec oder Contract-Typ.
- Der Zähler wird in `.sdd/state.json` unter den Schlüsseln `next_con_id` bzw. `next_hol_id` als Integer persistiert.
- Bei jeder Vergabe wird der Zähler atomar inkrementiert (Read–Increment–Write mit File-Lock), sodass Konflikte ausgeschlossen sind.
- Bereits vergebene IDs werden **niemals wiederverwendet** — auch nicht nach Löschung eines Contracts oder Holdouts.
- Das Format ist vierstellig nullgefüllt (`CON-0001`, `HOL-0042`); ab 9999 wird fünfstellig weitergeschrieben (`CON-10000`).

| Schlüssel in `state.json` | Startwert | Nächste vergebene ID |
|--------------------------|-----------|----------------------|
| `next_con_id` | `1` | `CON-0001` |
| `next_hol_id` | `1` | `HOL-0001` |

**Konflikt-Handling:** Da der Zähler vor dem Schreiben der Datei atomar reserviert wird, kann kein Namenskonflikt entstehen. Schlägt das anschließende Schreiben der Markdown-Datei fehl, bleibt die reservierte ID trotzdem verbraucht; der Endpunkt gibt `ok: false` zurück und nennt die nicht angelegte ID in `output`.

#### `summary` (in `/review`-Response)

| Feld | Typ | Pflicht | Beschreibung |
|------|-----|---------|--------------|
| `summary` | `string` | ja | Kompakte Gesamtbewertung des Reviews in 1–3 Sätzen; fasst die wichtigsten Befunde aus `issues[]` und `suggestions[]` zusammen (z. B. `"Der Spec ist weitgehend vollständig, enthält jedoch zwei kritische Fehler in der Fehlerbedingungstabelle."`) |

| Vorbedingung nicht erfüllt (`contracts-proposed` fehlt) | 422 | false |
| Vorbedingung nicht erfüllt (`holdouts-generated` fehlt) | 422 | false |

| Spec nicht gefunden | 404 | false |

Bei HTTP 404 wird folgender JSON-Body zurückgegeben:

```json
{"ok": false, "output": "Spec '{spec_id}' nicht gefunden"}
```

Das Response-Format `{ok, output}` gilt einheitlich für alle Fehlerbedingungen einschließlich 404.

**Fehlerbedingung: Leeres `contracts[]`-Array**

Wenn der LLM keine gültigen Contracts vorschlägt (d. h. `contracts[]` ist leer), gibt der Endpunkt `ok: false` zurück. Die Gate-Phase `contracts-proposed` wird **nicht** als abgeschlossen markiert. `output` enthält eine menschenlesbare Fehlermeldung, z. B. `"Der LLM hat keine gültigen Contracts vorgeschlagen."`

Ergänzung in der Fehlerbedingungen-Tabelle:

| Bedingung | HTTP-Code | ok |
|-----------|-----------|-----|
| Spec nicht gefunden | 404 | – |
| LLM-Provider-Fehler | 200 | false |
| Container nicht gestartet | 200 | false |
| Keine Contracts vorhanden (Holdout) | 200 | false |
| LLM schlägt keine Contracts vor (`contracts[]` leer) | 200 | false |

#### Verhalten der Gate-Phase `tests-passed` bei Regression

Die Gate-Phase `tests-passed` wird **nur bei `ok: true`** (rc == 0) gesetzt. Bei `ok: false` (rc != 0 oder Container nicht gestartet) gilt:

| Vorheriger Zustand | Ergebnis des Aufrufs | Neuer Zustand der Gate-Phase `tests-passed` |
|--------------------|----------------------|----------------------------------------------|
| Nicht gesetzt | `ok: false` | Bleibt **nicht gesetzt** |
| Gesetzt | `ok: false` | Wird **zurückgesetzt** (gelöscht) |
| Nicht gesetzt | `ok: true` | Wird **gesetzt** |
| Gesetzt | `ok: true` | Bleibt **gesetzt** |

> **Regression:** Schlägt ein erneuter Testlauf fehl (`ok: false`), wird eine bereits gesetzte Gate-Phase `tests-passed` **aktiv zurückgesetzt**. Damit ist sichergestellt, dass der Pipeline-Zustand stets den tatsächlichen Testergebnissen entspricht und eine bestandene Gate-Phase niemals einen fehlgeschlagenen Testlauf überdauert.

#### Verhalten der Gate-Phase `spec-review` bei LLM-Fehler

Die Gate-Phase `spec-review` wird **nur bei `ok: true`** als abgeschlossen markiert. Bei `ok: false` (z. B. LLM-Provider-Fehler) gilt:

| Vorheriger Zustand | Ergebnis des Aufrufs | Neuer Zustand der Gate-Phase `spec-review` |
|--------------------|----------------------|---------------------------------------------|
| Nicht gesetzt | `ok: false` | Bleibt **nicht gesetzt** |
| Gesetzt | `ok: false` | Bleibt **gesetzt** (kein Rücksetzen) |
| Nicht gesetzt | `ok: true` | Wird **gesetzt** |
| Gesetzt | `ok: true` | Bleibt **gesetzt** |

> **Hinweis:** Im Gegensatz zu `tests-passed` wird eine bereits gesetzte Gate-Phase `spec-review` bei einem fehlgeschlagenen Folgeaufruf **nicht zurückgesetzt** — ein LLM-Fehler invalidiert kein vorheriges erfolgreiches Review. Die Review-Datei (`.sdd/reviews/{spec_id}-review.md`) wird bei `ok: false` **nicht** überschrieben.

#### Validierung des `type`-Felds in `contracts[]`

Das `type`-Feld ist ein **geschlossenes Enum** mit exakt drei erlaubten Werten:

| Wert | Verzeichnis |
|------|-------------|
| `"api"` | `.sdd/contracts/api/` |
| `"data"` | `.sdd/contracts/data/` |
| `"behavior"` | `.sdd/contracts/behavior/` |

Jeder vom LLM vorgeschlagene Contract, dessen `type` keinem dieser drei Werte entspricht, wird **abgelehnt** — der Endpunkt gibt `ok: false` zurück und nennt den ungültigen Wert in `output` (z. B. `"Ungültiger Contract-Typ: 'event'. Erlaubte Werte: api, data, behavior."`). Der Pfad `.sdd/contracts/{type}/` wird **ausschließlich** durch direkte Zuordnung aus dieser Enum-Tabelle gebildet, niemals durch ungeprüfte String-Interpolation des LLM-Outputs.

Damit ist Path-Traversal strukturell ausgeschlossen: Ein Wert wie `"../../etc"` fällt nicht in die Enum-Menge und wird vor jeder Dateisystemoperation verworfen.

**Fehlerbedingung: Leeres `contracts[]`-Array**

Wenn der LLM keine gültigen Contracts vorschlägt (d. h. `contracts[]` ist leer), gibt der Endpunkt `ok: false` zurück. Die Gate-Phase `contracts-proposed` wird **nicht** als abgeschlossen markiert. `output` enthält eine menschenlesbare Fehlermeldung, z. B. `"Der LLM hat keine gültigen Contracts vorgeschlagen."`

Ergänzung in der Fehlerbedingungen-Tabelle:

| Bedingung | HTTP-Code | ok |
|-----------|-----------|-----|
| Spec nicht gefunden | 404 | – |
| LLM-Provider-Fehler | 200 | false |
| Container nicht gestartet | 200 | false |
| Keine Contracts vorhanden (Holdout) | 200 | false |
| LLM schlägt keine Contracts vor (`contracts[]` leer) | 200 | false |

**Priorisierung bei gemischten Matches (Label vs. Name):**

Bei der konventionsbasierten Suche (Schritt 3) werden Label-Matches und Name-Matches **gleichrangig** behandelt. Entscheidend ist ausschließlich die Gesamtzahl der gefundenen Container — unabhängig davon, ob ein Match über das Label `sdd.spec_id={spec_id}` oder den Namen `sdd-{spec_id}-dev` zustande kam.

| Situation | Verhalten |
|-----------|----------|
| Genau ein Container matched (egal ob per Label oder Name) | Wird verwendet |
| Mehrere Container matchen (auch Mischung aus Label- und Name-Matches) | `ok: false`, `output` enthält die Liste der gefundenen Container-IDs und die Aufforderung, `SDD_DEV_CONTAINER` zu setzen |
| Kein Container matched | `ok: false`, `output`: `"Kein passender Dev-Container gefunden"` |

**Beispiel:** Container A trägt das Label `sdd.spec_id=my-spec`, Container B hat den Namen `sdd-my-spec-dev` — dies zählt als **zwei Matches** und führt zu `ok: false`.

#### Initialisierung von `.sdd/state.json`

Existiert `.sdd/state.json` beim ersten Aufruf eines ID-vergebenden Endpunkts noch nicht, wird die Datei **automatisch angelegt** mit folgendem Inhalt:

```json
{"next_con_id": 1, "next_hol_id": 1}
```

Der Endpunkt gibt **nicht** `ok: false` zurück, weil die Datei fehlt. Das Anlegen erfolgt atomar im Rahmen des normalen Read–Increment–Write-Zyklus: Ist die Datei nicht vorhanden, werden die Startwerte als Ausgangsbasis verwendet, die ID wird reserviert, und die Datei wird neu geschrieben.

| Zustand von `.sdd/state.json` | Verhalten |
|-------------------------------|-----------|
| Datei existiert | Zähler wird gelesen, inkrementiert und zurückgeschrieben |
| Datei fehlt | Datei wird mit `{"next_con_id": 1, "next_hol_id": 1}` angelegt, dann normal weiterverarbeitet |
| Datei nicht lesbar / korrupt | `ok: false`; `output` enthält die Fehlermeldung (z. B. `"state.json konnte nicht gelesen werden: <Grund>"`) |

> **Hinweis:** Das übergeordnete Verzeichnis `.sdd/` muss bereits existieren. Fehlt es, gibt der Endpunkt `ok: false` zurück mit `output: ".sdd/-Verzeichnis nicht gefunden"`.
