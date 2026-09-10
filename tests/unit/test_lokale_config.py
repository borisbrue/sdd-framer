"""Lokale Ergaenzung zur Konfiguration: .sdd/config.local.yaml (#103).

Der PWA-Token ist die Bearer-Credential fuer POST /api/remote/run. Er stand in
der versionierten .sdd/config.yaml, und jede Rotation schrieb den neuen Wert
genau dorthin zurueck. Jetzt ueberlagert eine gitignorte Datei die
Konfiguration; wer config.yaml schreibt, nimmt nur die Basis.
"""
from __future__ import annotations

import stat
import subprocess
from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def projekt(tmp_path):
    sdd = tmp_path / ".sdd"
    sdd.mkdir()
    (sdd / "config.yaml").write_text(
        "project:\n  name: Probe\n"
        "pwa:\n  auth:\n    token: ''\n"
        "llm:\n  provider: claude-cli\n  timeout_seconds: 600\n"
        "languages: [python, typescript]\n",
        encoding="utf-8",
    )
    return tmp_path


def _lokal(root: Path, text: str) -> None:
    (root / ".sdd" / "config.local.yaml").write_text(text, encoding="utf-8")


class TestUeberlagerung:
    def test_ohne_lokale_datei_ist_alles_wie_vorher(self, projekt):
        from sdd_cli.config import load_config

        cfg = load_config(projekt)
        assert cfg.raw == cfg.basis
        assert cfg.raw["project"]["name"] == "Probe"

    def test_lokaler_wert_sticht(self, projekt):
        from sdd_cli.config import load_config

        _lokal(projekt, "pwa:\n  auth:\n    token: abc123\n")
        cfg = load_config(projekt)
        assert cfg.raw["pwa"]["auth"]["token"] == "abc123"

    def test_ueberlagerung_ist_rekursiv(self, projekt):
        """Ein lokaler Schluessel ersetzt nicht den ganzen Abschnitt."""
        from sdd_cli.config import load_config

        _lokal(projekt, "llm:\n  timeout_seconds: 900\n")
        cfg = load_config(projekt)
        assert cfg.raw["llm"]["timeout_seconds"] == 900
        assert cfg.raw["llm"]["provider"] == "claude-cli"

    def test_listen_werden_ersetzt_nicht_verschmolzen(self, projekt):
        from sdd_cli.config import load_config

        _lokal(projekt, "languages: [go]\n")
        assert load_config(projekt).raw["languages"] == ["go"]

    def test_basis_bleibt_die_versionierte_datei(self, projekt):
        """Genau das, was ein Schreiber zurueckschreiben darf."""
        from sdd_cli.config import load_config

        _lokal(projekt, "pwa:\n  auth:\n    token: geheim\n")
        cfg = load_config(projekt)
        assert cfg.basis["pwa"]["auth"]["token"] == ""
        assert cfg.basis == yaml.safe_load(
            (projekt / ".sdd" / "config.yaml").read_text(encoding="utf-8")
        )

    def test_basis_und_raw_teilen_keinen_zustand(self, projekt):
        """Wer raw veraendert, darf die Basis nicht mitveraendern."""
        from sdd_cli.config import load_config

        cfg = load_config(projekt)
        cfg.raw["llm"]["provider"] = "anders"
        assert cfg.basis["llm"]["provider"] == "claude-cli"

    def test_kaputte_lokale_datei_ist_kein_dict(self, projekt):
        from sdd_cli.config import load_config

        _lokal(projekt, "- nur\n- eine\n- liste\n")
        assert load_config(projekt).raw == load_config(projekt).basis


class TestSetLocal:
    def test_legt_datei_an(self, projekt):
        from sdd_cli.config import load_local, set_local

        set_local(projekt, "pwa.auth.token", "f" * 64)
        assert load_local(projekt)["pwa"]["auth"]["token"] == "f" * 64

    def test_rechte_sind_0600(self, projekt):
        """Die Datei ist fuer Geheimnisse da."""
        from sdd_cli.config import set_local

        pfad = set_local(projekt, "pwa.auth.token", "x")
        assert stat.S_IMODE(pfad.stat().st_mode) == 0o600

    def test_andere_lokale_schluessel_bleiben(self, projekt):
        from sdd_cli.config import load_local, set_local

        _lokal(projekt, "llm:\n  timeout_seconds: 900\n")
        set_local(projekt, "pwa.auth.token", "neu")
        daten = load_local(projekt)
        assert daten["llm"]["timeout_seconds"] == 900
        assert daten["pwa"]["auth"]["token"] == "neu"

    def test_versionierte_datei_bleibt_unberuehrt(self, projekt):
        from sdd_cli.config import set_local

        vorher = (projekt / ".sdd" / "config.yaml").read_text(encoding="utf-8")
        set_local(projekt, "pwa.auth.token", "neu")
        assert (projekt / ".sdd" / "config.yaml").read_text(encoding="utf-8") == vorher

    def test_keine_temporaeren_reste(self, projekt):
        from sdd_cli.config import set_local

        set_local(projekt, "pwa.auth.token", "neu")
        assert not list((projekt / ".sdd").glob("*.tmp"))

    def test_kopf_warnt_vor_versionierung(self, projekt):
        from sdd_cli.config import set_local

        pfad = set_local(projekt, "pwa.auth.token", "neu")
        assert "NICHT versionieren" in pfad.read_text(encoding="utf-8")


class TestGitignore:
    def test_init_traegt_eintrag_ein(self, tmp_path):
        from sdd_cli.init import init_project

        init_project(tmp_path, title="Probe")
        assert ".sdd/config.local.yaml" in (tmp_path / ".gitignore").read_text(encoding="utf-8")

    def test_eintrag_wird_nicht_verdoppelt(self, tmp_path):
        from sdd_cli.init import ignore_local_config

        assert ignore_local_config(tmp_path) is True
        assert ignore_local_config(tmp_path) is False
        text = (tmp_path / ".gitignore").read_text(encoding="utf-8")
        assert text.count(".sdd/config.local.yaml") == 1

    def test_dieses_repo_ignoriert_die_datei(self):
        ergebnis = subprocess.run(
            ["git", "check-ignore", "-q", ".sdd/config.local.yaml"],
            cwd=_ROOT, capture_output=True,
        )
        assert ergebnis.returncode == 0, ".sdd/config.local.yaml ist nicht gitignored"


class TestDiesesRepo:
    def test_versionierte_config_traegt_keinen_token(self):
        """Der konkrete Befund aus #103."""
        raw = yaml.safe_load((_ROOT / ".sdd" / "config.yaml").read_text(encoding="utf-8"))
        assert (raw.get("pwa") or {}).get("auth", {}).get("token", "") == ""


# ── End-to-End gegen die echten Endpunkte ─────────────────────────────────────

@pytest.fixture
def server(projekt, monkeypatch):
    """Echter sdd_context auf einem tmp-Projekt, echte Router."""
    import sdd_context
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from routes.auth import router as auth_router
    from routes.commands import router as commands_router

    # sdd_context ist ein Modul-Singleton. Andere Testdateien rufen beim Import
    # sdd_context.init(REPO_ROOT) auf — also bei der Sammlung, bevor irgendein
    # Test laeuft. Ein init() hier ohne Rueckstellung liess alle spaeteren Tests
    # ein leeres tmp-Projekt sehen: im Einzellauf unsichtbar, im Gesamtlauf
    # sechs rote Orchestrate-Tests. monkeypatch merkt sich jeden Ausgangswert
    # und stellt ihn am Testende wieder her, egal was init() dazwischen setzt.
    for name in ("_root", "_config", "_log_event_bus", "_log_streamer",
                 "_external_url", "_allowed_origins"):
        if hasattr(sdd_context, name):
            wert = getattr(sdd_context, name)
            monkeypatch.setattr(sdd_context, name, list(wert) if isinstance(wert, list) else wert)
    sdd_context.init(projekt)
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(commands_router)
    return TestClient(app), projekt


def _versioniert(root: Path) -> dict:
    return yaml.safe_load((root / ".sdd" / "config.yaml").read_text(encoding="utf-8"))


class TestTokenEndpunkte:
    def test_generate_schreibt_lokal_nicht_versioniert(self, server):
        client, root = server
        assert client.post("/auth/generate-token").status_code == 201

        from sdd_cli.config import load_local
        token = load_local(root)["pwa"]["auth"]["token"]
        assert len(token) == 64
        assert _versioniert(root)["pwa"]["auth"]["token"] == ""

    def test_rotation_schreibt_lokal_nicht_versioniert(self, server):
        """Der Kern von #103: jede Rotation schrieb den neuen Wert genau
        dorthin zurueck, wo der alte das Problem war."""
        client, root = server
        client.post("/auth/generate-token")
        from sdd_cli.config import load_local
        alt = load_local(root)["pwa"]["auth"]["token"]

        r = client.post("/auth/rotate-token", headers={"Authorization": f"Bearer {alt}"})
        assert r.status_code == 200
        neu = r.json()["token"]
        assert neu != alt
        assert load_local(root)["pwa"]["auth"]["token"] == neu
        assert neu not in (root / ".sdd" / "config.yaml").read_text(encoding="utf-8")

    def test_rotation_laesst_config_yaml_byteweise_unberuehrt(self, server):
        """Die Absicht hinter dem alten CON-0088-Test (project.name bleibt) —
        jetzt strukturell: die Datei wird gar nicht mehr geschrieben."""
        client, root = server
        client.post("/auth/generate-token")
        from sdd_cli.config import load_local
        alt = load_local(root)["pwa"]["auth"]["token"]
        vorher = (root / ".sdd" / "config.yaml").read_bytes()

        client.post("/auth/rotate-token", headers={"Authorization": f"Bearer {alt}"})
        assert (root / ".sdd" / "config.yaml").read_bytes() == vorher

    def test_neuer_token_gilt_sofort(self, server):
        """Die Ueberlagerung greift auch nach reload_config."""
        client, root = server
        client.post("/auth/generate-token")
        from sdd_cli.config import load_local
        alt = load_local(root)["pwa"]["auth"]["token"]
        neu = client.post(
            "/auth/rotate-token", headers={"Authorization": f"Bearer {alt}"}
        ).json()["token"]
        r = client.post("/auth/rotate-token", headers={"Authorization": f"Bearer {neu}"})
        assert r.status_code == 200


class TestPatchConfigLeaktNicht:
    def test_patch_schreibt_lokalen_token_nicht_zurueck(self, server):
        """PATCH /config baute `dict(cfg.raw)` und schrieb es zurueck — mit der
        Ueberlagerung waere der lokale Token in der versionierten Datei gelandet."""
        client, root = server
        client.post("/auth/generate-token")
        from sdd_cli.config import load_local
        token = load_local(root)["pwa"]["auth"]["token"]

        r = client.patch("/config", json={"title": "Neuer Titel"})
        assert r.status_code == 200
        text = (root / ".sdd" / "config.yaml").read_text(encoding="utf-8")
        assert "Neuer Titel" in text
        assert token not in text

    def test_get_config_zeigt_den_token_nicht(self, server):
        """Die Rohansicht der Konfiguration im Web-UI zeigte bisher den Token."""
        client, root = server
        client.post("/auth/generate-token")
        from sdd_cli.config import load_local
        token = load_local(root)["pwa"]["auth"]["token"]
        assert token not in client.get("/config").json()["yaml"]
