"""SPEC-0054 FR-05, CON-0194 INV-01/INV-02/INV-07: Regeln laden, Schichten zuordnen."""
from __future__ import annotations

import pytest
import yaml

from sdd_cli.quality.arch.rules import ArchConfigError, layer_of, load_architecture


def _schreiben(root, daten):
    (root / ".sdd").mkdir(exist_ok=True)
    (root / ".sdd/architecture.yaml").write_text(yaml.safe_dump(daten, sort_keys=False))


def test_laden_und_erste_passende_schicht(tmp_path):
    _schreiben(tmp_path, {"version": 1, "layers": {"web": ["src/web/**"], "core": ["src/**"]},
                          "rules": [{"id": "ARCH-01", "adr": "ADR-0001",
                                     "kind": "forbidden_dependency", "from": "core",
                                     "to_layers": "web"}]})
    arch = load_architecture(tmp_path)
    assert list(arch.layers) == ["web", "core"]
    assert layer_of("src/web/a.py", arch.layers) == "web"
    assert layer_of("src/b.py", arch.layers) == "core"
    assert layer_of("scripts/x.py", arch.layers) is None
    regel = arch.rules[0]
    assert regel.id == "ARCH-01" and regel.severity == "error"
    assert regel.params["to_layers"] == "web"


def test_fehlende_datei(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_architecture(tmp_path)


def test_schemafehler(tmp_path):
    _schreiben(tmp_path, {"version": 1, "layers": {"a": ["x/**"]},
                          "rules": [{"id": "ARCH-01", "kind": "forbidden_dependency",
                                     "from": "a", "to_layers": ["a"]}]})
    with pytest.raises(ArchConfigError) as fehler:
        load_architecture(tmp_path)
    assert any("adr" in p for p, _ in fehler.value.problems)


def test_unbekannte_schichten_je_regel(tmp_path):
    _schreiben(tmp_path, {"version": 1, "layers": {"a": ["x/**"]}, "rules": [
        {"id": "ARCH-01", "adr": "ADR-0001", "kind": "forbidden_dependency", "from": "b",
         "to_layers": ["a", "c"]}]})
    assert load_architecture(tmp_path).rules[0].unknown_layers(["a"]) == ["b", "c"]
