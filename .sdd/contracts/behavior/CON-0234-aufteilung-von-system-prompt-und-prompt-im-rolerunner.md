---
id: CON-0234
title: "Aufteilung von System-Prompt und Prompt im RoleRunner"
type: behavior
format: gherkin
spec: SPEC-0068
version: 0.3.0
status: approved
artifact: ".sdd/contracts/behavior/aufteilung-von-system-prompt-und-prompt-im-rolerunner.feature"
tests: ["TST-0263"]
---

# Contract: Aufteilung von System-Prompt und Prompt im RoleRunner

> **Spec:** SPEC-0068 · **Typ:** Verhalten (Gherkin) · **Status:** approved

## Zweck

Legt fest, welche Teile eines Rollenaufrufs der RoleRunner als `system_prompt` und welche als
Prompt an den Provider übergibt (SPEC-0068 FR-01 bis FR-04). Ziel ist ein System-Prompt, der über
Wiederholungsversuche gleich bleibt und deshalb aus dem Prompt-Cache gelesen wird.
Quellen, Titel und Budgets: SPEC-0053, CON-0199.

## Garantien

Die Szenarien im Artifact
(`.sdd/contracts/behavior/aufteilung-von-system-prompt-und-prompt-im-rolerunner.feature`) sind
**ausführbare Spezifikation**.

## Invarianten

- **INV-01:** Jede Kontextquelle hat genau eine Einteilung in `roles.SOURCE_KINDS`
  (`stable` oder `volatile`); `CONTEXT_SOURCES` sind genau die Schlüssel von `SOURCE_KINDS`, eine
  Quelle ohne Einteilung gibt es nicht. Wechselnd (`volatile`) sind genau `test_output`, `review`,
  `history`, `diff` und `gate_results`.
- **INV-02:** `system_prompt` = Rollen-Prompt, dann die gerenderten stabilen Quellen in der
  Reihenfolge der `inputs`; alle Teile durch `"\n\n"` getrennt. Ohne stabile Quellen ist er genau
  der Rollen-Prompt. Eine Quelle wird als `"## <Titel>\n\n<Inhalt>"` gerendert, der Inhalt auf
  ihr Budget gekürzt (`runner.render_sources`, SPEC-0053); leere Quellen (`None`, `""`, `[]`,
  `{}`) entfallen.
- **INV-03:** Prompt = `lead` (falls nicht leer), dann die gerenderten wechselnden Quellen in der
  Reihenfolge der `inputs`; alle Teile durch `"\n\n"` getrennt. Fehlen `lead` und wechselnde
  Quellen, ist der Prompt `purpose`. Danach folgt `"\n\nnonce: <16 Hex-Zeichen>"`.
- **INV-04:** `system_prompt` enthält keinen Wert, der je Aufruf wechselt: Bei gleichen stabilen
  Quellen ist er byte-gleich.
- **INV-05:** `prompt_hash` = erste 16 Hex-Zeichen von SHA-256 (UTF-8) über
  `system_prompt + "\n\n" + P`, wobei `P` der Prompt vor dem Suffix `"\n\nnonce: <hex>"` ist.

## Begriffe

| Begriff          | Definition |
|------------------|------------|
| stabile Quelle   | Quelle mit Einteilung `stable` (INV-01); sie ändert sich zwischen Versuchen derselben Rolle für dieselbe Task nur, wenn sich Dateien ändern (z. B. `current_files` nach grünem Stand und Review-Ablehnung) |
| wechselnde Quelle | Quelle mit Einteilung `volatile`: Rückmeldung aus dem vorigen Versuch |
| System-Nachricht | Die Nachricht mit `role: system`, die der `openai-compat`-Provider aus `system_prompt` bildet; so sieht sie der Fake-Server |
| Nutzer-Nachricht | Die Nachricht mit `role: user`, die der Provider aus dem Prompt bildet |
| Titel            | Überschrift einer Quelle nach `runner.SOURCE_TITLES`, z. B. `## Testausgabe` für `test_output`, `## history` für `history` |
| S1               | Entscheidungspunkt des Supervisors über die Zerlegung (SPEC-0053) |
| Wiederholungsversuch | erneuter Aufruf derselben Rolle für dieselbe Task im selben Run |
