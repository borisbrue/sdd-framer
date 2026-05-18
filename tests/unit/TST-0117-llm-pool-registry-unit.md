---
id: TST-0117
title: "LLM-Pool-Registry und Selector (Unit)"
level: unit
spec: SPEC-0026
contract: CON-0098
status: draft
---

# TST-0117: LLM-Pool-Registry und Selector

## Zu prüfendes Verhalten

`llm_pool.py` liest LLM-Einträge aus der Config und wählt via `LlmSelector`
das optimale LLM für einen Task gemäß CON-0098.

## Testfälle

- T01: low/S-Task → lokales cheap-LLM wird bevorzugt (INV-03)
- T02: high/L-Task → powerful-LLM wird gewählt
- T03: Bevorzugtes Tier fehlt → Fallback auf nächstes verfügbares Tier
- T04: Task mit estimated_tokens > LLM.max_context_tokens → LLM wird übersprungen (INV-02)
- T05: Leere Registry → LlmUnavailableError
- T06: Doppelte LLM-ID in Config → ValueError (INV-01)
- T07: remote vs. local bei gleichem Tier → lokal gewinnt (INV-03)
- T08: Alle LLMs haben zu kleines Kontext-Limit → LlmUnavailableError
