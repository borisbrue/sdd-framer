# SPEC-0105: Score-Baum des Quality-Reports

## 1. Zusammenfassung

Der Quality-Report fasst normalisierte Metriken (0 bis 1) zu Teilscores und einem Gesamtscore
zusammen. Blätter sind Metriken, innere Knoten Teilscores. Nicht jede Metrik ist in jedem Projekt
messbar (n/a); jeder innere Knoten legt fest, wie er damit umgeht.

## 3. Nicht-Ziele

- Keine anderen Aggregationen als der gewichtete Mittelwert.
- Keine Normalisierung von Rohwerten (die Blätter kommen bereits normalisiert an).

## 4. Funktionale Anforderungen

- **FR-01:** `MetricLeaf(name, raw, normalized, weight=1.0, reason=None)` ist eine Dataclass.
  `score()` liefert `normalized` (kann `None` sein = n/a), `renormalized()` ist immer `False`,
  `incomplete()` ist wahr, wenn `normalized` `None` ist.
- **FR-02:** `ScoreNode(name, weight, children=[], policy="renormalize", quorum=0.5, reason=None)`
  ist eine Dataclass. Eine andere `policy` als `renormalize`, `strict` oder `quorum` führt beim
  Anlegen zu `ValueError`. Kinder mit Gewicht `0` (oder kleiner) werden bei allen Berechnungen
  dieses Knotens ignoriert.
- **FR-03:** `ScoreNode.score()` ist der gewichtete Mittelwert der Kinder mit Score (n/a-Kinder
  fallen heraus, die Gewichte der übrigen werden renormalisiert), begrenzt auf `[0, 1]`. Ohne
  Kind mit Score ist das Ergebnis `None`. Bei `policy="strict"` ist das Ergebnis `None`, sobald
  ein Kind n/a ist. Bei `policy="quorum"` ist es `None`, wenn der Anteil fehlender Kinder
  `quorum` **übersteigt** (Gleichheit ist noch zulässig).
- **FR-04:** `renormalized()` ist wahr, wenn der Knoten einen Score hat, aber mindestens ein
  (gewichtetes) Kind n/a ist. `incomplete()` ist wahr, wenn der Knoten keinen Score hat oder
  irgendein Kind (auch mit Gewicht 0, rekursiv) unvollständig ist.
- **FR-05:** `na_reason()` ist `None`, wenn der Knoten einen Score hat. Sonst: der eigene `reason`,
  falls gesetzt; sonst die Gründe der n/a-Kinder (bei Blättern `reason`, bei Knoten rekursiv
  `na_reason()`), ohne leere Einträge, dedupliziert in Reihenfolge des Auftretens und mit `"; "`
  verbunden. Gibt es keine gewichteten Kinder oder keinen Grund, lautet er `"keine Messwerte"`.
- **FR-06:** `to_dict()` liefert für Knoten `{"name", "weight", "score"}` mit auf vier
  Nachkommastellen gerundetem Score (oder `None`), plus `"renormalized": true` nur wenn
  renormalisiert, `"reason"` nur wenn es einen n/a-Grund gibt, `"children"` (Liste der
  Kind-Knoten als dict) und `"metrics"` (Liste der Blätter als dict), jeweils nur wenn nicht
  leer. Blätter liefern `{"name", "raw", "normalized" (gerundet), "weight"}` und `"reason"`, wenn
  gesetzt.
