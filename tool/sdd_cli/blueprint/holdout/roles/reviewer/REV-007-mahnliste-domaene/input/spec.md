---
id: SPEC-0014
title: "Mahnwesen für Mitgliedsbeiträge"
status: approved
---

# SPEC-0014: Mahnwesen für Mitgliedsbeiträge

## 1. Kontext

Die Vereinskasse erfasst Beiträge mit Fälligkeitsdatum. Der Kassenwart braucht monatlich eine
Liste der Mitglieder, die gemahnt werden müssen.

## 2. Funktionale Anforderungen

- **FR-01:** Ein Beitrag gilt als mahnfähig, wenn er unbezahlt ist und sein Fälligkeitsdatum
  mehr als 30 Tage vor dem heutigen Datum liegt.
- **FR-02:** Die Mahnliste enthält je Mitglied einen Posten mit der Summe aller mahnfähigen
  Beiträge und dem ältesten Fälligkeitsdatum, sortiert nach ältestem Fälligkeitsdatum, bei
  Gleichstand nach Mitglieds-ID.
- **FR-03:** Die CLI `kasse mahnliste` gibt die Liste als Tabelle aus (eigener Task).
