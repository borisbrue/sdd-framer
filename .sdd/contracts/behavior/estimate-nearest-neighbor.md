# Schätzmethode: k=3 Nearest Neighbor (Artifact)

Siehe [CON-0042](CON-0042-estimate-nearest-neighbor.md) für die vollständige Contract-Definition.

## Kurzreferenz

- **Feature-Vektor:** 7 Merkmale (body_chars, contract_count, test_count, user_story_count, fr_count, dependency_count, priority_weight)
- **Algorithmus:** Min-Max-Normalisierung → Euklidischer Abstand → k=3 nächste Nachbarn → Gewichteter Durchschnitt (1/distance)
- **Konfidenz:** < 3 Punkte → LOW, 3–9 → MEDIUM, ≥ 10 → HIGH
- **Kein LLM-Einsatz** – rein statistisch/heuristisch
