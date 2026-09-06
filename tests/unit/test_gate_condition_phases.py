"""Unit-Tests für die zustandsbasierten Gate-Phasen (CON-0025 Phase 1 und 4).

CON-0025 nennt für die meisten Phasen einen Befehl als Auslöser. Zwei Phasen
haben stattdessen eine Bedingung:

    | 1 | spec-draft      | Datei erstellt   | Pflichtfelder valide                |
    | 4 | contracts-draft | Dateien angelegt | Alle vorgeschlagenen Contracts existieren |

Beide waren unimplementiert, wodurch die Kette bei contracts-review endete und
sdd start für keine Spec erreichbar war.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

from sdd_cli.gate import PHASE_ORDER, ExecutionGate


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _spec(root: Path, spec_id: str = "SPEC-0001", **overrides: str) -> None:
    fields = {
        "id": spec_id,
        "title": '"Beispiel"',
        "status": "draft",
        "owner": '"Boris"',
        "version": "0.1.0",
    }
    fields.update(overrides)
    fm = "\n".join(f"{k}: {v}" for k, v in fields.items() if v is not None)
    _write(root / ".sdd" / "specs" / f"{spec_id}-beispiel.md", f"---\n{fm}\n---\n\n# Beispiel\n")


def _contract(root: Path, cid: str, artifact: str | None, with_artifact_file: bool) -> None:
    art_line = f'artifact: "{artifact}"\n' if artifact else ""
    _write(
        root / ".sdd" / "contracts" / "api" / f"{cid}-beispiel.md",
        f'---\nid: {cid}\ntitle: "Beispiel"\ntype: api\nformat: openapi\n'
        f"spec: SPEC-0001\n{art_line}---\n\n# Contract\n",
    )
    if artifact and with_artifact_file:
        _write(root / artifact, "openapi: 3.1.0\n")


# ─── Konsistenz von PHASE_ORDER ───────────────────────────────────────────────

class TestPhaseOrderConsistency:
    """Der Test, der die Lücke beim Einbauen gefunden hätte."""

    def test_every_phase_is_reachable(self, tmp_path):
        """Jede Phase in PHASE_ORDER hat einen Weg, abgeschlossen zu werden.

        Befehlsbasierte Phasen werden von der CLI gesetzt; die beiden
        zustandsbasierten muss evaluate_condition_phases erreichen. Eine Phase,
        die in keiner der beiden Mengen liegt, blockiert die Kette dauerhaft.
        """
        command_driven = {
            "spec-review",
            "contracts-proposed",
            "contracts-review",
            "tests-generated",
            "regression-ok",
            "spec-approved",
            "execute-unlocked",
        }
        condition_driven = {"spec-draft", "contracts-draft"}
        unreachable = set(PHASE_ORDER) - command_driven - condition_driven
        assert not unreachable, f"Phasen ohne Auslöser: {sorted(unreachable)}"


# ─── Phase 1: spec-draft ──────────────────────────────────────────────────────

class TestSpecDraftPhase:
    def test_completed_when_spec_exists_with_required_fields(self, tmp_path):
        _spec(tmp_path)
        g = ExecutionGate(tmp_path)
        assert "spec-draft" in g.evaluate_condition_phases("SPEC-0001")

    def test_not_completed_when_spec_missing(self, tmp_path):
        g = ExecutionGate(tmp_path)
        assert g.evaluate_condition_phases("SPEC-0001") == []

    @pytest.mark.parametrize("missing", ["id", "title", "status", "owner", "version"])
    def test_not_completed_when_required_field_missing(self, tmp_path, missing):
        _spec(tmp_path, **{missing: None})
        g = ExecutionGate(tmp_path)
        assert "spec-draft" not in g.evaluate_condition_phases("SPEC-0001")

    def test_idempotent(self, tmp_path):
        _spec(tmp_path)
        g = ExecutionGate(tmp_path)
        g.evaluate_condition_phases("SPEC-0001")
        assert g.evaluate_condition_phases("SPEC-0001") == []

    def test_spec_review_is_allowed_without_manual_intervention(self, tmp_path):
        """Der eigentliche Zweck: spec-review braucht keinen Web-API-Aufruf mehr."""
        _spec(tmp_path)
        g = ExecutionGate(tmp_path)
        assert g.can_start_phase("SPEC-0001", "spec-review").allowed


# ─── Phase 4: contracts-draft ─────────────────────────────────────────────────

class TestContractsDraftPhase:
    def _proposed(self, tmp_path, ids: list[str]) -> ExecutionGate:
        _spec(tmp_path)
        g = ExecutionGate(tmp_path)
        g.mark_phase_complete("SPEC-0001", "spec-draft")
        g.mark_phase_complete("SPEC-0001", "spec-review")
        g.mark_phase_complete("SPEC-0001", "contracts-proposed", proposed=ids)
        return g

    def test_completed_when_all_proposed_contracts_exist(self, tmp_path):
        _contract(tmp_path, "CON-0001", ".sdd/contracts/api/a.openapi.yaml", True)
        _contract(tmp_path, "CON-0002", ".sdd/contracts/api/b.openapi.yaml", True)
        g = self._proposed(tmp_path, ["CON-0001", "CON-0002"])
        assert "contracts-draft" in g.evaluate_condition_phases("SPEC-0001")

    def test_not_completed_when_a_contract_document_is_missing(self, tmp_path):
        _contract(tmp_path, "CON-0001", ".sdd/contracts/api/a.openapi.yaml", True)
        g = self._proposed(tmp_path, ["CON-0001", "CON-0002"])
        assert "contracts-draft" not in g.evaluate_condition_phases("SPEC-0001")

    def test_not_completed_when_an_artifact_file_is_missing(self, tmp_path):
        """Ein Contract ohne Artefaktdatei ist noch nicht geschrieben."""
        _contract(tmp_path, "CON-0001", ".sdd/contracts/api/a.openapi.yaml", True)
        _contract(tmp_path, "CON-0002", ".sdd/contracts/api/b.openapi.yaml", False)
        g = self._proposed(tmp_path, ["CON-0001", "CON-0002"])
        assert "contracts-draft" not in g.evaluate_condition_phases("SPEC-0001")

    def test_contract_without_artifact_field_counts_as_present(self, tmp_path):
        """Ohne artifact-Feld gibt es keine Datei zu prüfen – das Dokument genügt."""
        _contract(tmp_path, "CON-0001", None, False)
        g = self._proposed(tmp_path, ["CON-0001"])
        assert "contracts-draft" in g.evaluate_condition_phases("SPEC-0001")

    def test_not_completed_before_contracts_proposed(self, tmp_path):
        """Ohne Vorschlagsliste gibt es nichts zu prüfen."""
        _contract(tmp_path, "CON-0001", ".sdd/contracts/api/a.openapi.yaml", True)
        _spec(tmp_path)
        g = ExecutionGate(tmp_path)
        g.mark_phase_complete("SPEC-0001", "spec-draft")
        g.mark_phase_complete("SPEC-0001", "spec-review")
        assert "contracts-draft" not in g.evaluate_condition_phases("SPEC-0001")

    def test_idempotent(self, tmp_path):
        _contract(tmp_path, "CON-0001", ".sdd/contracts/api/a.openapi.yaml", True)
        g = self._proposed(tmp_path, ["CON-0001"])
        g.evaluate_condition_phases("SPEC-0001")
        assert g.evaluate_condition_phases("SPEC-0001") == []


# ─── Die Kette als Ganzes ─────────────────────────────────────────────────────

class TestChainIsPassable:
    def test_contracts_review_becomes_allowed(self, tmp_path):
        """Der Blocker: contracts-review war unerreichbar."""
        _contract(tmp_path, "CON-0001", ".sdd/contracts/api/a.openapi.yaml", True)
        _spec(tmp_path)
        g = ExecutionGate(tmp_path)
        g.mark_phase_complete("SPEC-0001", "spec-draft")
        g.mark_phase_complete("SPEC-0001", "spec-review")
        g.mark_phase_complete("SPEC-0001", "contracts-proposed", proposed=["CON-0001"])
        assert g.can_start_phase("SPEC-0001", "contracts-review").allowed

    def test_contracts_review_stays_blocked_while_contracts_unwritten(self, tmp_path):
        """Die Phase darf nicht bedingungslos durchwinken."""
        _contract(tmp_path, "CON-0001", ".sdd/contracts/api/a.openapi.yaml", False)
        _spec(tmp_path)
        g = ExecutionGate(tmp_path)
        g.mark_phase_complete("SPEC-0001", "spec-draft")
        g.mark_phase_complete("SPEC-0001", "spec-review")
        g.mark_phase_complete("SPEC-0001", "contracts-proposed", proposed=["CON-0001"])
        result = g.can_start_phase("SPEC-0001", "contracts-review")
        assert not result.allowed
        assert "contracts-draft" in result.reason

    def test_full_chain_reaches_execute_unlocked(self, tmp_path):
        """Von der leeren Wiese bis zur Freigabe, ohne manuellen Eingriff am JSON."""
        _spec(tmp_path)
        _contract(tmp_path, "CON-0001", ".sdd/contracts/api/a.openapi.yaml", True)
        g = ExecutionGate(tmp_path)

        assert g.can_start_phase("SPEC-0001", "spec-review").allowed  # zieht spec-draft nach
        g.mark_phase_complete("SPEC-0001", "spec-review")
        g.mark_phase_complete("SPEC-0001", "contracts-proposed", proposed=["CON-0001"])

        for phase in ("contracts-review", "tests-generated", "regression-ok",
                      "spec-approved", "execute-unlocked"):
            allowed = g.can_start_phase("SPEC-0001", phase)
            assert allowed.allowed, f"{phase} blockiert: {allowed.reason}"
            g.mark_phase_complete("SPEC-0001", phase)

        assert not g.check("SPEC-0001").blocked
