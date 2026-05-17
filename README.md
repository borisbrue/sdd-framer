# SDD Blueprint

Ein vollständiges, sprachneutrales Spec-Driven Development System.
Bestandteile:

- **`.sdd/`** – Konfiguration, JSON-Schemas, Templates
- **`specs/`** – Specifications mit YAML-Frontmatter
- **`contracts/`** – API-, Daten-, Verhaltens- und Performance-Contracts
- **`tests/`** – Contract-, Unit-, Integration-, Acceptance- und Performance-Tests
- **`docs/`** – Architektur, ADRs, Traceability-Matrix
- **`tool/`** – Die `sdd`-CLI (Python)

## Schnellstart

```bash
# 1. CLI installieren
cd tool
pip install -e .

# 2. Im eigenen Projekt
cd /pfad/zum/eigenen/projekt
sdd init --name "Mein Projekt"

# 3. Erste Spec, Contract, Test
sdd new spec "User Login"
sdd new contract --spec SPEC-0001 --format openapi --title "Login API"
sdd new test --spec SPEC-0001 --contract CON-0001 --level contract --title "OpenAPI Konformitaet"

# 4. IDs in der Spec eintragen (Frontmatter: contracts: [CON-0001], tests: [TST-0001])
$EDITOR specs/SPEC-0001-user-login.md

# 5. Konsistenz prüfen
sdd validate

# 6. Traceability-Matrix erzeugen
sdd trace
```

## Vollständiges Beispiel

Im Repository ist das Feature **"User Login"** komplett ausgearbeitet:

- Spec: `specs/SPEC-0001-user-login.md`
- Contracts:
  - `contracts/api/CON-0001-login.md` + `login.openapi.yaml`
  - `contracts/behavior/CON-0002-login.md` + `login.feature`
  - `contracts/performance/CON-0003-login.md` + `login.slo.yaml`
- Tests: `tests/{contract,acceptance,unit,performance}/TST-000X-*.md`
- ADR: `docs/adr/ADR-0001-brute-force-pro-account.md`
- Traceability: `docs/traceability.md`

So siehst du, wie alle Bestandteile zusammenwirken.

## Garantierte Invarianten

Die CLI setzt durch `sdd validate` folgende Regeln durch:

1. Jede Spec referenziert mindestens einen Contract.
2. Jeder Contract referenziert mindestens einen Test.
3. Alle Referenzen (Spec ↔ Contract ↔ Test) zeigen auf existierende Dokumente.
4. Frontmatter aller Dokumente entspricht den JSON-Schemas.
5. Keine verwaisten Contracts oder Tests ohne Spec-Bezug.

→ In CI eingehängt (`sdd validate --strict`) blockiert das jeden Merge, der gegen diese Regeln verstößt.
