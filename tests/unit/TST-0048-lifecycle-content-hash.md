---
id: TST-0048
project: PRJ-0001
title: "lifecycle – Content-Hash ignoriert status: und updated:"
level: unit
spec: SPEC-0010
contract: CON-0037
status: draft
framework: pytest
artifact: "tests/unit/test_lifecycle.py"
tags: ["lifecycle", "content-hash", "sha256"]
---

# Test: Content-Hash-Berechnung

Unit-Tests für `lifecycle.compute_content_hash()`.

## Test Cases

| TC    | Beschreibung                                              | Erwartet                         |
|-------|-----------------------------------------------------------|----------------------------------|
| TC-01 | Zwei Texte mit gleichem Body aber anderem `status:` → gleicher Hash | Hash identisch |
| TC-02 | Zwei Texte mit gleichem Body aber anderem `updated:` → gleicher Hash | Hash identisch |
| TC-03 | Texte mit unterschiedlichem Body → unterschiedlicher Hash | Hashes verschieden |
| TC-04 | Leerer Text → Hash wird ohne Fehler berechnet             | Valider SHA-256-String (64 hex) |
