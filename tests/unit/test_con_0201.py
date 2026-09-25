"""TST-0230 – CON-0201: Supervisor-Commands für S1 bis S3.

Spec: SPEC-0053 · Contract: CON-0201
"""
from __future__ import annotations

import pytest

from tests.support.quality_project import schema_errors

ERLAUBT = {"S1": {"approve", "revise", "halt"},
           "S2": {"retry_with_hint", "reassign", "redecompose", "halt"},
           "S3": {"accept_frs", "halt"}}
FELDER = {"retry_with_hint": {"task_id": "t-1", "hint": "h"},
          "reassign": {"task_id": "t-1", "role": "implementer", "model": "m2"},
          "accept_frs": {"frs": [{"id": "FR-01", "status": "erfüllt", "evidence": "tests/a"}]}}


def _cmd(point, name, **extra):
    return {"point": point, "command": name, "reason": "begründet", **FELDER.get(name, {}),
            **extra}


def test_tc01_valid_instance_passes():
    """Valides Command (CON-0201): reassign in S2."""
    assert schema_errors("supervisor_command", _cmd("S2", "reassign")) == []


def test_tc02_invalid_instance_rejected():
    """Beispiel aus dem Contract: approve in S2 ohne Begründung."""
    assert schema_errors("supervisor_command", {"point": "S2", "command": "approve"})


@pytest.mark.parametrize("point", ["S1", "S2", "S3"])
@pytest.mark.parametrize("name", sorted({c for cs in ERLAUBT.values() for c in cs}))
def test_inv02_commands_je_punkt(point, name):
    fehler = schema_errors("supervisor_command", _cmd(point, name))
    assert (fehler == []) is (name in ERLAUBT[point])


def test_inv01_begruendung_pflicht():
    cmd = _cmd("S1", "approve")
    del cmd["reason"]
    assert schema_errors("supervisor_command", cmd)
    assert schema_errors("supervisor_command", _cmd("S1", "approve", reason=""))


def test_inv03_reassign_nie_an_supervisor():
    assert schema_errors("supervisor_command", _cmd("S2", "reassign", role="supervisor"))


def test_inv04_accept_frs_mit_beleg():
    assert schema_errors("supervisor_command", _cmd("S3", "accept_frs", frs=[
        {"id": "FR-01", "status": "erfüllt"}]))
    assert schema_errors("supervisor_command", _cmd("S3", "accept_frs", frs=[
        {"id": "FR-01", "status": "ok", "evidence": "x"}]))


def test_unbekannte_felder():
    assert schema_errors("supervisor_command", _cmd("S1", "approve", extra="x"))
