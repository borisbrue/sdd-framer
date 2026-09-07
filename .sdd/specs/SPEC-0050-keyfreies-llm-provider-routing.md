---
id: SPEC-0050
title: Keyfreies LLM-Provider-Routing – claude-cli als Default, keine stillen Fallbacks
type: feature
status: in-progress
owner: Boris
created: 2026-06-23
updated: '2026-06-23'
version: 0.3.0
priority: high
tags:
- llm
- provider
- routing
- keyless
- reliability
depends_on:
- SPEC-0008
contracts:
- CON-0186
- CON-0187
tests:
- TST-0212
- TST-0213
fr_test_map:
  FR-01:
  - TST-0212
  FR-02:
  - TST-0212
  FR-03:
  - TST-0213
  FR-04:
  - TST-0213
  FR-05:
  - TST-0212
  FR-06:
  - TST-0212
  FR-07:
  - TST-0212
started_at: '2026-06-23T15:03:12Z'
---
# Keyfreies LLM-Provider-Routing – claude-cli als Default, keine stillen Fallbacks

> **Status:** draft · **Owner:** Boris · **Version:** 0.3.0

## 1. Kontext & Motivation

SPEC-0008 hat eine pluggable LLM-Provider-Abstraktion eingeführt. Das System ist bewusst so
ausgelegt, dass es **ohne `ANTHROPIC_API_KEY`** läuft: der `claude-cli`-Provider ruft die
Claude-Code-CLI headless auf (`claude --print --output-format json -p …`) und nutzt damit die
angemeldete Claude-Code-Session statt eines direkten API-Keys.

`config.yaml` stellt entsprechend `ai_routes` und `evaluator` auf `provider: claude-cli`. Das
**Holdout-Gate** (`evaluator.py` → Komponente `evaluator`) läuft dadurch bereits korrekt keyfrei.

Die Provider-Factory (`tool/sdd_cli/llm/factory.py`) hat jedoch eine undichte Stelle: Für die
Komponente `"completion"` greift bei fehlender Konfiguration der **Builtin-Default**
`_COMPLETION_BUILTIN["completion"] = {"provider": "anthropic", …}`. Alle Aufrufer, die
`get_completion_provider(config, "completion")` verwenden, verlangen damit still den Key:

- `lifecycle.review_contract` (Contract-Review) und `lifecycle.py:533`
- `solid.py` (SOLID-Check)
- `pattern.py` (Pattern-Vorschläge)
- `main.py:721`

Zusätzlich **schlucken** `pattern.py` und `solid.py` den daraus resultierenden LLM-Fehler:
Ein fehlender Key führt zu einem leeren Ergebnis, das wie „keine Befunde / keine Vorschläge"
aussieht – eine stille Degradierung, die echte Lücken verschleiert (beobachtet beim Review von
SPEC-0049: „Keine Pattern-Vorschläge generiert" statt eines Fehlerhinweises).

## 2. Zielsetzung

**Primärziel:** Jeder LLM-Pfad ist standardmäßig keyfrei (claude-cli); wo ein Provider nicht
nutzbar ist, scheitert der Aufruf **laut und klar** statt still auf den Key zurückzufallen oder
ein leeres Ergebnis vorzutäuschen.

**Erfolgskriterien (messbar):**
- [ ] `get_completion_provider(config, "completion")` liefert ohne jegliche `llm`-Konfiguration
  einen `claude-cli`-Provider (kein `anthropic`).
- [ ] Ist der gewählte Provider nicht nutzbar (z. B. `claude` CLI fehlt, oder `anthropic` ohne
  Key), schlägt der Aufruf mit einer eindeutigen Fehlermeldung fehl – **kein** automatischer
  Wechsel auf einen anderen Provider.
- [ ] `pattern.py` und `solid.py` melden einen LLM-Fehler sichtbar (`[WARN] … übersprungen: <Grund>`)
  und geben ihn nicht als „keine Vorschläge" / „compliant" aus.
- [ ] Der `anthropic`-Provider bleibt nutzbar, wenn explizit konfiguriert
  (`llm.completion.provider: anthropic` + Key) – unverändertes Verhalten.
- [ ] Das Holdout-Gate (`evaluator`) bleibt unverändert keyfrei (Regressionssicherung).
- [ ] Ein frisch per `sdd init` erzeugtes Projekt ist ohne `ANTHROPIC_API_KEY` arbeitsfähig —
  die Blueprint-`config.yaml` setzt keinen Key-Provider (FR-06).
- [ ] Keine Komponente fällt ohne explizite Konfiguration auf einen Key-Provider zurück —
  weder über `_COMPLETION_BUILTIN` noch über den Fallback in `get_completion_provider` (FR-07).
- [ ] Unit-Tests decken ab: Default-Auflösung auf claude-cli, lautes Scheitern ohne Fallback,
  sichtbare Fehlermeldung in pattern/solid, anthropic-Opt-in via Config.

**Nicht-Ziele (explizit):**
- Keine Änderung am `claude-cli`-Provider selbst.
- Keine Entfernung des `anthropic`- oder `openai-compat`-Providers (bleiben Opt-in).
- Keine Änderung am Evaluator/Holdout-Gate (ist bereits korrekt).
- Kein Umbau der `config.yaml`-Struktur oder der Auflösungs-Hierarchie (nur Default + Fehlerpfad).

## 3. Architektur-Entscheidungen & Design Patterns

### 3.1 Factory Method (Creational)
**Anwendung:** Die zentrale Provider-Auswahl bleibt in `factory.py` (`get_completion_provider`).
Geändert wird nur der Builtin-Default der Komponente `completion` und der Fehlerpfad – die
Auflösungs-Hierarchie (Komponenten-Override → Default-Block → Builtin) bleibt unangetastet.

**Begründung:** Die Factory ist der einzige Ort der Provider-Entscheidung (SRP). Die Korrektur an
genau einer Stelle wirkt für alle `completion`-Aufrufer konsistent (DRY), ohne deren Code zu ändern.

**Alternative:** Den Default an jeder Aufrufstelle setzen – abgelehnt, weil es die Entscheidung
über fünf Module streut und erneut inkonsistent werden kann.

Quelle: https://refactoring.guru/design-patterns/factory-method

### 3.2 Fail-Fast statt Null Object (bewusste Abkehr)
**Anwendung:** Der Fehlerpfad gibt bei nicht nutzbarem Provider einen klaren Fehler zurück statt
eines leeren Ergebnisses. `pattern.py`/`solid.py` propagieren bzw. melden den Fehler sichtbar.

**Begründung:** Das Null-Object-Pattern ist in diesem Projekt anderswo bewusst akzeptiert
(z. B. leerer Katalog-String, `NullSolidChecker`). Hier ist es jedoch der **falsche** Mechanismus:
ein leeres Ergebnis auf einen Infrastruktur-Fehler verschleiert eine reale Lücke und täuscht
Qualität vor. Für den Provider-Fehlerpfad gilt explizit „laut scheitern".

**Alternative:** Stiller Fallback auf einen anderen Provider – abgelehnt, weil er Konfiguration
und tatsächliches Verhalten entkoppelt und Debugging erschwert.

Quelle: https://refactoring.guru/design-patterns/null-object (bewusste Abgrenzung)

## 4. Funktionale Anforderungen

- **FR-01:** `_COMPLETION_BUILTIN["completion"]` verwendet `provider: claude-cli`. Ein
  `get_completion_provider(config, "completion")`-Aufruf ohne `llm`-Konfiguration liefert den
  `claude-cli`-Provider.
- **FR-02:** Ist der aufgelöste Provider nicht nutzbar (CLI fehlt/nicht angemeldet; `anthropic`
  ohne Key), wird ein `RuntimeError` mit klarer Ursache geworfen – kein automatischer Wechsel
  auf einen anderen Provider.
- **FR-03:** `pattern.py` fängt LLM-Fehler nicht still ab, sondern meldet sie sichtbar
  (`[WARN] Pattern-Vorschläge übersprungen: <Grund>`) und unterscheidet so „kein LLM" von
  „keine Vorschläge".
- **FR-04:** `solid.py` verhält sich analog: ein LLM-Fehler wird gemeldet, nicht als „compliant"
  dargestellt.
- **FR-05:** Der `anthropic`-Provider bleibt über explizite Konfiguration
  (`llm.completion.provider: anthropic` + `api_key`) unverändert nutzbar.

- **FR-06:** Die Blueprint-`config.yaml` (`tool/sdd_cli/blueprint/config.yaml`) setzt den
  `llm`-Block auf `claude-cli`, sodass ein per `sdd init` erzeugtes Projekt ohne
  `ANTHROPIC_API_KEY` arbeitsfähig ist.

  **Warum das eine eigene FR braucht:** FR-01 wirkt auf den *Builtin*-Default, also auf den
  Fall „keine `llm`-Konfiguration vorhanden". Das Blueprint liefert aber eine — und setzte
  `completion` bisher ausdrücklich auf `anthropic`. Der keyfreie Builtin wurde damit für
  **jedes neue Projekt** wieder überschrieben. FR-01 war erfüllt und das Primärziel trotzdem
  verfehlt, weil die beiden Ebenen gegeneinander arbeiteten.

  Nachgereicht am 2026-09-07, nachdem der Fall beim Aufsetzen eines realen Projekts
  aufgefallen ist. Die Umsetzung lag zu diesem Zeitpunkt bereits vor; die FR dokumentiert
  sie nach, statt Code ohne Anforderung stehen zu lassen.

- **FR-07:** Die Builtin-Defaults (`_COMPLETION_BUILTIN`) für `evaluator` und `ai_routes`
  sowie der Provider-Fallback in `get_completion_provider` verwenden `claude-cli`. Damit
  löst *jede* Komponente ohne explizite Konfiguration keyfrei auf, nicht nur `completion`.

  **Warum das eine eigene FR braucht:** FR-01 nennt ausdrücklich nur die Komponente
  `completion`. `evaluator` und `ai_routes` standen im Builtin weiter auf `anthropic`, und
  der Fallback für Komponenten ohne Builtin-Eintrag (`local_llm`) ebenfalls. US-01 — „SDD
  ohne `ANTHROPIC_API_KEY` voll nutzen können" — war damit nicht erfüllt: das Holdout-Gate
  und die AI-Routes verlangten weiterhin einen Key. FR-01 deckte diese Lücke nicht ab.

  Abgrenzung zu FR-06: FR-06 betrifft die vom Blueprint *ausgelieferte* Konfiguration,
  FR-07 die Auflösung, wenn gar keine Konfiguration greift. Beide Ebenen mussten
  angefasst werden, weil sie unabhängig voneinander einen Key erzwingen konnten.

  Nachgereicht am 2026-09-07 aus demselben Anlass wie FR-06. Auch hier lag die Umsetzung
  bereits vor.

> Die Dokumentation des keyfreien Default-Verhaltens ist als Schritt 5 der
> Implementierungsreihenfolge erfasst (keine eigene FR, da nicht funktional/testbar).

## 5. User Stories

| ID    | Als ...        | möchte ich ...                                                       | um ...                                              |
|-------|----------------|------------------------------------------------------------------------|------------------------------------------------------|
| US-01 | Entwickler:in  | SDD ohne `ANTHROPIC_API_KEY` voll nutzen können                        | autonom in Claude Code zu arbeiten ohne Key-Setup    |
| US-02 | Maintainer:in  | bei fehlendem LLM einen klaren Fehler statt leerer Ergebnisse sehen     | echte Lücken nicht mit „keine Befunde" zu verwechseln |
| US-03 | Power-User      | optional weiterhin den anthropic-Provider per Config wählen            | bei Bedarf den direkten API-Pfad zu nutzen           |

## 6. Contracts

> Werden in `/sdd-review SPEC-0050` → Contract-Erstellung ergänzt (behavior: Provider-Auflösung
> + Fail-Loud; ggf. data: Builtin-Defaults pro Komponente).

## 7. Tests

> Werden nach Contract-Approval ergänzt (Default-Auflösung, Fail-Loud ohne Fallback, sichtbare
> Fehler in pattern/solid, anthropic-Opt-in, Evaluator-Regression).

## 8. Implementierungsreihenfolge

1. `factory.py`: Builtin-Default `completion` → `claude-cli`; Fehlerpfad „kein stiller Fallback"
   schärfen + Unit-Tests.
2. `pattern.py`: LLM-Fehler sichtbar melden statt leeres Ergebnis + Test.
3. `solid.py`: LLM-Fehler sichtbar melden statt „compliant" + Test.
4. Regressionstest: `evaluator`-Komponente bleibt claude-cli/keyfrei.
5. Doku: keyfreies Default-Routing in `config.yaml`-Vorlage/Provider-Doku.

## 9. Offene Fragen

| # | Frage | Verantwortlich | Deadline |
|---|-------|----------------|----------|
| OQ-01 | ✅ Soll bei nicht nutzbarem Provider laut gescheitert werden statt still auf anthropic/leer zurückzufallen? **Antwort:** Ja – kein stiller Fallback (Kernziel der Spec). | Boris | geklärt |
| OQ-02 | Soll auch `main.py:721` (Komponente `completion`) explizit auf einen sinnvollen Default geprüft werden, oder reicht der globale `completion`-Default? | Boris | offen |

## 10. Änderungshistorie

| Version | Datum      | Änderung           |
|---------|------------|---------------------|
| 0.1.0   | 2026-06-23 | Initiale Erstellung |
