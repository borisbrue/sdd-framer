---
id: SPEC-0012
title: Notiz-API mit Token-Authentifizierung
status: approved
---

# SPEC-0012: Notiz-API mit Token-Authentifizierung

## 1. Kontext

`notes` ist ein kleiner HTTP-Dienst für persönliche Notizen im internen Netz. Er läuft als
einzelner Prozess (`python3 -m notes.server`) mit der Python-Standardbibliothek
(`http.server`, `sqlite3`, `json`). Nutzer und ihre API-Tokens werden vom Betrieb in
`notes.toml` hinterlegt; der Dienst verwaltet keine Konten.

## 2. Ziele

- Notizen per JSON-API anlegen, lesen, ändern und löschen.
- Jede Notiz gehört genau einem Nutzer; niemand sieht fremde Notizen.

## 3. Datenmodell

Notiz: `id` (int, fortlaufend), `owner` (Nutzername), `title` (1–200 Zeichen), `body` (Text,
darf leer sein), `created_at`, `updated_at` (ISO-8601, UTC).

## 4. Funktionale Anforderungen

- **FR-01:** Notizen werden in einer SQLite-Datenbank (Pfad aus `notes.toml`, Schlüssel
  `db_path`) gespeichert. Beim Start wird die Tabelle angelegt, falls sie fehlt; bestehende
  Daten bleiben erhalten.
- **FR-02:** Jede Anfrage muss den Header `Authorization: Bearer <token>` tragen. Das Token wird
  gegen die Tabelle `[tokens]` in `notes.toml` (Token → Nutzername) geprüft. Fehlt der Header
  oder ist das Token unbekannt, antwortet der Dienst mit 401 und `{"error": "unauthorized"}`.
- **FR-03:** Endpunkte `POST /notes`, `GET /notes/<id>`, `PUT /notes/<id>`,
  `DELETE /notes/<id>`. `POST` liefert 201 mit der angelegten Notiz, `DELETE` liefert 204.
  Ein `title` außerhalb von 1–200 Zeichen ergibt 422 mit `{"error": "invalid_title"}`.
- **FR-04:** Greift ein Nutzer auf eine Notiz eines anderen Nutzers zu (lesen, ändern,
  löschen), antwortet der Dienst mit 404 – nicht mit 403 –, damit die Existenz fremder
  Notizen nicht erkennbar ist.
- **FR-05:** `GET /notes?limit=<n>&offset=<m>` listet die eigenen Notizen, neueste zuerst
  (`updated_at` absteigend). `limit` ist 1–100, Standard 20; ungültige Werte ergeben 400.

## 5. Nicht-Ziele

- Benutzerregistrierung, Passwort-Login oder Token-Ausgabe über die API.
- Eine Web-Oberfläche.
- Volltextsuche über Notizinhalte.

## 6. Akzeptanzkriterien

- Jede FR ist durch mindestens einen automatisierten Test abgedeckt.
- Der Dienst startet mit leerer Datenbank und mit vorhandener Datenbank fehlerfrei.
