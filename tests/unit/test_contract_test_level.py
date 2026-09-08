"""Der Test-Stub aus `sdd new contract` muss zum Contract-Typ passen.

main.new_contract() setzte test_level fest auf "contract" — auch fuer Daten-
und Verhaltens-Contracts, fuer die unit bzw. acceptance richtig ist. Der Stub
landete damit im falschen Verzeichnis, und sein Frontmatter behauptete ein
Level, das nicht zum Ablageort passte.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

from sdd_cli.templates import CONTRACT_TEMPLATES


def level_for(fmt: str) -> str:
    """Lazy, damit der Verhaltenstest unten auch gegen einen Stand ohne die
    neuen Symbole laeuft — sonst scheitert schon das Einsammeln des Moduls."""
    # Aliasen: pytest wuerde die Funktion sonst als Testfunktion einsammeln.
    from sdd_cli.templates import test_level_for_contract_format as _impl
    return _impl(fmt)

# Muss zu new_test --level passen.
_VALID_LEVELS = {"unit", "integration", "contract", "acceptance",
                 "performance", "property"}


class TestLevelMapping:
    def test_every_format_maps_to_a_valid_level(self):
        for fmt in CONTRACT_TEMPLATES:
            level = level_for(fmt)
            assert level in _VALID_LEVELS, f"{fmt} -> {level!r} ist kein gueltiges Level"

    def test_data_contracts_are_unit_level(self):
        for fmt in ("json-schema", "avro", "protobuf"):
            assert level_for(fmt) == "unit"

    def test_behavior_contracts_are_acceptance_level(self):
        for fmt in ("gherkin", "markdown"):
            assert level_for(fmt) == "acceptance"

    def test_api_contracts_stay_contract_level(self):
        for fmt in ("openapi", "asyncapi", "graphql", "grpc"):
            assert level_for(fmt) == "contract"

    def test_performance_contracts_are_performance_level(self):
        assert level_for("slo-yaml") == "performance"

    def test_not_every_format_is_contract_level(self):
        """Der eigentliche Defekt: vorher war alles 'contract'."""
        levels = {level_for(f) for f in CONTRACT_TEMPLATES}
        assert len(levels) > 1, "Alle Formate landen auf demselben Level"

    def test_subdir_map_covers_every_format(self):
        from sdd_cli.templates import CONTRACT_SUBDIR
        assert set(CONTRACT_SUBDIR) == set(CONTRACT_TEMPLATES)

    def test_every_subdir_has_a_level(self):
        from sdd_cli.templates import CONTRACT_SUBDIR, CONTRACT_TEST_LEVEL
        assert set(CONTRACT_SUBDIR.values()) <= set(CONTRACT_TEST_LEVEL)

    def test_unknown_format_falls_back_to_contract(self):
        assert level_for("gibt-es-nicht") == "contract"


class TestStubLandsInTheRightPlace:
    """Verhaltensnachweis ohne die neuen Symbole – laeuft auch gegen alten Code."""

    def _project(self, tmp_path: Path) -> Path:
        import subprocess
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, capture_output=True)
        subprocess.run(["sdd", "init", "--name", "P"], cwd=tmp_path,
                       capture_output=True, timeout=180)
        subprocess.run(["sdd", "new", "spec", "Beispiel"], cwd=tmp_path,
                       capture_output=True, timeout=120)
        return tmp_path

    def test_data_contract_stub_is_not_filed_under_contract(self, tmp_path):
        import subprocess

        root = self._project(tmp_path)
        subprocess.run(["sdd", "new", "contract", "--spec", "SPEC-0001",
                        "--format", "json-schema", "--title", "Datenmodell"],
                       cwd=root, capture_output=True, timeout=120)

        stubs = list((root / ".sdd" / "tests").rglob("TST-*.md"))
        assert len(stubs) == 1, f"erwartet genau einen Stub, gefunden: {stubs}"
        stub = stubs[0]
        assert stub.parent.name == "unit", (
            f"Stub eines data-Contracts liegt unter {stub.parent.name}/ statt unit/"
        )
        assert "level: unit" in stub.read_text(encoding="utf-8"), \
            "Frontmatter-Level passt nicht zum Ablageort"
