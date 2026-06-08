---
id: TST-0171
project: ''
title: Projektstatus-Datenmodell gegen JSON-Schema validieren
level: unit
spec: SPEC-0040
contract: CON-0148
status: planned
framework: ''
artifact: tests/unit/test_tst_0171.py
tags: []
---
## Was wird geprüft?

Dieser Unit-Test stellt sicher, dass das Projektstatus-Datenmodell der Hub-API dem in CON-0148 definierten JSON-Schema entspricht. Konkret wird geprüft:

- Objekte mit allen Pflichtfeldern (`id`, `name`, `status`) werden als valide akzeptiert.
- Gültige Statuswerte (`running`, `stopped`, `starting`, `stopping`) bestehen die Schemavalidierung.
- Ungültige oder unbekannte Statuswerte (`unknown`, `error`, `""`, `null`) werden als Schemaverstoß erkannt.
- Objekte mit fehlenden Pflichtfeldern werden abgelehnt.
- Zusätzliche, nicht definierte Felder verhalten sich gemäß Schema (Toleranz oder Ablehnung, je nach `additionalProperties`-Konfiguration).

---

## Vorbedingungen

- Das JSON-Schema aus CON-0148 liegt als Datei vor und ist im Test referenzierbar (z. B. als Import oder Fixture).
- Eine JSON-Schema-Validierungsbibliothek ist als Abhängigkeit verfügbar (z. B. `ajv` für TypeScript/JavaScript oder `jsonschema` für Python).
- Es sind keine externen Dienste, Netzwerkverbindungen oder laufenden Hub-Instanzen erforderlich — der Test ist vollständig isoliert.

---

## Ablauf

1. **Schema laden:** Das JSON-Schema aus dem Contract-Artefakt (CON-0148) wird einmalig in der Test-Setup-Phase geladen und kompiliert.
2. **Valide Objekte testen:** Für jeden der vier erlaubten Statuswerte wird ein minimales Projektstatus-Objekt mit Pflichtfeldern konstruiert und gegen das Schema validiert — erwartet: valide.
3. **Vollständiges Objekt testen:** Ein Objekt mit allen bekannten optionalen Feldern (z. B. `description`, `url`) wird validiert — erwartet: valide.
4. **Ungültige Statuswerte testen:** Objekte mit den Werten `"unknown"`, `"error"`, `"paused"`, `""` und `null` im Feld `status` werden einzeln validiert — erwartet: Schemaverstoß.
5. **Pflichtfelder prüfen:** Je ein Objekt mit fehlendem `id`, fehlendem `name` und fehlendem `status` wird validiert — erwartet: Schemaverstoß.
6. **Leeres Objekt testen:** Ein komplett leeres Objekt `{}` wird validiert — erwartet: Schemaverstoß.
7. **Typfehler testen:** `id` als Integer statt String, `status` als Array statt String — erwartet: Schemaverstoß.

---

## Erwartetes Ergebnis

| Testobjekt | Ergebnis |
|---|---|
| `{ id: "abc", name: "My Project", status: "running" }` | valide |
| `{ id: "abc", name: "My Project", status: "stopped" }` | valide |
| `{ id: "abc", name: "My Project", status: "starting" }` | valide |
| `{ id: "abc", name: "My Project", status: "stopping" }` | valide |
| `{ id: "abc", name: "My Project", status: "unknown" }` | **invalide** |
| `{ id: "abc", name: "My Project", status: "" }` | **invalide** |
| `{ id: "abc", name: "My Project" }` (kein `status`) | **invalide** |
| `{ name: "My Project", status: "running" }` (kein `id`) | **invalide** |
| `{ id: "abc", status: "running" }` (kein `name`) | **invalide** |
| `{}` | **invalide** |
| `{ id: 42, name: "My Project", status: "running" }` | **invalide** |

Alle validen Objekte müssen ohne Validierungsfehler durchlaufen. Jeder invalide Fall muss mindestens einen Fehler im Validierungsergebnis liefern; die Fehlermeldung soll das betroffene Feld und den Verstoßtyp benennen.

---

## Negativfälle / Edge Cases

- **Leerzeichen im Statuswert:** `"running "` (trailing space) — invalide, da kein exakter Enum-Match.
- **Großschreibung:** `"Running"`, `"STOPPED"` — invalide; das Schema ist case-sensitive.
- **`null` als Statuswert:** Explizit als invalide zu behandeln, auch wenn das Schema `nullable` nicht setzt.
- **`status` als Array:** `["running"]` statt `"running"` — Typfehler, invalide.
- **Felder mit `null`-Wert für Pflichtfelder:** `{ id: null, name: "x", status: "running" }` — invalide wenn `id` als String typisiert ist.
- **Vollständig unbekannte Struktur:** `{ foo: "bar" }` — invalide (Pflichtfelder fehlen).
- **Sehr langer `name`-Wert:** Falls das Schema eine `maxLength`-Einschränkung definiert, ist ein String über diesem Limit invalide. Falls nicht, gilt der Test als Hinweis, eine Längenbeschränkung im Schema zu ergänzen.

---

## Verknüpfung mit dem Contract

Dieser Test implementiert direkt die Validierungsregeln aus **CON-0148** (`Projektstatus-Datenmodell`):

- Die Enum-Prüfung der Statuswerte (`running`, `stopped`, `starting`, `stopping`) entspricht dem `enum`-Constraint im Schema-Artefakt von CON-0148.
- Die Pflichtfeld-Prüfung (`id`, `name`, `status`) entspricht dem `required`-Array im Schema.
- Jede Änderung am Schema-Artefakt in CON-0148 macht eine Anpassung der Testfixtures und erwarteten Ergebnisse erforderlich. Schemaversion und Contract-Version sind im Testfile zu dokumentieren.

---

## Hinweise zur Implementierung

**Framework:** Jest (TypeScript) oder Vitest — passend zur bestehenden Frontend-Testinfrastruktur der PWA.

**Validierungsbibliothek:** [`ajv`](https://ajv.js.org/) (Version 8+, JSON Schema Draft-07 oder Draft-2020-12 je nach Schema-Definition in CON-0148). Alternativ `zod` mit einem aus dem Schema generierten Parser, falls das Projekt Zod bereits einsetzt.

**Empfohlene Struktur:**

```typescript
// __tests__/projectStatusSchema.unit.test.ts
import Ajv from "ajv";
import schema from "../contracts/con-0148.schema.json";

const ajv = new Ajv({ allErrors: true });
const validate = ajv.compile(schema);
```

**Fixture-Datei:** Valide und invalide Testobjekte als separate Konstanten oder in einer `test.each`-Tabelle ablegen, um die Testmatrix lesbar zu halten und zukünftige Statuswerte einfach ergänzen zu können.

**Hinweis zur Schemaevolution:** Sobald CON-0148 neue Statuswerte oder Felder aufnimmt, sind die entsprechenden Testfälle synchron zu aktualisieren. Ein fehlgeschlagener Test signalisiert bewusst einen Contract-Breaking-Change.