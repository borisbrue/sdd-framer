# TST-0217 – PatternUsageService – Scan, Normalisierung, Merge
# Spec: SPEC-0049 · Contract: CON-0185
import json
from pathlib import Path

from sdd_cli.pattern_usage import PatternUsageService


def _setup(tmp: Path, accepted: list[dict], source_files: dict[str, str]) -> PatternUsageService:
    cat = tmp / ".sdd" / "patterns"
    cat.mkdir(parents=True)
    (cat / "_catalog.json").write_text(json.dumps({"accepted_patterns": accepted}), encoding="utf-8")
    src_root = tmp / "src"
    src_root.mkdir()
    for rel, content in source_files.items():
        f = src_root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content, encoding="utf-8")
    return PatternUsageService(root=tmp, scan_roots=[src_root])


class TestTST0217:
    def test_accepted_with_annotation_has_location(self, tmp_path) -> None:
        svc = _setup(
            tmp_path,
            [{"pattern_name": "Strategy", "spec_id": "SPEC-0015",
              "acceptance_reason": "weil X", "refactoring_guru_url": "https://refactoring.guru/x"}],
            {"routing.py": "# Strategy Pattern (Refactoring Guru): austauschbar\nx = 1\n"},
        )
        usage = {u.pattern_name: u for u in svc.usage()}
        assert "Strategy" in usage
        locs = usage["Strategy"].code_locations
        assert len(locs) == 1 and locs[0].file.endswith("routing.py") and locs[0].line == 1

    def test_accepted_without_annotation_empty(self, tmp_path) -> None:
        svc = _setup(
            tmp_path,
            [{"pattern_name": "Observer", "spec_id": "SPEC-0034", "acceptance_reason": "y",
              "refactoring_guru_url": None}],
            {"x.py": "print('nichts')\n"},
        )
        usage = {u.pattern_name: u for u in svc.usage()}
        assert usage["Observer"].code_locations == []

    def test_name_normalization(self, tmp_path) -> None:
        svc = _setup(
            tmp_path,
            [{"pattern_name": "ChainOfResponsibility", "spec_id": "SPEC-0029",
              "acceptance_reason": "z", "refactoring_guru_url": None}],
            {"c.py": "# Chain of Responsibility Pattern: Kette\n"},
        )
        usage = {u.pattern_name: u for u in svc.usage()}
        assert len(usage["ChainOfResponsibility"].code_locations) == 1

    def test_specs_grouped_per_pattern(self, tmp_path) -> None:
        svc = _setup(
            tmp_path,
            [{"pattern_name": "Strategy", "spec_id": "SPEC-0015", "acceptance_reason": "a",
              "refactoring_guru_url": None},
             {"pattern_name": "Strategy", "spec_id": "SPEC-0050", "acceptance_reason": "b",
              "refactoring_guru_url": None}],
            {},
        )
        usage = {u.pattern_name: u for u in svc.usage()}
        assert {s.spec_id for s in usage["Strategy"].specs} == {"SPEC-0015", "SPEC-0050"}

    def test_orphan_annotation_ignored(self, tmp_path) -> None:
        svc = _setup(
            tmp_path,
            [{"pattern_name": "Strategy", "spec_id": "SPEC-0015", "acceptance_reason": "a",
              "refactoring_guru_url": None}],
            {"v.py": "# Visitor Pattern: nicht im Katalog\n"},
        )
        names = {u.pattern_name for u in svc.usage()}
        assert "Visitor" not in names

    def test_empty_catalog_empty_result(self, tmp_path) -> None:
        svc = _setup(tmp_path, [], {"x.py": "# Strategy Pattern: x\n"})
        assert svc.usage() == []
