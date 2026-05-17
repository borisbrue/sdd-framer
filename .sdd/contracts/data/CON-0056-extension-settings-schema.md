---
id: CON-0056
title: "extension-settings-schema"
type: data
format: json-schema
spec: SPEC-0017
version: 0.1.0
status: draft
artifact: "contracts/data/extension-settings.schema.json"
tests: [TST-0060]
---

# Contract: extension-settings-schema

> **Spec:** SPEC-0017 · **Typ:** Daten (JSON Schema) · **Status:** draft

## Zweck

Definiert das vollständige Schema der VS Code Extension Settings unter dem
`sdd.*`-Namespace. Umfasst alle bestehenden Settings aus SPEC-0002 sowie
die neuen Settings aus SPEC-0017.

## Garantien

- **G-01:** Jede Setting hat einen Typ, einen Default-Wert und eine
  `markdownDescription` für den Settings-Editor.
- **G-02:** `sdd.webUi.port == 0` ist semantisch "dynamisch" und immer ein
  valider Wert – kein Fehler, keine Rückfrage.
- **G-03:** Das Schema wird in `package.json contributes.configuration` eingebunden
  und von VS Code beim Laden der Extension validiert.

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SDD Extension Settings",
  "type": "object",
  "properties": {
    "sdd.executablePath": {
      "type": "string",
      "default": "sdd",
      "markdownDescription": "Pfad zur `sdd`-CLI. Leer = `sdd` im PATH suchen."
    },
    "sdd.pythonPath": {
      "type": "string",
      "default": "python",
      "markdownDescription": "Python-Interpreter für Port-Ermittlung und Server-Start. Muss dieselbe venv wie `sdd` nutzen."
    },
    "sdd.validateOnSave": {
      "type": "boolean",
      "default": true,
      "markdownDescription": "`sdd validate` bei jedem Speichern einer `.md`-Datei ausführen."
    },
    "sdd.treeView.refreshInterval": {
      "type": "number",
      "default": 5000,
      "minimum": 1000,
      "markdownDescription": "TreeView-Aktualisierungsintervall in Millisekunden."
    },
    "sdd.webUi.port": {
      "type": "integer",
      "default": 0,
      "minimum": 0,
      "maximum": 65535,
      "markdownDescription": "Port für den SDD Web UI Server. `0` = freier Port automatisch ermitteln (empfohlen). Fixer Wert z.B. `8000` = fixer Port."
    },
    "sdd.webUi.autoStart": {
      "type": "boolean",
      "default": false,
      "markdownDescription": "Web UI Server automatisch starten wenn ein SDD-Projekt erkannt wird."
    },
    "sdd.webUi.openBrowser": {
      "type": "boolean",
      "default": true,
      "markdownDescription": "Systembrowser automatisch öffnen nachdem der Server erfolgreich gestartet ist."
    },
    "sdd.pipeline.pollInterval": {
      "type": "number",
      "default": 5000,
      "minimum": 1000,
      "maximum": 30000,
      "markdownDescription": "Polling-Intervall für Pipeline-Statusabfragen in Millisekunden."
    }
  },
  "required": []
}
```

## Invarianten

- **INV-01:** `sdd.webUi.port` ist integer, kein float; `minimum: 0`, `maximum: 65535`.
- **INV-02:** Alle Settings haben sinnvolle Defaults, die ohne jede Konfiguration
  ein funktionierendes Setup ergeben.
- **INV-03:** `sdd.pythonPath` und `sdd.executablePath` werden aus demselben venv
  aufgerufen; Abweichung führt zu einem Fehler mit klarer Meldung.

## package.json-Auszug

Das Schema wird direkt in `vscode-extension/package.json` unter
`contributes.configuration.properties` eingetragen. Die Felder `type`,
`default`, `minimum`, `maximum` und `markdownDescription` werden 1:1 übernommen.

```json
"contributes": {
  "configuration": {
    "title": "SDD",
    "properties": {
      "sdd.webUi.port": {
        "type": "integer",
        "default": 0,
        "minimum": 0,
        "maximum": 65535,
        "markdownDescription": "..."
      },
      ...
    }
  }
}
```
