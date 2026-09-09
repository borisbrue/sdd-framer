"""AsyncAPI-Contracts erzeugen einen Rumpf je Nachricht (#66).

Der Generator zaehlte Pfade (OpenAPI) und Szenarien (Gherkin) korrekt auf,
Nachrichten nicht: `asyncapi` fiel auf den generischen Einzelrumpf zurueck.

    ✓ CON-0006: tests/contract/test_live_statusstrom.py (1 Tests)

Fuer ein Protokoll mit drei Nachrichtenarten. Wer sich auf die Zahl verlaesst,
haelt es fuer abgedeckt.
"""
from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest

ASYNCAPI_3 = textwrap.dedent("""\
    asyncapi: 3.0.0
    info:
      title: "Statusstrom"
      version: "1.0.0"
    channels:
      status:
        address: "drucker.status.v1"
        messages:
          DruckerGestartet:
            $ref: "#/components/messages/DruckerGestartet"
    operations:
      empfangeStart:
        action: receive
        channel:
          $ref: "#/channels/status"
      empfangeStop:
        action: receive
        channel:
          $ref: "#/channels/status"
      sendeBefehl:
        action: send
        channel:
          $ref: "#/channels/status"
    components:
      messages:
        DruckerGestartet:
          name: DruckerGestartet
    """)

ASYNCAPI_2 = textwrap.dedent("""\
    asyncapi: 2.6.0
    info:
      title: "Statusstrom"
      version: "1.0.0"
    channels:
      drucker.status.v1:
        publish:
          message:
            name: DruckerGestartet
        subscribe:
          message:
            name: BefehlAngenommen
      drucker.fehler.v1:
        publish:
          message:
            name: FehlerGemeldet
    """)

NUR_MESSAGES = textwrap.dedent("""\
    asyncapi: 3.0.0
    info:
      title: "Statusstrom"
      version: "1.0.0"
    components:
      messages:
        A: {name: A}
        B: {name: B}
    """)


def _op(text: str) -> list[str]:
    import yaml
    from sdd_cli.test_generator import _asyncapi_operationen
    return _asyncapi_operationen(yaml.safe_load(text))


class TestAufzaehlung:
    def test_drei_operationen_in_asyncapi_3(self):
        assert len(_op(ASYNCAPI_3)) == 3

    def test_richtungen_zaehlen_einzeln_in_asyncapi_2(self):
        """publish und subscribe eines Kanals sind zwei Operationen."""
        assert len(_op(ASYNCAPI_2)) == 3

    def test_rueckfall_auf_components_messages(self):
        assert sorted(_op(NUR_MESSAGES)) == ["A", "B"]

    def test_leeres_dokument_ergibt_nichts(self):
        assert _op("asyncapi: 3.0.0\ninfo: {title: X, version: '1'}\n") == []


class TestGenerierteDatei:
    def _erzeugen(self, tmp_path: Path, artifact: str) -> str:
        from sdd_cli.test_generator import TestGenerator

        ziel = tmp_path / "contract.asyncapi.yaml"
        ziel.write_text(artifact, encoding="utf-8")
        gen = TestGenerator(tmp_path)
        return gen._render_template({
            "id": "CON-0006",
            "title": "Live-Statusstrom",
            "spec": "SPEC-0002",
            "format": "asyncapi",
            "artifact": "contract.asyncapi.yaml",
        })

    def _tests(self, quelle: str) -> list[str]:
        return [
            k.name for k in ast.parse(quelle).body
            if isinstance(k, ast.FunctionDef) and k.name.startswith("test_")
        ]

    def test_ein_rumpf_je_operation(self, tmp_path):
        namen = self._tests(self._erzeugen(tmp_path, ASYNCAPI_3))
        assert len(namen) == 3, f"erzeugt: {namen}"

    def test_namen_benennen_die_operation(self, tmp_path):
        namen = self._tests(self._erzeugen(tmp_path, ASYNCAPI_3))
        assert any("empfangestart" in n for n in namen), namen
        assert any("sendebefehl" in n for n in namen), namen

    def test_datei_ist_syntaktisch_gueltig(self, tmp_path):
        ast.parse(self._erzeugen(tmp_path, ASYNCAPI_2))

    def test_ohne_aufzaehlbaren_inhalt_sagt_der_rumpf_warum(self, tmp_path):
        """Ehrlich bleiben statt eine 1 zu melden."""
        quelle = self._erzeugen(tmp_path, "asyncapi: 3.0.0\ninfo: {title: X, version: '1'}\n")
        assert len(self._tests(quelle)) == 1
        assert "keine Nachricht aufzaehlbar" in quelle

    def test_zielverzeichnis_ist_api_nicht_contract(self, tmp_path):
        """asyncapi fehlte in der Format-Tabelle und fiel auf contract/ zurueck."""
        from sdd_cli.test_generator import TestGenerator

        ziel = TestGenerator(tmp_path)._output_path("CON-0006", {"format": "asyncapi"})
        assert ziel.parent == tmp_path / "tests" / "api"
