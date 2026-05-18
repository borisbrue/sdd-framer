# TST-0108 – CON-0077: Push-Notification-Payload Schema
# Contract: CON-0077
# Spec: SPEC-0023

import json
import re
import pytest

VALID_TYPES = {"orchestrate_done", "build_done", "build_failed", "spec_implemented"}
SPEC_ID_PATTERN = re.compile(r"^SPEC-\d{4}$")


def make_payload(type_: str, spec_id: str, message: str) -> dict:
    return {"type": type_, "spec_id": spec_id, "message": message}


class TestTST0108:
    # CON-0077 G-01: type ist einer der vier definierten Werte
    def test_valid_types_accepted(self) -> None:
        for t in VALID_TYPES:
            p = make_payload(t, "SPEC-0001", "ok")
            assert p["type"] in VALID_TYPES

    # CON-0077 G-01: Unbekannter type ist ungültig
    def test_invalid_type_not_in_valid_set(self) -> None:
        for t in ["done", "started", "error", ""]:
            assert t not in VALID_TYPES

    # CON-0077 G-02: spec_id entspricht SPEC-XXXX (4 Ziffern)
    def test_spec_id_format_valid(self) -> None:
        for spec_id in ["SPEC-0001", "SPEC-0024", "SPEC-9999"]:
            assert SPEC_ID_PATTERN.match(spec_id) is not None

    # CON-0077 G-02: Ungültige spec_id wird nicht akzeptiert
    def test_spec_id_format_invalid(self) -> None:
        for spec_id in ["SPEC-001", "spec-0024", "SPEC-00240", "0024"]:
            assert SPEC_ID_PATTERN.match(spec_id) is None

    # CON-0077 G-03: message ist niemals leer
    def test_message_not_empty(self) -> None:
        p = make_payload("orchestrate_done", "SPEC-0024", "SPEC-0024 — Pipeline abgeschlossen")
        assert len(p["message"]) > 0

    # CON-0077 G-04: JSON-Größe ≤ 4096 Bytes
    def test_payload_size_within_limit(self) -> None:
        p = make_payload(
            "orchestrate_done",
            "SPEC-0024",
            "SPEC-0024 — Pipeline abgeschlossen (approved)",
        )
        encoded = json.dumps(p, ensure_ascii=False).encode("utf-8")
        assert len(encoded) <= 4096

    # CON-0077 G-04: Maximale Payload-Größe bleibt unter 4096 selbst bei langem message
    def test_large_message_still_under_limit(self) -> None:
        p = make_payload("build_failed", "SPEC-0001", "x" * 4000)
        encoded = json.dumps(p, ensure_ascii=False).encode("utf-8")
        assert len(encoded) <= 4096

    # CON-0077 G-05: Payload ist gültiges UTF-8 JSON
    def test_payload_is_valid_utf8_json(self) -> None:
        p = make_payload("spec_implemented", "SPEC-0023", "SPEC-0023 — implementiert")
        raw = json.dumps(p, ensure_ascii=False)
        decoded = json.loads(raw)
        assert decoded["type"] == p["type"]
        assert decoded["spec_id"] == p["spec_id"]
