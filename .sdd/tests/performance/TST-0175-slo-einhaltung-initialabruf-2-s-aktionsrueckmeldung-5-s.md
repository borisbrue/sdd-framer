---
id: TST-0175
project: ''
title: 'SLO-Einhaltung: Initialabruf ≤ 2 s, Aktionsrückmeldung ≤ 5 s'
level: performance
spec: SPEC-0040
contract: CON-0151
status: planned
framework: ''
artifact: tests/unit/test_tst_0175.py
tags: []
---
## Was wird geprüft?

Dieser Test verifiziert die Einhaltung der in CON-0151 definierten Service-Level-Objectives (SLOs) unter realistischer Last:

- **SLO-1 (Initialabruf):** Der initiale `GET /projects`-Aufruf wird bei p95 in ≤ 2 Sekunden abgeschlossen — gemessen von Absenden der Anfrage bis zum vollständigen Empfang der Antwort.
- **SLO-2 (Aktionsrückmeldung):** Die End-to-End-Latenz einer Start- oder Stopp-Aktion — von Absenden des API-Aufrufs (`POST /projects/{id}/start` bzw. `/stop`) bis zur bestätigten Statusänderung (Hub-Antwort mit neuem Status) — liegt bei p95 in ≤ 5 Sekunden.

Beide SLOs werden unter simulierter Normallast gemessen (mehrere Projekte, typische Netzwerkbedingungen ohne künstliche Degradierung).

---

## Vorbedingungen

- Der Hub läuft und ist über seine REST-API erreichbar.
- Im Hub sind **mindestens 10 Projekte** hinterlegt, davon mindestens 5 im Status `stopped` und 5 im Status `running`, um beide Aktionstypen abzudecken.
- Die Netzwerkverbindung entspricht normalen Bedingungen (kein Throttling, keine simulierten Ausfälle).
- Der API-Endpunkt `GET /projects` liefert die vollständige Projektliste in einer einzigen paginierten oder nicht-paginierten Antwort.
- Authentifizierungstoken/Session ist vorhanden und gültig.
- Es laufen **keine anderen Lasttests parallel**, die die Hub-Ressourcen verfälschen könnten.
- Das Testsystem kann Zeitstempel mit Millisekunden-Präzision erfassen.

---

## Ablauf

**Phase 1 — SLO-1: Initialabruf**

1. Testlauf wird **k-mal wiederholt** (Empfehlung: k = 50 Iterationen), um belastbare Perzentilwerte zu erhalten.
2. Pro Iteration:
   a. Zeitstempel `t_start` erfassen (unmittelbar vor dem HTTP-Request).
   b. `GET /projects` absenden.
   c. Zeitstempel `t_end` erfassen (nach Eingang des letzten Bytes der Antwort, HTTP 200).
   d. Latenz `Δt = t_end − t_start` speichern.
3. Aus allen Messungen das **p95-Perzentil** berechnen.

**Phase 2 — SLO-2: Aktionsrückmeldung**

1. Testlauf wird **k-mal wiederholt** (k = 50), abwechselnd Start- und Stopp-Aktionen.
2. Pro Iteration:
   a. Projekt mit passendem Ausgangsstatus auswählen (`stopped` → Start, `running` → Stopp).
   b. Zeitstempel `t_action` erfassen.
   c. `POST /projects/{id}/start` bzw. `/stop` absenden.
   d. Zeitstempel `t_confirmed` erfassen, sobald die Hub-Antwort den neuen Status enthält (z. B. `{"status": "starting"}` oder `{"status": "stopping"}`).
   e. Latenz `Δt = t_confirmed − t_action` speichern.
   f. Projektstatus für die nächste Iteration zurücksetzen (ggf. Gegenaktion auslösen und auf stabilen Zustand warten).
3. Aus allen Messungen das **p95-Perzentil** berechnen.

---

## Erwartetes Ergebnis

| SLO | Metrik | Grenzwert | Ergebnis |
|-----|--------|-----------|----------|
| SLO-1 | p95-Latenz `GET /projects` | ≤ 2 000 ms | PASS |
| SLO-2 | p95-Latenz Start/Stopp (bis Statusbestätigung) | ≤ 5 000 ms | PASS |

Beide Bedingungen müssen gleichzeitig erfüllt sein, damit der Test als **PASS** gilt. Ein Fehlschlagen einer SLO genügt für **FAIL**.

Zusätzlich werden als Informationsmetriken protokolliert: Median, p50, p75, p99, Min, Max — zur Trendbeobachtung über Testläufe hinweg.

---

## Negativfälle / Edge Cases

| Szenario | Erwartetes Verhalten |
|----------|----------------------|
| Hub antwortet mit HTTP 5xx | Iteration wird als Fehler gewertet, nicht in die Perzentilberechnung einbezogen; Fehlerrate wird separat protokolliert. Überschreitet die Fehlerrate 5 %, schlägt der Test mit eigenem Fehlerbild fehl. |
| Netzwerk-Timeout überschreitet 10 s | Iteration zählt als Ausreißer; p99 wird zusätzlich gemeldet, um Ausreißer sichtbar zu machen. |
| Statusänderung kommt als Zwischenstatus (`starting`/`stopping`) | Zeitstempel `t_confirmed` wird beim **ersten** Eingang des Übergangsstatus gesetzt — nicht erst beim Endzustand (`running`/`stopped`). Begründung: Die Spec fordert eine *sichtbare* Statusänderung, nicht den abgeschlossenen Hochfahrvorgang. |
| Weniger als 10 Projekte vorhanden | Test bricht mit Konfigurationsfehler ab (`SETUP_FAIL`), bevor Messungen beginnen. |
| Projektstatus konvergiert nicht rechtzeitig für Reset | Reset-Timeout von 30 s; Projekt wird übersprungen und der Fehler protokolliert. |

---

## Verknüpfung mit dem Contract

Dieser Test validiert direkt die in **CON-0151** (`slo-yaml`) definierten SLO-Schwellwerte:

- Die in CON-0151 spezifizierten Endpunkte (`GET /projects`, `POST /projects/{id}/start`, `POST /projects/{id}/stop`) sind die einzigen unter Beobachtung stehenden Schnittstellen.
- Die Grenzwerte (p95 ≤ 2 s, p95 ≤ 5 s) werden 1:1 aus dem Contract übernommen — keine Eigeninterpretation.
- Sollte CON-0151 die SLO-Grenzwerte anpassen, muss dieser Test-Body **versionssynchron** aktualisiert werden (Contract-Version im Frontmatter beachten).
- Funktionale Korrektheit der Antwortinhalte (Schema, Statusübergänge) ist nicht Gegenstand dieses Tests — das prüft TST-0170 (Contract-Test zu CON-0150).

---

## Hinweise zur Implementierung

**Framework & Tools**

- **[k6](https://k6.io/)** (empfohlen): Nativ für HTTP-Lasttests konzipiert, liefert Perzentilauswertung out-of-the-box (`http_req_duration{p(95)}`), Skript in JavaScript/TypeScript, CI-Integration über `k6 run --out json`.
- Alternativ: **pytest-benchmark** + `httpx` für Python-nahe Umgebungen, wenn der Hub-Stack bereits Python-Testwerkzeuge nutzt.

**Messgenauigkeit**

- Latenz wird **client-seitig** gemessen (inkl. Netzwerk-Round-Trip), nicht server-seitig — spiegelt die Nutzerperspektive gemäß Spec wider.
- Warmup-Phase: Die ersten **5 Iterationen** pro Phase werden verworfen, um TCP-Verbindungsaufbau und JIT-Effekte herauszurechnen.

**CI-Integration**

```yaml
# Beispiel: k6-Schwellwert im Skript
thresholds:
  http_req_duration{scenario:initial_fetch}: ["p(95)<2000"]
  http_req_duration{scenario:action_roundtrip}: ["p(95)<5000"]
```

Bei Schwellwertüberschreitung gibt k6 Exit-Code 99 zurück — direkt als CI-Fehler auswertbar.

**Datenisolation**

Testprojekte sollten eine eigene Namenskonvention tragen (z. B. Präfix `slo-test-`) und nach Testlauf in den Ausgangszustand zurückversetzt werden, um keine Folgetests zu beeinflussen.