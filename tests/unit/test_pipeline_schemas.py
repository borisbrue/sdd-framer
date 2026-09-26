"""Die mitgelieferten Pipeline-Schemas entsprechen den Contract-Artefakten (SPEC-0053)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sdd_cli.pipeline.schemas import load_schema

REPO = Path(__file__).resolve().parents[2]
CONTRACT_SCHEMAS = {
    "role-definition": "rollendefinition-frontmatter-von-sdd-roles-rolle-md",
    "role-outputs": "rollenausgaben-decomposer-test-author-implementer-reviewer",
    "supervisor-decision": "supervisor-commands-fuer-s1-bis-s3",
    "pipeline-run": "run-verzeichnis-run-json-state-json-events-decisions-pending-decision",
    "pipeline-capabilities": "profile-rollenbelegung-session-auftrag-und-reopen",
    "role-case": "golden-case-case-yaml",
    "role-eval-report": "eval-report-und-baseline",
}


@pytest.mark.parametrize(("paket", "contract"), CONTRACT_SCHEMAS.items())
def test_paket_schemas_entsprechen_den_contract_artefakten(paket, contract):
    artefakt = REPO / ".sdd/contracts/data" / f"{contract}.schema.json"
    assert load_schema(paket) == json.loads(artefakt.read_text(encoding="utf-8"))
