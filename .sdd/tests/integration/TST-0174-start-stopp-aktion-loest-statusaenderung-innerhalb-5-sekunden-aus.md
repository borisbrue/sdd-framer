---
id: TST-0174
project: ''
title: Start/Stopp-Aktion löst Statusänderung innerhalb ≤ 5 Sekunden aus
level: integration
spec: SPEC-0040
contract: CON-0147
status: planned
framework: ''
artifact: tests/unit/test_tst_0174.py
tags: []
---
## Was wird geprüft?

Dieser Test stellt sicher, dass eine Start- oder Stopp-Anfrage an die Hub-API innerhalb von **≤ 5 Sekunden** zu einer messbaren Statusänderung des betroffenen Projekts führt. Die Statusänderung gilt als sichtbar, sobald entweder der direkte Action-Response oder ein nachfolgender `GET /projects/{id}` einen abweichenden `status`-Wert gegenüber dem Ausgangszustand zurückgibt.

Geprüft werden beide Richtungen:
- `stopped` → Start-Aktion → `starting` oder `running`
- `running` → Stopp-Aktion → `stopping` oder `stopped`

---

## Vorbedingungen

- Ein laufender Hub ist per Netzwerk erreichbar; die Basis-URL ist als Umgebungsvariable `HUB_BASE_URL` gesetzt.
- Ein gültiges Auth-Token (`HUB_API_TOKEN`) mit Schreibrechten auf mindestens zwei Testprojekte liegt vor.
- **Testprojekt A** befindet sich vor Testbeginn im Status `stopped`.
- **Testprojekt B** befindet sich vor Testbeginn im Status `running`.
- Beide Projekte sind über `GET /projects/{id}` erreichbar und liefern einen stabilen Initialstatus (zwei aufeinanderfolgende Abfragen im Abstand von 500 ms geben denselben Status zurück).
- Die Systemuhr des Testläufers ist monoton (kein NTP-Sprung während des Tests zu erwarten).

---

## Ablauf

**Szenario 1 — Start-Aktion:**

1. `GET /projects/{projectA_id}` — Initialstatus festhalten (`stopped`), Zeitstempel `t0` setzen.
2. `POST /projects/{projectA_id}/start` — Request abschicken.
3. Polling-Schleife mit maximal **5 000 ms** Gesamtlaufzeit und 250 ms Intervall:
   - `GET /projects/{projectA_id}` absenden.
   - Antwort-`status` auslesen.
   - Bei Wert ≠ `stopped` (z. B. `starting` oder `running`): Zeitstempel `t1` setzen, Schleife beenden.
4. Verstrichene Zeit `Δt = t1 − t0` berechnen.

**Szenario 2 — Stopp-Aktion:**

1. `GET /projects/{projectB_id}` — Initialstatus festhalten (`running`), Zeitstempel `t0` setzen.
2. `POST /projects/{projectB_id}/stop` — Request abschicken.
3. Polling-Schleife analog zu Szenario 1; Abbruch bei Status ≠ `running`.
4. `Δt = t1 − t0` berechnen.

---

## Erwartetes Ergebnis

| Prüfpunkt | Kriterium |
|---|---|
| HTTP-Status der Action-Endpoints | `200` oder `202` |
| Status nach Start-Aktion | `starting` oder `running` innerhalb ≤ 5 000 ms |
| Status nach Stopp-Aktion | `stopping` oder `stopped` innerhalb ≤ 5 000 ms |
| Antwortformat | JSON-Objekt mit Feld `status` (string), konform zum Schema in CON-0147 |
| `Δt` beider Szenarien | < 5 000 ms |

---

## Negativfälle / Edge Cases

**Timeout überschritten:** Polling läuft 5 000 ms ohne Statuswechsel — Test schlägt fehl mit Meldung `STATUS_CHANGE_TIMEOUT` und dem letzten beobachteten Status.

**Ungültiger Übergangsstatus:** Der Hub antwortet mit einem unbekannten `status`-Wert — Test schlägt fehl und protokolliert den unerwarteten Wert für Analyse.

**Action-Endpoint liefert 4xx/5xx:** Fehlercode wird protokolliert; Test schlägt fehl ohne Polling zu starten (kein Folgeschaden durch Wiederholungsversuche).

**Race-Condition beim Initialzustand:** Projekt befindet sich bereits in einem Übergangsstatus (`starting`/`stopping`) — Test bricht vor Ausführung ab und meldet `PRECONDITION_FAILED`; kein Fehlalarm durch bereits laufenden Übergang.

**Netzwerkunterbrechung während des Pollings:** Einzelne `GET`-Requests schlagen mit Timeout fehl — bis zu zwei aufeinanderfolgende Fehler werden überbrückt, beim dritten gilt der Test als fehlgeschlagen (`POLLING_NETWORK_ERROR`).

---

## Verknüpfung mit dem Contract

Der Test validiert folgende Operationen aus **CON-0147** (Hub Projekt-Status & Steuerungs-API):

| Operation | Endpoint | Relevanz |
|---|---|---|
| Projektstatus lesen | `GET /projects/{id}` | Initialstatus, Polling, Statusverifikation |
| Projektserver starten | `POST /projects/{id}/start` | Szenario 1 |
| Projektserver stoppen | `POST /projects/{id}/stop` | Szenario 2 |

Das OpenAPI-Schema aus CON-0147 wird als Request-/Response-Validator eingebunden; jede Abweichung vom deklarierten Schema führt zu einem eigenen Validierungsfehler — unabhängig vom Timing-Ergebnis.

---

## Hinweise zur Implementierung

**Framework:** pytest mit `httpx` für synchrone HTTP-Calls oder `pytest-asyncio` + `httpx.AsyncClient` für parallelen Betrieb beider Szenarien.

**Timing:** `time.monotonic()` statt `time.time()` verwenden, um Systemuhranpassungen auszuschließen.

**Schema-Validierung:** `openapi-core` oder `jsonschema` gegen das in CON-0147 referenzierte OpenAPI-Artefakt einbinden — idealerweise als pytest-Fixture, die das Schema einmalig lädt.

**Polling-Hilfsfunktion:** Gemeinsame `await_status_change(project_id, forbidden_status, timeout_ms=5000, interval_ms=250)`-Funktion für beide Szenarien extrahieren, um Duplikation zu vermeiden.

**Umgebungsvariablen:** `HUB_BASE_URL`, `HUB_API_TOKEN`, `TEST_PROJECT_STOPPED_ID`, `TEST_PROJECT_RUNNING_ID` über `.env`-Datei oder CI-Secrets bereitstellen — keine Hardcodierung.

**Teardown:** Nach dem Test Projekte in ihren Ausgangszustand zurückführen (Stopp von A, Start von B), um Testlauf-Isolation sicherzustellen. Bei fehlgeschlagenem Teardown Warnung loggen, aber keinen weiteren Testfehler auslösen.