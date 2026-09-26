---
id: SPEC-0102
title: Kurz-URL-Dienst
status: approved
---
# SPEC-0102: Kurz-URL-Dienst

## 1. Zweck
Eine kleine HTTP-API (Python, `http.server`) erzeugt Kurz-URLs und leitet sie weiter.

## 4. Funktionale Anforderungen
- **FR-01:** `POST /links` mit JSON `{"url": "https://…"}` legt eine Kurz-URL an und antwortet mit
  201 und `{"code": "<7 Zeichen [a-zA-Z0-9]>"}`.
- **FR-02:** Ungültige Ziel-URLs (kein Schema `http` oder `https`, leer) werden mit 400 abgelehnt.
- **FR-03:** `GET /<code>` antwortet mit 302 und `Location` auf die Ziel-URL; unbekannte Codes mit 404.
- **FR-04:** Optional kann beim Anlegen `expires_in_days` (1–365) angegeben werden; nach Ablauf
  antwortet `GET /<code>` mit 410 Gone statt einer Weiterleitung.
- **FR-05:** `GET /links/<code>/stats` liefert `{"hits": <Anzahl Weiterleitungen>}`.

## 5. Nicht-Ziele
- Benutzerkonten, eigene Wunsch-Codes.
