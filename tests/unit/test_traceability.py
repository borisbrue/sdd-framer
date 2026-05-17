"""Unit-Tests für traceability.py – Traceability-Matrix (SPEC-0007)."""
from __future__ import annotations

from pathlib import Path

import pytest

from sdd_cli.traceability import build_matrix, write_matrix
from sdd_cli.config import SddConfig


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _cfg(tmp_path: Path, raw: dict | None = None) -> SddConfig:
    sdd = tmp_path / ".sdd"
    (sdd / "specs").mkdir(parents=True)
    (sdd / "contracts").mkdir(parents=True)
    (sdd / "tests").mkdir(parents=True)
    return SddConfig(root=tmp_path, raw=raw or {})


def _write_spec(path: Path, spec_id: str, title: str = "T", status: str = "draft",
                contracts: list[str] | None = None, tests: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    contracts_yaml = str(contracts).replace("'", '"') if contracts else "[]"
    tests_yaml = str(tests).replace("'", '"') if tests else "[]"
    path.write_text(
        f"---\nid: {spec_id}\ntitle: {title}\nstatus: {status}\n"
        f"contracts: {contracts_yaml}\ntests: {tests_yaml}\n---\nbody\n",
        encoding="utf-8",
    )


def _write_contract(path: Path, contract_id: str, ctype: str = "openapi",
                    tests: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tests_yaml = str(tests).replace("'", '"') if tests else "[]"
    path.write_text(
        f"---\nid: {contract_id}\ntype: {ctype}\ntests: {tests_yaml}\n---\nbody\n",
        encoding="utf-8",
    )


def _write_test(path: Path, test_id: str, level: str = "contract",
                status: str = "draft") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nid: {test_id}\nlevel: {level}\nstatus: {status}\n---\nbody\n",
        encoding="utf-8",
    )


# ─── build_matrix ─────────────────────────────────────────────────────────────

class TestBuildMatrix:
    def test_empty_project_returns_header(self, tmp_path):
        cfg = _cfg(tmp_path)
        result = build_matrix(cfg)
        assert "Traceability-Matrix" in result
        assert "Spec → Contract → Test" in result

    def test_spec_without_contracts_shows_dash(self, tmp_path):
        cfg = _cfg(tmp_path)
        _write_spec(tmp_path / ".sdd" / "specs" / "SPEC-0001.md", "SPEC-0001", "Feature A")
        result = build_matrix(cfg)
        assert "SPEC-0001" in result
        assert "Feature A" in result
        # No contracts → row with dashes
        assert "| — | — | — | — | — |" in result

    def test_spec_with_contract_but_no_tests(self, tmp_path):
        cfg = _cfg(tmp_path)
        _write_spec(
            tmp_path / ".sdd" / "specs" / "SPEC-0001.md", "SPEC-0001",
            contracts=["CON-0001"],
        )
        _write_contract(tmp_path / ".sdd" / "contracts" / "CON-0001.md", "CON-0001")
        result = build_matrix(cfg)
        assert "CON-0001" in result
        assert "openapi" in result

    def test_full_chain_spec_contract_test(self, tmp_path):
        cfg = _cfg(tmp_path)
        _write_spec(
            tmp_path / ".sdd" / "specs" / "SPEC-0001.md", "SPEC-0001",
            contracts=["CON-0001"], tests=["TST-0001"],
        )
        _write_contract(
            tmp_path / ".sdd" / "contracts" / "CON-0001.md", "CON-0001",
            tests=["TST-0001"],
        )
        _write_test(
            tmp_path / ".sdd" / "tests" / "TST-0001.md", "TST-0001",
            level="contract", status="draft",
        )
        result = build_matrix(cfg)
        assert "SPEC-0001" in result
        assert "CON-0001" in result
        assert "TST-0001" in result
        assert "contract" in result

    def test_missing_contract_file_shows_fehlt(self, tmp_path):
        cfg = _cfg(tmp_path)
        _write_spec(
            tmp_path / ".sdd" / "specs" / "SPEC-0001.md", "SPEC-0001",
            contracts=["CON-9999"],
        )
        result = build_matrix(cfg)
        assert "FEHLT" in result

    def test_coverage_overview_section(self, tmp_path):
        cfg = _cfg(tmp_path)
        _write_spec(tmp_path / ".sdd" / "specs" / "SPEC-0001.md", "SPEC-0001")
        result = build_matrix(cfg)
        assert "Coverage-Übersicht" in result
        assert "kein Contract" in result

    def test_specs_sorted_by_id(self, tmp_path):
        cfg = _cfg(tmp_path)
        _write_spec(tmp_path / ".sdd" / "specs" / "SPEC-0002.md", "SPEC-0002")
        _write_spec(tmp_path / ".sdd" / "specs" / "SPEC-0001.md", "SPEC-0001")
        result = build_matrix(cfg)
        idx1 = result.index("SPEC-0001")
        idx2 = result.index("SPEC-0002")
        assert idx1 < idx2

    def test_archived_specs_excluded(self, tmp_path):
        cfg = _cfg(tmp_path)
        archive = tmp_path / ".sdd" / "specs" / "_archive"
        archive.mkdir(parents=True)
        _write_spec(archive / "SPEC-0099.md", "SPEC-0099", "Archived")
        result = build_matrix(cfg)
        assert "SPEC-0099" not in result

    def test_spec_with_no_id_in_frontmatter_excluded(self, tmp_path):
        cfg = _cfg(tmp_path)
        p = tmp_path / ".sdd" / "specs" / "noid.md"
        p.write_text("---\ntitle: No ID\n---\nbody\n", encoding="utf-8")
        result = build_matrix(cfg)
        assert "No ID" not in result

    def test_multiple_tests_per_contract(self, tmp_path):
        cfg = _cfg(tmp_path)
        _write_spec(
            tmp_path / ".sdd" / "specs" / "SPEC-0001.md", "SPEC-0001",
            contracts=["CON-0001"],
        )
        _write_contract(
            tmp_path / ".sdd" / "contracts" / "CON-0001.md", "CON-0001",
            tests=["TST-0001", "TST-0002"],
        )
        _write_test(tmp_path / ".sdd" / "tests" / "TST-0001.md", "TST-0001")
        _write_test(tmp_path / ".sdd" / "tests" / "TST-0002.md", "TST-0002")
        result = build_matrix(cfg)
        assert result.count("SPEC-0001") >= 2  # one row per test

    def test_today_date_in_output(self, tmp_path):
        from datetime import date
        cfg = _cfg(tmp_path)
        result = build_matrix(cfg)
        assert date.today().isoformat() in result


# ─── write_matrix ─────────────────────────────────────────────────────────────

class TestWriteMatrix:
    def test_creates_file(self, tmp_path):
        cfg = _cfg(tmp_path)
        path = write_matrix(cfg)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "Traceability-Matrix" in content

    def test_default_output_path(self, tmp_path):
        cfg = _cfg(tmp_path)
        path = write_matrix(cfg)
        assert path == tmp_path / "docs" / "traceability.md"

    def test_custom_output_path_from_config(self, tmp_path):
        cfg = _cfg(tmp_path, raw={"traceability": {"output_path": "reports/trace.md"}})
        path = write_matrix(cfg)
        assert path == tmp_path / "reports" / "trace.md"

    def test_overwrites_existing_file(self, tmp_path):
        cfg = _cfg(tmp_path)
        out = tmp_path / "docs" / "traceability.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("old content", encoding="utf-8")
        write_matrix(cfg)
        assert "Traceability-Matrix" in out.read_text(encoding="utf-8")
