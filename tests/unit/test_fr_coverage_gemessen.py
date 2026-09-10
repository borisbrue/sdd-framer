"""`spec approve` misst die FR-Abdeckung, statt sie sich sagen zu lassen (#67).

Der Befund: fuer SPEC-0002 stand `{'fr_coverage': '', ...}` im Gate, obwohl die
fr_test_map 25 von 25 FR abdeckte. Bei SPEC-0005 stand korrekt `18/18`.

Der Unterschied lag nicht in der Spec: `fr_coverage` war ein CLI-Flag mit
Default "" und wurde nie berechnet. SPEC-0005 bekam seine Zahl, weil der Aufruf
sie mitgab. Der Wert stand im Gate unter `consistency_check` — als haette ihn
etwas geprueft.
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
from click.testing import CliRunner

SPEC = textwrap.dedent("""\
    ---
    id: SPEC-0002
    title: "Steuerung"
    status: reviewed
    contracts: [CON-9001]
    tests: [TST-9001]
    fr_test_map:
      FR-01: TST-0001
      FR-02: TST-0001
      FR-03: TST-0002
    ---

    # Steuerung

    ## Funktionale Anforderungen

    - FR-01: Erstes
    - FR-02: Zweites
    - FR-03: Drittes
    """)


def _spec_doc(text: str = SPEC, tmp: Path | None = None):
    import tempfile

    from sdd_cli.frontmatter import parse

    ziel = Path(tempfile.mkdtemp()) / "SPEC-0002.md"
    ziel.write_text(text, encoding="utf-8")
    return parse(ziel)


def _messung(text: str = SPEC) -> str:
    """Was der Fix eintraegt: covered/gesamt aus der Spec selbst."""
    from sdd_cli.compliance import FrCoverageSpecification
    ergebnis = FrCoverageSpecification().is_satisfied_by(_spec_doc(text), [])
    gesamt = len(ergebnis.covered) + len(ergebnis.uncovered)
    return f"{len(ergebnis.covered)}/{gesamt}" if gesamt else ""


class TestAbdeckungIstMessbar:
    def test_vollstaendige_map_ergibt_volle_abdeckung(self):
        assert _messung() == "3/3"

    def test_luecke_in_der_map_wird_sichtbar(self):
        ohne = SPEC.replace("  FR-03: TST-0002\n", "")
        assert _messung(ohne) == "2/3"

    def test_spec_ohne_fr_ergibt_leere_angabe(self):
        """Leer heisst dann tatsaechlich 'keine FR', nicht 'nicht gemessen'."""
        ohne = SPEC.split("## Funktionale Anforderungen")[0].replace(
            "fr_test_map:\n  FR-01: TST-0001\n  FR-02: TST-0001\n  FR-03: TST-0002\n", ""
        )
        assert _messung(ohne) == ""


class TestCliTraegtDieMessungEin:
    """Der Befund selbst: ohne Flag stand nichts im Gate."""

    def test_approve_ohne_flag_schreibt_die_messung(self, tmp_path, monkeypatch):
        from sdd_cli.main import cli

        root = _projekt(tmp_path)
        monkeypatch.chdir(root)
        ergebnis = CliRunner().invoke(cli, ["spec", "approve", "SPEC-0002"])
        assert ergebnis.exit_code == 0, ergebnis.output
        assert _gate_wert(root) == "3/3"

    def test_widerspruch_zur_angabe_wird_gemeldet(self, tmp_path, monkeypatch):
        from sdd_cli.main import cli

        root = _projekt(tmp_path)
        monkeypatch.chdir(root)
        ergebnis = CliRunner().invoke(
            cli, ["spec", "approve", "SPEC-0002", "--fr-coverage", "99/99"]
        )
        assert ergebnis.exit_code == 0, ergebnis.output
        assert "99/99" in ergebnis.output and "3/3" in ergebnis.output
        assert _gate_wert(root) == "3/3", "die Behauptung darf die Messung nicht schlagen"


# ── Projektgeruest ───────────────────────────────────────────────────────────

def _projekt(tmp_path: Path) -> Path:
    from sdd_cli.init import init_project
    from sdd_cli.gate import ExecutionGate

    init_project(tmp_path, title="Testprojekt")
    (tmp_path / ".sdd" / "specs" / "SPEC-0002-steuerung.md").write_text(
        SPEC, encoding="utf-8"
    )
    con = tmp_path / ".sdd" / "contracts" / "behavior"
    con.mkdir(parents=True, exist_ok=True)
    (con / "CON-9001-steuerung.md").write_text(
        "---\nid: CON-9001\ntitle: \"Steuerung\"\ntype: behavior\n"
        "format: gherkin\nspec: SPEC-0002\nversion: 0.1.0\nstatus: approved\n"
        "tests: [TST-9001]\n---\n\n# Contract\n",
        encoding="utf-8",
    )
    tst = tmp_path / ".sdd" / "tests" / "contract"
    tst.mkdir(parents=True, exist_ok=True)
    (tst / "TST-9001-steuerung.md").write_text(
        "---\nid: TST-9001\ntitle: \"Steuerung\"\nlevel: contract\n"
        "spec: SPEC-0002\ncontract: CON-9001\nstatus: approved\n"
        'artifact: "tests/contract/test_con_9001.py"\n---\n\n# Test\n',
        encoding="utf-8",
    )
    g = ExecutionGate(tmp_path)
    from sdd_cli.gate import PHASE_ORDER
    for phase in PHASE_ORDER[: PHASE_ORDER.index("spec-approved")]:
        g.mark_phase_complete("SPEC-0002", phase)
    return tmp_path


def _gate_wert(root: Path) -> str:
    """Der eingetragene fr_coverage-Wert aus der spec-approved-Phase."""
    daten = json.loads(
        (root / ".sdd" / "pipeline" / "SPEC-0002-gate.json").read_text(encoding="utf-8")
    )
    for eintrag in daten.get("phase_history", []):
        if eintrag.get("phase") == "spec-approved":
            return (eintrag.get("consistency_check") or {}).get("fr_coverage", "")
    raise AssertionError("keine spec-approved-Phase im Gate gefunden")
