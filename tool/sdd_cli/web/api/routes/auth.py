"""SPEC-0025: Server-Info und Token-Rotation.

CON-0085: GET /api/server-info — kein Auth, gibt name/externalUrl/tokenHash zurück.
CON-0086: POST /api/auth/rotate-token — Bearer-Auth, generiert neuen Token, invalidiert alten.
"""
from __future__ import annotations

import copy
import hashlib
import os
import secrets
import tempfile
import threading

import yaml
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pathlib import Path

import sdd_context

router = APIRouter()

# Lock für atomar-sichere Token-Rotation (CON-0086 INV-01)
_rotation_lock = threading.Lock()


def _get_current_token(config) -> str:
    return config.raw.get("pwa", {}).get("auth", {}).get("token", "")


def _write_config_atomic(config_path, raw: dict) -> None:
    """Schreibt config.yaml atomar via temporäre Datei + rename (CON-0086 INV-03)."""
    content = yaml.dump(raw, allow_unicode=True, default_flow_style=False, sort_keys=False)
    dir_ = config_path.parent
    fd, tmp_path = tempfile.mkstemp(dir=str(dir_), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, str(config_path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


@router.get("/server-info")
async def server_info():
    """CON-0085: Öffentlich, kein Auth. Gibt Metadaten des laufenden Servers zurück."""
    config = sdd_context.get_config()
    name = config.raw.get("project", {}).get("name", "SDD Project")
    external_url = sdd_context.get_external_url()
    token = _get_current_token(config)
    # CON-0085 G-03: nur die ersten 8 Zeichen des SHA-256-Hashes — nie der Token selbst
    token_hash = hashlib.sha256(token.encode()).hexdigest()[:8] if token else ""
    hub_url = sdd_context.get_hub_url()
    return {"name": name, "externalUrl": external_url, "tokenHash": token_hash, "hubUrl": hub_url}


@router.get("/auth/qr-payload")
async def qr_payload():
    """Gibt den vollständigen QR-Code-Inhalt zurück.

    Dieser Endpoint ist ausschliesslich für das Web UI auf dem lokalen Rechner gedacht —
    kein CORS für externe Domains. Gibt HTTP 404 zurück wenn kein Token oder keine
    externe URL konfiguriert ist.
    """
    config = sdd_context.get_config()
    name = config.raw.get("project", {}).get("name", "SDD Project")
    external_url = sdd_context.get_external_url()
    token = _get_current_token(config)
    if not token:
        raise HTTPException(status_code=404, detail="no_token_configured")
    if not external_url:
        raise HTTPException(status_code=404, detail="no_external_url_configured")
    hub_url = sdd_context.get_hub_url()
    root = sdd_context.get_root()
    return {"sdd": 1, "name": name, "url": external_url, "token": token,
            "hub": hub_url, "root": root}


@router.post("/auth/generate-token", status_code=201)
async def generate_token():
    """Erstellt den ersten Token wenn noch keiner existiert. Kein Auth nötig."""
    with _rotation_lock:
        config = sdd_context.get_config()
        if _get_current_token(config):
            raise HTTPException(status_code=409, detail="token_already_exists")
        new_token = secrets.token_hex(32)
        raw = copy.deepcopy(config.raw)
        raw.setdefault("pwa", {}).setdefault("auth", {})["token"] = new_token
        config_path = config.root / ".sdd" / "config.yaml"
        _write_config_atomic(config_path, raw)
        sdd_context.reload_config()
    return {"ok": True}


@router.post("/auth/rotate-token")
async def rotate_token(request: Request):
    """CON-0086: Token-Rotation.

    Verifiziert den alten Token, generiert einen neuen, schreibt ihn in config.yaml
    und trägt den alten in die In-Memory-Blacklist ein.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="invalid_token")
    old_token = auth_header[7:]

    # Lock verhindert doppelte Rotation bei gleichzeitigen Requests (CON-0086 INV-01)
    with _rotation_lock:
        config = sdd_context.get_config()
        current_token = _get_current_token(config)

        if not current_token:
            raise HTTPException(status_code=401, detail="invalid_token")

        # CON-0086 G-05: bereits rotierter Token ist blacklistet → 401
        if sdd_context.is_blacklisted(old_token) or old_token != current_token:
            raise HTTPException(status_code=401, detail="invalid_token")

        # CON-0086 G-02: neuer Token = secrets.token_hex(32) → 64 Hex-Zeichen
        new_token = secrets.token_hex(32)

        raw = copy.deepcopy(config.raw)
        raw.setdefault("pwa", {}).setdefault("auth", {})["token"] = new_token

        config_path = config.root / ".sdd" / "config.yaml"
        _write_config_atomic(config_path, raw)

        # Alten Token sofort invalidieren (CON-0086 G-03)
        sdd_context.blacklist_token(old_token)

        # In-Memory-Config aktualisieren damit der neue Token ab sofort gilt
        sdd_context.reload_config()

    return {"token": new_token}


@router.get("/certs/root-ca", include_in_schema=False)
async def serve_root_ca():
    """Liefert das mkcert Root-CA-Zertifikat zum Installieren auf dem Gerät.

    Kein Auth nötig — das Zertifikat ist öffentlich (nur der Private Key ist geheim).
    iOS Safari erkennt application/x-x509-ca-cert und startet die Profil-Installation.
    """
    candidates = [
        Path.home() / ".local/share/sdd/certs/rootCA.pem",
        Path(sdd_context.get_root()) / ".certs/rootCA.pem" if sdd_context.get_root() else None,
    ]
    for path in candidates:
        if path and path.exists():
            return FileResponse(
                str(path),
                media_type="application/x-x509-ca-cert",
                filename="sdd-root-ca.pem",
            )
    raise HTTPException(status_code=404, detail="root_ca_not_found")
