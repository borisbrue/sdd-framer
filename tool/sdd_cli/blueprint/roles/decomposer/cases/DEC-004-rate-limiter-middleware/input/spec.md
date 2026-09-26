---
id: SPEC-0034
title: Rate-Limiting für die Katalog-API
status: approved
---

# SPEC-0034: Rate-Limiting für die Katalog-API

## 1. Kontext

Die Katalog-API (`catalog/app.py`, eine WSGI-Anwendung) wird von einzelnen Partnern mit
Skripten überlastet. Ein Rate-Limiter soll vor die Anwendung gesetzt werden, ohne ihren Code
zu ändern. Der Dienst läuft als ein Prozess mit mehreren Threads.

## 2. Funktionale Anforderungen

- **FR-01:** Das Limit wird je Schlüssel mit einem Token-Bucket umgesetzt: Kapazität `burst`,
  Nachfüllrate `rate` Token pro Sekunde, jede Anfrage verbraucht ein Token. Die Zeitquelle ist
  injizierbar (Standard `time.monotonic`), damit das Verhalten ohne Warten testbar ist. Der
  Zugriff auf einen Bucket ist threadsicher.
- **FR-02:** Der Schlüssel ist der Wert des Headers `X-Api-Key`; fehlt er, die Client-Adresse
  (`REMOTE_ADDR`). Anfragen mit und ohne API-Key derselben Adresse teilen sich keinen Bucket.
- **FR-03:** Ist kein Token verfügbar, antwortet die Middleware selbst mit `429 Too Many
  Requests`, ohne die Anwendung aufzurufen, und setzt `Retry-After` auf die aufgerundete Zahl
  Sekunden bis zum nächsten Token. Erlaubte Antworten der Anwendung erhalten den Header
  `X-RateLimit-Remaining` mit den verbleibenden Token (abgerundet).
- **FR-04:** Limits werden je Pfadpräfix konfiguriert (z. B. `/search` strenger als `/items`);
  es gilt das längste passende Präfix, sonst ein Standardlimit. Pfade in `exempt` (z. B.
  `/health`) werden nie begrenzt und verbrauchen keine Token.
- **FR-05:** Buckets, die länger als `idle_ttl` Sekunden (Standard 600) nicht benutzt wurden,
  werden entfernt, damit der Speicher bei vielen wechselnden Clients nicht unbegrenzt wächst.
  Das Aufräumen läuft bei Anfragen mit, höchstens einmal je `idle_ttl / 10` Sekunden, ohne
  eigenen Hintergrund-Thread.

## 3. Nicht-Ziele

- Keine verteilten Limits über mehrere Prozesse oder Rechner (kein Redis, keine Datenbank).
- Keine Konfiguration zur Laufzeit über eine Admin-API.
- Keine Änderungen an `catalog/app.py`.
