"""Shared helper: hält die SddConfig als App-State, initialisiert beim Start."""
from __future__ import annotations

import os
import threading
from pathlib import Path

from fastapi import HTTPException

from sdd_cli.config import SddConfig, find_project_root, load_config
from sdd_cli.log_streamer import LogEventBus, LogStreamer

_root: Path | None = None
_config: SddConfig | None = None
_log_event_bus: LogEventBus | None = None
_log_streamer: LogStreamer | None = None

# SPEC-0025: Server-Kontext
_external_url: str = ""
_allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:8000"]

# In-Memory-Blacklist für rotierte Tokens (leert sich bei Server-Neustart)
_token_blacklist: set[str] = set()
_blacklist_lock = threading.Lock()


def init(project_root: str | Path | None = None) -> None:
    """Wird beim Serverstart aufgerufen. Einmalig."""
    global _root, _config, _log_event_bus, _log_streamer, _external_url, _allowed_origins

    if project_root:
        _root = Path(project_root).resolve()
    else:
        env = os.environ.get("SDD_PROJECT_ROOT")
        _root = Path(env).resolve() if env else find_project_root()

    if _root is None:
        raise RuntimeError("Kein SDD-Projekt gefunden. Starte mit --project <pfad>.")
    _config = load_config(_root)

    _external_url = os.environ.get("SDD_EXTERNAL_URL", "")

    raw_origins = os.environ.get("SDD_ALLOWED_ORIGINS", "")
    if raw_origins:
        _allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
    else:
        _allowed_origins = ["http://localhost:5173", "http://localhost:8000"]

    max_lines = _config.raw.get("docker", {}).get("log_stream", {}).get("max_lines", 500)
    _log_event_bus = LogEventBus(max_lines=max_lines)

    from sdd_cli.dev_container import get_runtime
    _log_streamer = LogStreamer(_log_event_bus, get_runtime(_config))


def get_config() -> SddConfig:
    if _config is None:
        raise HTTPException(status_code=503, detail="Server nicht initialisiert.")
    return _config


def reload_config() -> SddConfig:
    """Lädt die config.yaml neu — nach externem Schreiben aufrufen."""
    global _config
    if _root is None:
        raise HTTPException(status_code=503, detail="Server nicht initialisiert.")
    _config = load_config(_root)
    return _config


def get_log_event_bus() -> LogEventBus:
    if _log_event_bus is None:
        raise HTTPException(status_code=503, detail="Server nicht initialisiert.")
    return _log_event_bus


def get_log_streamer() -> LogStreamer:
    if _log_streamer is None:
        raise HTTPException(status_code=503, detail="Server nicht initialisiert.")
    return _log_streamer


# ── SPEC-0025: Token-Rotation & Server-Info ───────────────────────────────────

def get_external_url() -> str:
    return _external_url


def get_allowed_origins() -> list[str]:
    return list(_allowed_origins)


def blacklist_token(token: str) -> None:
    with _blacklist_lock:
        _token_blacklist.add(token)


def is_blacklisted(token: str) -> bool:
    with _blacklist_lock:
        return token in _token_blacklist
