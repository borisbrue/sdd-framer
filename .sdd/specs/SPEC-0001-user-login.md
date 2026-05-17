---
id: SPEC-0001
title: User Login mit E-Mail und Passwort
status: implemented
project: PRJ-0002
owner: Auth-Team
created: 2026-05-11
updated: '2026-05-16'
version: 1.0.0
priority: high
tags:
- auth
- security
- mvp
depends_on: []
contracts:
- CON-0001
- CON-0002
- CON-0003
tests:
- TST-0001
- TST-0002
- TST-0003
- TST-0004
adrs:
- ADR-0001
---
# User Login mit E-Mail und Passwort

> **Status:** approved · **Owner:** Auth-Team · **Version:** 1.0.0

## 1. Kontext & Motivation

Registrierte Nutzer benötigen einen sicheren Weg, sich am System zu authentifizieren, um auf ihre persönlichen Daten zuzugreifen. Login ist Voraussetzung für nahezu alle anderen Features und damit Teil des MVP.

Stakeholder: Endnutzer (primär), Customer Support (Account-Wiederherstellung), Security-Team (Compliance).

## 2. Zielsetzung

**Primärziel:** Authentifizierung registrierter Nutzer mit E-Mail/Passwort, ausgegeben als kurzlebiges JWT-Access-Token plus rotierendes Refresh-Token.

**Erfolgskriterien (messbar):**
- [ ] Login-Endpoint antwortet im 95. Perzentil unter 300 ms
- [ ] Fehlerrate (5xx) < 0.1 % im 30-Tage-Fenster
- [ ] Brute-Force-Schutz: nach 5 Fehlversuchen pro Account → 15 min Sperre
- [ ] 100 % aller Passwörter werden mit Argon2id gehasht (kein Klartext, kein MD5/SHA1)

**Nicht-Ziele (explizit):**
- Social Login (Google/GitHub) → separate Spec
- Passwort-Reset-Flow → SPEC-0002
- MFA → SPEC-0003
- Account-Registrierung → SPEC-0004

## 3. User Stories

| ID    | Als ...           | möchte ich ...                          | um ...                              |
|-------|-------------------|-----------------------------------------|-------------------------------------|
| US-01 | registrierter Nutzer | mich mit E-Mail und Passwort einloggen | auf meine Daten zugreifen zu können |
| US-02 | Nutzer            | nach Inaktivität ausgeloggt werden       | mein Konto bei verlorenem Gerät zu schützen |
| US-03 | Nutzer            | bei falschem Passwort klare Rückmeldung | meinen Fehler korrigieren zu können |

## 4. Funktionale Anforderungen

- **FR-01:** Der Endpoint `POST /v1/auth/login` akzeptiert `{email, password}` als JSON.
- **FR-02:** Bei gültigen Credentials wird ein Access-Token (JWT, 15 min Gültigkeit) und ein Refresh-Token (Opaque, 30 Tage Gültigkeit, rotierend) zurückgegeben.
- **FR-03:** Bei ungültigen Credentials wird HTTP 401 mit generischer Fehlermeldung zurückgegeben (keine Unterscheidung "User existiert nicht" vs. "Passwort falsch").
- **FR-04:** Nach 5 Fehlversuchen innerhalb von 15 min wird der Account für 15 min gesperrt (HTTP 423).
- **FR-05:** Erfolgreicher Login protokolliert: Zeitstempel, IP, User-Agent. Misserfolge ebenfalls.
- **FR-06:** Refresh-Token werden bei Verwendung rotiert; der alte Token wird invalidiert.

## 5. Nicht-funktionale Anforderungen

| Kategorie     | Anforderung                                                            |
|---------------|------------------------------------------------------------------------|
| Performance   | p95 < 300 ms, p99 < 800 ms                                             |
| Security      | Argon2id für Passwort-Hashing; TLS 1.3; JWT mit ES256; Rate-Limiting   |
| Accessibility | API-Fehlermeldungen sind lokalisierbar (Accept-Language Header)        |
| Observability | Strukturierte Logs (JSON), Trace-ID pro Request, Metriken: Rate/Errors/Duration |
| Datenschutz   | Keine Passwörter, JWTs oder PII in Logs                                |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: User Login

  Scenario: Erfolgreicher Login mit korrekten Credentials
    Given ein registrierter Nutzer mit E-Mail "alice@example.com" und Passwort "Correct-Horse-Battery"
    When ein POST /v1/auth/login mit diesen Credentials gesendet wird
    Then ist die Antwort HTTP 200
    And der Response-Body enthält "access_token" und "refresh_token"
    And das access_token ist ein gültiges JWT mit Algorithmus ES256

  Scenario: Login mit falschem Passwort
    Given ein registrierter Nutzer mit E-Mail "alice@example.com"
    When ein POST /v1/auth/login mit falschem Passwort gesendet wird
    Then ist die Antwort HTTP 401
    And die Fehlermeldung lautet "Invalid credentials"

  Scenario: Account-Sperre nach Brute-Force
    Given ein registrierter Nutzer mit E-Mail "alice@example.com"
    When 5 fehlgeschlagene Login-Versuche innerhalb von 15 Minuten erfolgen
    Then ist die Antwort beim 6. Versuch HTTP 423
    And der Account ist für 15 Minuten gesperrt
```

## 7. Edge Cases & Fehlerfälle

- E-Mail im Request leer oder fehlt → HTTP 400 mit Validierungsfehler
- Passwort > 1024 Zeichen → HTTP 400 (DoS-Schutz gegen sehr lange Argon2-Hashes)
- Nutzer existiert nicht → HTTP 401 (gleiche Antwort wie falsches Passwort, Timing-Constant)
- Konkurrierende Logins → beide gültig, separate Refresh-Token-Familien
- Refresh-Token-Wiederverwendung → komplette Token-Familie invalidieren (Replay-Schutz)

## 8. Contracts

| Contract-ID | Typ         | Was wird garantiert?                                                |
|-------------|-------------|---------------------------------------------------------------------|
| CON-0001    | api         | OpenAPI-Schema für `POST /v1/auth/login`                            |
| CON-0002    | behavior    | Gherkin-Szenarien als ausführbare Spezifikation                     |
| CON-0003    | performance | SLOs: Latenz p95 < 300 ms, Verfügbarkeit ≥ 99.9 %                   |

## 9. Tests

| Test-ID  | Level       | Was prüft der Test?                                            |
|----------|-------------|----------------------------------------------------------------|
| TST-0001 | contract    | OpenAPI-Konformität (Schemathesis gegen CON-0001)              |
| TST-0002 | acceptance  | Gherkin-Szenarien aus CON-0002 (Cucumber/behave)               |
| TST-0003 | unit        | Argon2id-Hashing-Wrapper, Token-Generierung                    |
| TST-0004 | performance | k6-Lasttest gegen CON-0003                                     |

## 10. Offene Fragen

- [ ] Soll der Sperr-Counter pro IP oder pro Account gezählt werden? → Entscheidung in ADR-0001 dokumentiert
- [ ] Welche JWT-Library wird verwendet? → tech-spezifisch, in Implementierung

## 11. Änderungshistorie

| Datum      | Version | Autor      | Änderung           |
|------------|---------|------------|--------------------|
| 2026-05-11 | 0.1.0   | Auth-Team  | Initialer Draft    |
| 2026-05-11 | 1.0.0   | Auth-Team  | Approval nach Review|
