---
id: TST-0170
project: ''
title: OpenAPI-Schemakonformität der Hub-Steuerungs-API
level: contract
spec: SPEC-0040
contract: CON-0147
status: planned
framework: ''
artifact: tests/unit/test_tst_0170.py
tags: []
---
## Was wird geprüft?

Dieser Contract-Test verifiziert, dass alle drei Endpunkte der Hub-Steuerungs-API das in CON-0147 definierte OpenAPI-Schema vollständig einhalten. Konkret wird geprüft:

- **`GET /projects`**: Response-Body enthält ein Array von Projektobjekten mit allen Pflichtfeldern (`id`, `name`, `status`) und gültigen Statuswerten (`running`, `stopped`, `starting`, `stopping`). HTTP-Statuscode ist `200`.
- **`POST /projects/{id}/start`**: Request wird mit gültigem Projekt-ID-Pfadparameter gesendet; Response enthält das aktualisierte Projektobjekt mit Status `starting` oder `running` und Statuscode `200` oder `202`.
- **`POST /projects/{id}/stop`**: Analog zu Start; Response-Status ist `stopping` oder `stopped`, HTTP-Code `200` oder `202`.

Zusätzlich werden HTTP-Fehlercodes auf Schema-Konformität geprüft: `404` bei unbekannter Projekt-ID, `503` bei nicht erreichbarem Hub.

---

## Vorbedingungen

- Eine laufende Hub-Instanz (oder ein Mock-Server, der das OpenAPI-Schema aus CON-0147 bedient) ist unter der konfigurierten Base-URL erreichbar.
- Das OpenAPI-Schema aus CON-0147 liegt als maschinenlesbare Datei (z. B. `hub-control-api.openapi.yaml`) im Test-Fixture-Verzeichnis vor.
- Mindestens zwei Testprojekte sind im Hub vorkonfiguriert: eines mit Status `stopped`, eines mit Status `running`.
- Der Test-Runner hat Netzwerkzugang zum Hub-Endpunkt (oder zum Mock).
- Abhängigkeiten (`schemathesis` oder `openapi-validator`, HTTP-Client) sind installiert.

---

## Ablauf

1. **Schema laden**: Das OpenAPI-Dokument aus CON-0147 wird eingelesen und als Referenz für alle Validierungsschritte verwendet.

2. **`GET /projects` — Positivfall**:
   - HTTP-GET gegen `/projects` absenden.
   - Response-Status auf `200` prüfen.
   - Response-Body gegen das Schema-Objekt `ProjectList` aus CON-0147 validieren (Array-Typ, Pflichtfelder je Eintrag, Enum-Werte für `status`).

3. **`POST /projects/{id}/start` — Positivfall**:
   - Projekt-ID des `stopped`-Projekts aus Schritt 2 entnehmen.
   - HTTP-POST gegen `/projects/{id}/start` absenden (kein Request-Body erforderlich laut Schema).
   - Response-Status auf `200` oder `202` prüfen.
   - Response-Body gegen Schema-Objekt `ProjectStatusResponse` validieren; Feld `status` muss `starting` oder `running` sein.

4. **`POST /projects/{id}/stop` — Positivfall**:
   - Analog mit der ID des `running`-Projekts.
   - Response `status` muss `stopping` oder `stopped` sein.

5. **Negativfall — unbekannte Projekt-ID**:
   - POST gegen `/projects/nonexistent-id-000/start`.
   - Response-Status muss `404` sein; Response-Body gegen Schema-Objekt `ErrorResponse` validieren.

6. **Negativfall — Hub nicht erreichbar** (simuliert durch Mock-Server):
   - GET gegen `/projects` bei abgeschaltetem Backend.
   - Response-Status muss `503` sein; Body gegen `ErrorResponse` validieren.

7. **Strukturelle Vollständigkeit**:
   - Jedes Response-Objekt wird auf das Vorhandensein aller im Schema als `required` markierten Felder geprüft — keine zusätzlichen Felder, die laut Schema nicht erlaubt sind (wenn `additionalProperties: false` gesetzt).

---

## Erwartetes Ergebnis

Alle HTTP-Antworten der drei Endpunkte stimmen in Struktur, Pflichtfeldern, Feldtypen und Enum-Werten exakt mit dem OpenAPI-Schema aus CON-0147 überein. Kein validierter Request oder Response erzeugt eine Schema-Verletzung. Fehlercodes und Fehlerobjekte entsprechen den im Schema definierten Error-Komponenten.

---

## Negativfälle / Edge Cases

| Szenario | Erwartetes Verhalten |
|---|---|
| Projekt-ID enthält Sonderzeichen (`/`, `?`, Leerzeichen) | `400` oder `404`, Body Schema-konform |
| `GET /projects` gibt leeres Array zurück (kein Projekt hinterlegt) | `200` mit `[]` — Schema muss leeres Array erlauben |
| Start-Aktion auf bereits `running`-Projekt | `409 Conflict` oder idempotentes `200`/`202` — muss im Schema definiert sein |
| Stop-Aktion auf bereits `stopped`-Projekt | analog |
| Response enthält unbekanntes Zusatzfeld | schlägt fehl, wenn `additionalProperties: false`; wird dokumentiert |
| Response-Feld `status` enthält undokumentierten Wert (z. B. `"error"`) | Schema-Verletzung — Test schlägt fehl und meldet Enum-Abweichung |
| Hub antwortet mit `200` aber leerem Body | Schema-Verletzung — Pflichtfelder fehlen |

---

## Verknüpfung mit dem Contract

TST-0170 ist der primäre Validierungstest für **CON-0147** und deckt alle dort spezifizierten Endpunkte, Statuscodes und Datenschemata ab. Die in CON-0147 definierten Pflichtfelder der Objekte `Project`, `ProjectStatusResponse` und `ErrorResponse` bilden die direkte Prüfgrundlage. Änderungen an CON-0147 (Schema-Version bump, neue Felder, geänderte Enum-Werte) erfordern zwingend eine Aktualisierung dieses Tests. Der Test schlägt fehl, wenn die tatsächliche API-Antwort nicht mit dem im Contract versionierten Schema übereinstimmt — nicht erst, wenn die Antwort inhaltlich falsch ist.

---

## Hinweise zur Implementierung

**Framework / Tools:**

- **[Schemathesis](https://schemathesis.readthedocs.io/)** empfohlen: generiert aus dem OpenAPI-Dokument automatisch Test-Cases für alle Endpunkte und prüft Response-Konformität ohne manuell geschriebene Assertions. Minimaler Aufwand bei vollständiger Coverage.
- Alternativ: **pytest** + **jsonschema** + **httpx** für explizite, gut lesbare Einzeltests pro Endpunkt.
- Für den Hub-Mock: **Prism** (OpenAPI-Mock-Server) oder **pytest-httpserver** — erlaubt isoliertes Testen ohne laufende Hub-Instanz.

**Empfohlene Struktur (pytest + schemathesis):**

```python
# tests/contract/test_tst_0170_hub_control_api.py
import schemathesis

schema = schemathesis.from_path("fixtures/hub-control-api.openapi.yaml", base_url=HUB_BASE_URL)

@schema.parametrize()
def test_hub_control_api_schema_conformance(case):
    response = case.call()
    case.validate_response(response)
```

**CI-Hinweis**: Der Test sollte in einer dedizierten Contract-Test-Stage laufen, nach Unit-Tests, aber vor Integrations- und Acceptance-Tests. Bei Mock-Betrieb kann er offline in der Pipeline ausgeführt werden; gegen die echte Hub-Instanz nur in Staging-Umgebungen.