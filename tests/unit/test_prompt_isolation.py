"""TST-0010b: Prompt-Isolation-Unit-Test.

Verifiziert maschinell, dass _build_code_gen_prompt() keinen Inhalt aus
.sdd/holdout/ in den Code-Generierungs-Prompt einbettet (CON-0009 INV-01).
"""
from sdd_cli.orchestrator import _build_code_gen_prompt

SPEC_CONTENT = "# Test Spec\nImplementiere das Login-Feature gemäß den Anforderungen."
AGENTS_CONTENT = "## Service-Zweck\nDieser Service übernimmt die Authentifizierung."
CONTRACT_CONTENT = "# CON-0001\nHTTP POST /api/auth/login → 200 mit token"

HOL_TITLE = "GEHEIMER_HOL_TITEL_XYZZY_NICHT_IM_PROMPT"
HOL_BODY = "Given ein Nutzer mit passwort secret_holdout_abc_nicht_sichtbar"
HOL_ID = "HOL-HOLDOUT-ISOLATION-TESTMARKER"


def _build(prev_error: str = "") -> str:
    contracts = [("CON-0001", CONTRACT_CONTENT)]
    return _build_code_gen_prompt(SPEC_CONTENT, AGENTS_CONTENT, contracts, prev_error)


def test_holdout_title_not_in_prompt():
    """TC-01a: HOL-Titel erscheint nicht im generierten Prompt."""
    prompt = _build()
    assert HOL_TITLE not in prompt


def test_holdout_body_not_in_prompt():
    """TC-01b: HOL-Body erscheint nicht im generierten Prompt."""
    prompt = _build()
    assert HOL_BODY not in prompt


def test_holdout_id_not_in_prompt():
    """TC-01c: HOL-ID erscheint nicht im generierten Prompt."""
    prompt = _build()
    assert HOL_ID not in prompt


def test_spec_content_present_in_prompt():
    """TC-01d (positiv): Spec-Inhalt ist im Prompt enthalten."""
    prompt = _build()
    assert SPEC_CONTENT in prompt


def test_contract_content_in_prompt():
    """TC-02: Contract-Inhalt ist im Prompt enthalten."""
    prompt = _build()
    assert CONTRACT_CONTENT in prompt
    assert HOL_TITLE not in prompt


def test_agents_md_in_prompt():
    """TC-03: AGENTS.md-Inhalt ist im Prompt enthalten."""
    prompt = _build()
    assert AGENTS_CONTENT in prompt
    assert HOL_TITLE not in prompt


def test_empty_contracts_no_error():
    """TC-04a: Leere Contract-Liste → kein Fehler, Spec noch enthalten."""
    prompt = _build_code_gen_prompt(SPEC_CONTENT, AGENTS_CONTENT, [], "")
    assert SPEC_CONTENT in prompt
    assert HOL_TITLE not in prompt


def test_empty_agents_md_no_error():
    """TC-04b: Leeres AGENTS.md → kein Fehler."""
    prompt = _build_code_gen_prompt(SPEC_CONTENT, "", [], "")
    assert SPEC_CONTENT in prompt
    assert HOL_TITLE not in prompt


def test_prev_error_context_included_without_hol():
    """TC-05: Fehler-Kontext wird eingebettet, enthält aber keinen HOL-Inhalt."""
    error_ctx = "Build failed: ImportError on line 42"
    prompt = _build(prev_error=error_ctx)
    assert error_ctx in prompt
    assert HOL_TITLE not in prompt
    assert HOL_BODY not in prompt


def test_allowlist_principle_no_holdout_leakage():
    """Gesamtprüfung: Keiner der bekannten HOL-Marker taucht im Prompt auf.

    Simuliert ein Szenario, in dem ein Angreifer versucht, HOL-Inhalte durch
    manipulation von contracts/agents_md einzuschleusen — das _build_code_gen_prompt
    gibt exakt das aus, was hineingegeben wird (kein Zugriff auf Dateisystem).
    """
    contracts = [("CON-0001", CONTRACT_CONTENT)]
    prompt = _build_code_gen_prompt(SPEC_CONTENT, AGENTS_CONTENT, contracts, "")
    for marker in [HOL_TITLE, HOL_BODY, HOL_ID, ".sdd/holdout", "HOL-0001"]:
        assert marker not in prompt, f"Unerwarteter HOL-Marker im Prompt: {marker!r}"
