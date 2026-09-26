---
id: SPEC-0105
title: "Run-IDs der Pipeline"
status: approved
---
# SPEC-0105: Run-IDs der Pipeline

## 1. Kontext

Jeder Pipeline-Lauf bekommt eine Run-ID, unter der Tasks, Gate-Ergebnisse und Logs
abgelegt werden. Run-IDs müssen über Rechner mit unterschiedlicher Zeitzone hinweg
eindeutig und chronologisch sortierbar sein.

## 4. Funktionale Anforderungen

- **FR-01:** `new_run_id(spec_id, when)` liefert `<spec_id>-<YYYYMMDDTHHMMSSZ>`, wobei der
  Zeitstempel `when` in UTC umgerechnet und im 24-Stunden-Format mit Sekunden geschrieben
  wird. Beispiel: `new_run_id("SPEC-0055", datetime(2026, 9, 26, 16, 5, 9,
  tzinfo=timezone(timedelta(hours=2))))` ergibt `SPEC-0055-20260926T140509Z`.
- **FR-02:** `new_run_id` lehnt mit `ValueError` ab: einen Zeitstempel ohne Zeitzone
  (naives `datetime`) und eine `spec_id`, die nicht dem Muster `<GROSSBUCHSTABEN>-<Ziffern>`
  entspricht (z. B. `spec-0055`, `SPEC_0055`, `SPEC-0055-x`).
- **FR-03:** `parse_run_id(run_id)` ist die Umkehrung: es liefert `(spec_id, when)` mit
  einem zeitzonenbewussten `datetime` in UTC, sodass
  `parse_run_id(new_run_id(s, t)) == (s, t)` für jeden zeitzonenbewussten Zeitpunkt `t`
  mit ganzen Sekunden gilt. Eine Zeichenkette, die nicht dem Format aus FR-01 entspricht,
  führt zu `ValueError`.

## 5. Nicht-Ziele

- Eindeutigkeit innerhalb derselben Sekunde (die Pipeline startet nie zwei Läufe
  derselben Spec pro Sekunde).
