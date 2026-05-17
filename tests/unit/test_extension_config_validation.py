"""TST-0006: Validiert contracts/data/extension-config.schema.json gegen CON-0005."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).parents[2] / ".sdd" / "contracts" / "data" / "extension-config.schema.json"
PACKAGE_PATH = Path(__file__).parents[2] / "vscode-extension" / "package.json"

REQUIRED_PROPERTIES = {
    "sdd.cliPath",
    "sdd.validateOnSave",
    "sdd.showCodeLens",
    "sdd.treeViewRefreshInterval",
}


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def package() -> dict:
    return json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))


class TestSchemaStructure:
    def test_schema_is_valid_json_schema(self, schema: dict):
        jsonschema.Draft7Validator.check_schema(schema)

    def test_schema_has_required_properties(self, schema: dict):
        defined = set(schema.get("properties", {}).keys())
        assert REQUIRED_PROPERTIES.issubset(defined), (
            f"Fehlende Properties: {REQUIRED_PROPERTIES - defined}"
        )

    def test_no_additional_properties(self, schema: dict):
        assert schema.get("additionalProperties") is False

    def test_cli_path_is_string(self, schema: dict):
        assert schema["properties"]["sdd.cliPath"]["type"] == "string"

    def test_validate_on_save_is_boolean_with_default_true(self, schema: dict):
        prop = schema["properties"]["sdd.validateOnSave"]
        assert prop["type"] == "boolean"
        assert prop["default"] is True

    def test_show_code_lens_is_boolean_with_default_true(self, schema: dict):
        prop = schema["properties"]["sdd.showCodeLens"]
        assert prop["type"] == "boolean"
        assert prop["default"] is True

    def test_refresh_interval_is_integer_with_minimum_0(self, schema: dict):
        prop = schema["properties"]["sdd.treeViewRefreshInterval"]
        assert prop["type"] in ("integer", "number")
        assert prop.get("minimum", -1) >= 0
        assert prop["default"] == 0


class TestSchemaPackageConsistency:
    def test_all_schema_properties_exist_in_package_json(self, schema: dict, package: dict):
        pkg_props = set(package["contributes"]["configuration"]["properties"].keys())
        schema_props = set(schema["properties"].keys())
        missing = schema_props - pkg_props
        assert not missing, f"Properties im Schema aber nicht in package.json: {missing}"

    def test_defaults_match_between_schema_and_package(self, schema: dict, package: dict):
        pkg_props = package["contributes"]["configuration"]["properties"]
        for key, s_prop in schema["properties"].items():
            if key not in pkg_props:
                continue
            s_default = s_prop.get("default")
            p_default = pkg_props[key].get("default")
            assert s_default == p_default, (
                f"{key}: Schema-Default {s_default!r} != package.json-Default {p_default!r}"
            )


class TestSchemaValidation:
    def test_valid_config_passes(self, schema: dict):
        valid = {
            "sdd.cliPath": "/usr/local/bin/sdd",
            "sdd.validateOnSave": False,
            "sdd.showCodeLens": True,
            "sdd.treeViewRefreshInterval": 30,
        }
        jsonschema.validate(valid, schema)

    def test_empty_config_passes(self, schema: dict):
        jsonschema.validate({}, schema)

    def test_unknown_property_fails(self, schema: dict):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({"sdd.unknownKey": True}, schema)

    def test_wrong_type_for_validate_on_save_fails(self, schema: dict):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({"sdd.validateOnSave": "yes"}, schema)

    def test_negative_refresh_interval_fails(self, schema: dict):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({"sdd.treeViewRefreshInterval": -1}, schema)
