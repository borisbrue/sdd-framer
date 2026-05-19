---
id: TST-0122
title: "LLM-Pool-Konfiguration und Provider-Test (Unit)"
level: unit
spec: SPEC-0027
contract: CON-0103
status: draft
artifact: tests/unit/test_tst_0122.py
---

# TST-0122: LLM-Pool-Konfiguration und Provider-Test

## Zu prüfendes Verhalten

`config_manager.py` + `llm_probe.py`: mehrere Provider konfigurieren, Env-Var-Sicherheit,
Verbindungstest, Strategie-Auswahl (CON-0103).

## Testfälle

- T01: Mehrere Provider werden in `config.yaml` gespeichert mit allen Pflichtfeldern
- T02: Remote-Provider speichert `api_key_env`, nie Klartext-Key (INV-04)
- T03: Direkteingabe eines Keys (beginnt mit "sk-") → Sicherheitswarnung + Ablehnung
- T04: `test_llm(id)` → gibt Latenz zurück wenn Provider erreichbar (INV-03)
- T05: `test_llm(id)` → LlmProbeError wenn Provider nicht erreichbar (INV-03)
- T06: Strategie `local_first` → lokaler Provider wird vor remote bevorzugt
- T07: Doppelte Provider-ID → ValueError (INV-01)
- T08: Remote-Provider ohne `api_key_env` → ValidationError (INV-02)
