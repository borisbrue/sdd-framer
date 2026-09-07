"""Jedes Contract-Format muss seine artifact-Datei auch anlegen.

`sdd new contract` schreibt fuer jedes Format einen artifact:-Pfad ins
Frontmatter, legte die Datei aber nur fuer openapi und gherkin an. Fuer die
uebrigen acht zeigte das Frontmatter auf eine Datei, die nie entstand — und
`sdd validate` warnte fuer jeden dieser Contracts.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

from sdd_cli.templates import CONTRACT_TEMPLATES

_ROOT = Path(__file__).resolve().parents[2]
_SKELETON_DIRS = [
    _ROOT / "tool" / "sdd_cli" / "blueprint" / "templates" / "contract",
    _ROOT / ".sdd" / "templates" / "contract",
]

# Muss zu ext_map in main.new_contract passen.
_EXPECTED_EXT = {
    "openapi": "openapi.yaml", "asyncapi": "asyncapi.yaml",
    "graphql": "graphql", "grpc": "proto",
    "json-schema": "schema.json", "avro": "avsc", "protobuf": "proto",
    "gherkin": "feature", "markdown": "md", "slo-yaml": "slo.yaml",
}


class TestEveryFormatHasASkeleton:
    def test_no_format_is_without_skeleton(self):
        ohne = [f for f, (_, _, skel) in CONTRACT_TEMPLATES.items() if not skel]
        assert not ohne, (
            f"Formate ohne Skeleton: {sorted(ohne)} — `sdd new contract` schreibt "
            f"fuer sie einen artifact:-Pfad, legt die Datei aber nicht an."
        )

    def test_skeleton_files_exist_in_both_template_dirs(self):
        for fmt, (_, _, skel) in CONTRACT_TEMPLATES.items():
            for d in _SKELETON_DIRS:
                assert (d / skel).exists(), f"{fmt}: {skel} fehlt in {d}"

    def test_all_ten_formats_are_covered(self):
        assert set(CONTRACT_TEMPLATES) == set(_EXPECTED_EXT)


class TestSkeletonsAreValid:
    """Ein Skeleton, das nicht parst, ist so wenig wert wie gar keines."""

    def _blueprint(self, fmt: str) -> Path:
        return _SKELETON_DIRS[0] / CONTRACT_TEMPLATES[fmt][2]

    def test_yaml_skeletons_parse(self):
        for fmt in ("openapi", "asyncapi", "slo-yaml"):
            data = yaml.safe_load(self._blueprint(fmt).read_text(encoding="utf-8"))
            assert isinstance(data, dict) and data, f"{fmt}: kein YAML-Mapping"

    def test_json_skeletons_parse(self):
        for fmt in ("json-schema", "avro"):
            data = json.loads(self._blueprint(fmt).read_text(encoding="utf-8"))
            assert isinstance(data, dict) and data, f"{fmt}: kein JSON-Objekt"

    def test_proto_skeletons_declare_syntax(self):
        for fmt in ("grpc", "protobuf"):
            text = self._blueprint(fmt).read_text(encoding="utf-8")
            assert 'syntax = "proto3"' in text, f"{fmt}: keine proto3-Deklaration"

    def test_grpc_has_a_service_protobuf_has_not(self):
        """Beide enden auf .proto, meinen aber Verschiedenes."""
        assert "service " in self._blueprint("grpc").read_text(encoding="utf-8")
        assert "service " not in self._blueprint("protobuf").read_text(encoding="utf-8")

    def test_graphql_skeleton_has_a_type(self):
        assert "type Query" in self._blueprint("graphql").read_text(encoding="utf-8")

    def test_markdown_skeleton_has_invariants(self):
        assert "INV-01" in self._blueprint("markdown").read_text(encoding="utf-8")

    def test_both_template_dirs_hold_identical_skeletons(self):
        for fmt, (_, _, skel) in CONTRACT_TEMPLATES.items():
            texts = {d.name: (d / skel).read_text(encoding="utf-8") for d in _SKELETON_DIRS}
            assert len(set(texts.values())) == 1, f"{fmt}: Blueprint und .sdd weichen ab"
