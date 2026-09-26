---
id: SPEC-0019
title: "Rate-Limiting pro API-Schlüssel"
status: approved
---

# SPEC-0019: Rate-Limiting pro API-Schlüssel

## 1. Kontext

Die Wetterdaten-API (`wetterapi`, Python, WSGI ohne Framework) wird von Partnern mit einem
API-Schlüssel im Header `X-Api-Key` genutzt. Ein Partner hat mit einer Endlosschleife den Dienst
lahmgelegt. Wir begrenzen die Anfragen pro Schlüssel. Die API läuft als **ein** Prozess.

## 2. Nicht-Ziele

- Kein verteiltes Limit (Redis o. Ä.); der Zustand liegt im Speicher des Prozesses.
- Keine Limits pro IP-Adresse.
- Keine Änderung der Authentifizierung selbst.

## 3. Funktionale Anforderungen

- **FR-01:** Jeder API-Schlüssel hat einen Token-Bucket mit Kapazität `burst` und Nachfüllrate
  `rate` Tokens pro Sekunde. Eine Anfrage verbraucht ein Token; ist keines da, wird sie
  abgelehnt. Die Zeitquelle ist injizierbar (monotone Uhr), damit das Verhalten testbar ist.
- **FR-02:** `rate` und `burst` kommen aus `config/limits.toml`: ein Abschnitt `[default]` und
  optional `[keys."<schlüssel>"]` mit abweichenden Werten. Fehlt die Datei, gilt
  `rate = 5`, `burst = 20`. Ungültige Werte (≤ 0) verhindern den Start mit klarer Meldung.
- **FR-03:** Eine WSGI-Middleware wendet das Limit auf alle Pfade unter `/v1/` an. Jede
  Antwort trägt die Header aus CON-0040; abgelehnte Anfragen bekommen Status 429 mit dem dort
  beschriebenen JSON-Körper und `Retry-After`.
- **FR-04:** `GET /admin/limits/<schlüssel>` (nur mit Admin-Schlüssel) zeigt die aktuelle
  Konfiguration und den Füllstand des Buckets als JSON.
- **FR-05:** Die Middleware zählt abgelehnte Anfragen je Schlüssel; der bestehende
  Metrik-Endpunkt `/metrics` gibt sie als `wetterapi_ratelimit_rejected_total{key="…"}` aus.

## 4. Nicht-funktionale Anforderungen

- Zusätzliche Latenz je Anfrage < 1 ms; Zugriff auf die Buckets thread-sicher (der WSGI-Server
  nutzt Threads).
- Nur Standardbibliothek (`tomllib`, `threading`).
