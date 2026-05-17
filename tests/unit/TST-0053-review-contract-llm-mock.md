---
id: TST-0053
project: PRJ-0001
title: "review_contract – LLM via Provider-Mock, TST-Datei-Output"
level: unit
spec: SPEC-0010
contract: CON-0039
status: draft
framework: pytest
artifact: "tests/unit/test_lifecycle.py"
tags: ["lifecycle", "llm-mock", "review-contract", "tst-generation"]
---

# Test: review_contract mit LLM-Mock

Unit-Tests für `lifecycle.review_contract()` mit gemocktem CompletionProvider.

## Test Cases

| TC    | Beschreibung                                                                    | Erwartet                                           |
|-------|---------------------------------------------------------------------------------|----------------------------------------------------|
| TC-01 | approved-LLM-Antwort → TST-Datei mit `generated_by: llm` und `status: draft`   | Frontmatter korrekt                                |
| TC-02 | needs_revision-Antwort → LLM Review Notes an Contract angehängt               | `## LLM Review Notes` am Ende der Contract-Datei  |
| TC-03 | Contract-Datei wird mit neuer TST-ID verknüpft (`tests: ["TST-XXXX"]`)         | Contract-Frontmatter enthält TST-ID               |
| TC-04 | LLM nicht erreichbar (RuntimeError) → Contract bleibt unverändert              | ValueError/RuntimeError propagiert, keine Datei   |
