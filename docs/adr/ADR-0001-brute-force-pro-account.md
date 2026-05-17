---
id: ADR-0001
title: "Brute-Force-Schutz: Sperre pro Account statt pro IP"
status: accepted
date: 2026-05-11
deciders: [Auth-Team, Security]
related_specs: [SPEC-0001]
supersedes: ""
---

# ADR-0001: Brute-Force-Schutz: Sperre pro Account statt pro IP

## Status

accepted

## Kontext

SPEC-0001 fordert Brute-Force-Schutz mit 5 Fehlversuchen → 15 min Sperre (FR-04). Offene Frage: Wird der Counter pro IP oder pro Account geführt?

Beide Varianten haben Vor- und Nachteile, und die Entscheidung beeinflusst Tests, Datenmodell und Edge-Case-Verhalten.

## Optionen

### Option A: Pro IP
- **Pro:** Stoppt verteilte Versuche eines Angreifers von einer IP.
- **Contra:** Nutzer hinter Corporate-NAT teilen IP — ein Angreifer sperrt unbeteiligte Kollegen aus.
- **Contra:** Mobile Nutzer wechseln IP häufig → Schutz umgehbar.

### Option B: Pro Account
- **Pro:** Schützt jeden Account isoliert. Mobile Nutzer leiden nicht.
- **Contra:** Angreifer kann gezielt einen bekannten Account temporär aussperren (DoS auf Nutzerebene).
- **Contra:** Schützt nicht gegen Credential-Stuffing über viele Accounts hinweg.

### Option C: Beides kombiniert
- **Pro:** Robusteste Verteidigung.
- **Contra:** Höhere Komplexität, mehr Tuning nötig, mehr State.

## Entscheidung

**Option B (pro Account)** wird für das MVP gewählt, ergänzt um globales Rate-Limiting pro IP (Off-the-shelf, z.B. via Reverse Proxy). Damit:

- Erfüllt FR-04 buchstäblich
- Schützt Nutzer in Multi-User-Netzen
- Globales IP-Rate-Limit fängt Massenangriffe vor der App ab (Defense in Depth)

Credential-Stuffing wird separat über Have-I-Been-Pwned-Integration adressiert (Out-of-Scope SPEC-0001).

## Konsequenzen

**Positiv:**
- Klare, testbare Regel (Test TST-0002 deckt sie ab)
- Mobile/Enterprise-Nutzer nicht benachteiligt

**Negativ:**
- Gezielter DoS auf einzelne Accounts möglich → Risiko im Threat-Model dokumentieren

**Neutral:**
- Datenmodell: Tabelle `login_attempts(user_id, timestamp, success)` statt `login_attempts(ip, ...)`

## Verknüpfungen

- Specs: SPEC-0001
- Ersetzt: —
