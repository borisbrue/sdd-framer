"""Shared test fixtures und sys.path-Konfiguration."""
from __future__ import annotations

import sys
from pathlib import Path

# web/api Verzeichnis für WebSocket-Route-Tests (TST-0082)
_WEB_API = Path(__file__).resolve().parents[1] / "web" / "api"
if str(_WEB_API) not in sys.path:
    sys.path.insert(0, str(_WEB_API))
