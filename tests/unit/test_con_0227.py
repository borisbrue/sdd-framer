# AUTO-GENERATED from CON-0227 via sdd test generate — do not delete
"""Contract-Tests für Stack-Vorlage und stack-Eintrag (CON-0227).

Spec: SPEC-0057 · Contract: CON-0227
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from tests.support.stack_project import BLUEPRINT_STACKS, REPO, STACK_SCHEMA, write_stack

PACKAGE_SCHEMA = REPO / "tool/sdd_cli/stacks/stack.schema.json"
SHA = "sha256:" + "a" * 64


def _errors(definition: str, instance: object) -> list[str]:
    schema = json.loads(STACK_SCHEMA.read_text(encoding="utf-8"))
    sub = {"$ref": f"#/$defs/{definition}", "$defs": schema["$defs"]}
    return [e.message for e in Draft202012Validator(sub).iter_errors(instance)]


def _entry(**extra: object) -> dict:
    return {"name": "python-cli", "version": "1.0.0", "source": "blueprint",
            "values": {"package_name": "app"}, "files": {".sdd/quality.yaml": SHA}, **extra}


BLUEPRINT = sorted(p.parent.name for p in BLUEPRINT_STACKS.glob("*/stack.yaml"))


def test_tc01_valid_instance_passes():
    """Gültige Instanzen: jede Blueprint-Vorlage und ein stack-Eintrag (CON-0227)."""
    Draft202012Validator.check_schema(json.loads(STACK_SCHEMA.read_text(encoding="utf-8")))
    assert BLUEPRINT == ["python-cli", "python-fastapi"]
    for name in BLUEPRINT:
        daten = yaml.safe_load((BLUEPRINT_STACKS / name / "stack.yaml").read_text())
        assert _errors("stack", daten) == [], name
    assert _errors("entry", _entry()) == []


@pytest.mark.parametrize("instanz", [
    {"name": "x", "version": "1.0.0", "description": "d", "languages": ["py"], "extra": 1},
    {"name": "X_ungueltig", "version": "1.0.0", "description": "d", "languages": ["py"]},
    {"name": "x", "version": "1.0", "description": "d", "languages": ["py"]},
    {"name": "x", "version": "1.0.0", "description": "d", "languages": ["py"],
     "requires": [{"tool": "t"}]},
    {"name": "x", "version": "1.0.0", "description": "d", "languages": ["py"],
     "verify": [{"name": "v"}]},
], ids=["zusatzfeld", "name", "semver", "requires-ohne-befehl", "verify-ohne-befehl"])
def test_tc02_invalid_instance_rejected(instanz):
    """Ungültige Vorlagen werden abgelehnt (CON-0227)."""
    assert _errors("stack", instanz)


@pytest.mark.parametrize("aenderung", [
    {"source": "irgendwo"}, {"files": {"a.txt": "md5:abc"}}, {"values": {"x": 1}},
], ids=["quelle", "hash", "wert-kein-string"])
def test_eintrag_ungueltig(aenderung):
    """INV-04: Quelle, Hash-Format und Platzhalterwerte sind festgelegt."""
    assert _errors("entry", _entry(**aenderung))


def test_paketkopie_gleicht_dem_contract_artefakt():
    assert json.loads(PACKAGE_SCHEMA.read_text()) == json.loads(STACK_SCHEMA.read_text())


# ── INV-01/INV-02: Laden einer Vorlage ────────────────────────────────────────

def test_inv01_name_gleich_verzeichnis(tmp_path):
    from sdd_cli.stacks import StackError, load

    ordner = write_stack(tmp_path, "demo", {"a.txt": "x"})
    (ordner.parent / "anders").mkdir()
    ordner.rename(ordner.parent / "anders" / "demo2")
    with pytest.raises(StackError, match="Verzeichnis"):
        load(ordner.parent / "anders" / "demo2", "user")


def test_inv01_files_pflicht(tmp_path):
    from sdd_cli.stacks import StackError, load

    ordner = write_stack(tmp_path, "demo", {})
    (ordner / "files").rmdir()
    with pytest.raises(StackError, match="files/"):
        load(ordner, "user")


@pytest.mark.parametrize("files,verify", [
    ({"a.txt": "{{unbekannt}}"}, []),
    ({"{{unbekannt}}/a.txt": "x"}, []),
    ({"a.txt": "x"}, [{"name": "v", "command": "echo {{unbekannt}}"}]),
], ids=["inhalt", "pfad", "verify"])
def test_inv02_undeklarierter_platzhalter(tmp_path, files, verify):
    from sdd_cli.stacks import StackError, load

    ordner = write_stack(tmp_path, "demo", files, verify=verify)
    with pytest.raises(StackError, match="unbekannt"):
        load(ordner, "user")


def test_inv02_deklarierte_platzhalter_und_blueprint_laden(tmp_path):
    from sdd_cli.stacks import load

    ordner = write_stack(tmp_path, "demo", {"{{p}}/a.txt": "{{p}}"},
                         placeholders=[{"name": "p", "default": "x"}],
                         verify=[{"name": "v", "command": "test -d {{p}}"}])
    assert load(ordner, "user").placeholders() == {"p": {"name": "p", "default": "x"}}
    for name in BLUEPRINT:
        assert load(BLUEPRINT_STACKS / name, "blueprint").name == name


def test_inv01_kern_kennt_keine_vorlage_mit_namen():
    kern = [*(REPO / "tool/sdd_cli/stacks").glob("*.py")]
    for datei in kern:
        text = datei.read_text(encoding="utf-8")
        for name in BLUEPRINT:
            assert name not in text, f"{datei.name} nennt {name}"


def test_inv03_min_vergleicht_erste_zahlenfolge(tmp_path):
    from sdd_cli.stacks import load
    from sdd_cli.stacks.verify import check_requires

    ordner = write_stack(tmp_path, "demo", {"a.txt": "x"}, requires=[
        {"tool": "neu", "version_command": "echo 'werkzeug 3.12.1 (build 7)'", "min": "3.11"},
        {"tool": "alt", "version_command": "echo 'werkzeug 3.9'", "min": "3.11",
         "install_hint": "neu installieren"},
    ])
    ergebnis = {c.name: c for c in check_requires(load(ordner, "user"), tmp_path)}
    assert ergebnis["Werkzeug neu"].ok
    assert not ergebnis["Werkzeug alt"].ok and "neu installieren" in ergebnis["Werkzeug alt"].message


# ── INV-04: stack: in config.yaml (Regelgruppe stack, CON-0190) ──────────────

@pytest.mark.parametrize("stack,fehler", [
    ([_entry()], False),
    ({"name": "x"}, True),
    ([_entry(files={"a": "md5:1"})], True),
    ([_entry(), _entry()], True),
], ids=["gueltig", "keine-liste", "hash", "doppelt"])
def test_inv04_config_validate(stack, fehler):
    from sdd_cli.config_validator import ConfigValidator

    raw = {"version": "1", "project": {"name": "P", "description": "d"}, "stack": stack}
    probleme = [i for i in ConfigValidator(raw, Path(".")).validate()
                if i.level == "error" and i.path.startswith("stack")]
    assert bool(probleme) is fehler
