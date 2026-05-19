"""Hub – Multi-Projekt-Dashboard.

POST /api/hub/register   – Projektserver anmelden
POST /api/hub/deregister – Projektserver abmelden
GET  /api/hub/projects   – Alle registrierten Server
GET  /hub                – Browser-Dashboard (HTML)
"""
from __future__ import annotations

import asyncio
import threading
from typing import Any

import httpx
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

router = APIRouter()

_HEALTH_INTERVAL = 15   # Sekunden zwischen Health-Checks
_HEALTH_TIMEOUT = 2.0   # Timeout pro Request


# ── Registry ──────────────────────────────────────────────────────────────────

class _HubRegistry:
    """Registry keyed by project root — stable across port changes."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_root: dict[str, dict[str, Any]] = {}

    def register(self, port: int, name: str, root: str, scheme: str = "http", external_url: str = "") -> None:
        with self._lock:
            self._by_root[root] = {
                "port": port,
                "name": name,
                "root": root,
                "scheme": scheme,
                "externalUrl": external_url or f"{scheme}://localhost:{port}",
                "status": "online",
            }

    def deregister(self, port: int) -> None:
        with self._lock:
            for root, entry in list(self._by_root.items()):
                if entry["port"] == port:
                    del self._by_root[root]
                    break

    def set_status(self, port: int, status: str) -> None:
        with self._lock:
            for entry in self._by_root.values():
                if entry["port"] == port:
                    entry["status"] = status
                    break

    def all(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._by_root.values())


_registry = _HubRegistry()


# ── Endpoints ─────────────────────────────────────────────────────────────────

class _RegisterRequest(BaseModel):
    port: int
    name: str
    root: str
    scheme: str = "http"
    externalUrl: str = ""


class _DeregisterRequest(BaseModel):
    port: int


@router.post("/hub/register", status_code=201)
async def hub_register(body: _RegisterRequest) -> dict:
    _registry.register(body.port, body.name, body.root, body.scheme, body.externalUrl)
    return {"registered": True}


@router.post("/hub/deregister")
async def hub_deregister(body: _DeregisterRequest) -> dict:
    _registry.deregister(body.port)
    return {"deregistered": True}


@router.get("/hub/projects")
async def hub_projects() -> list[dict]:
    return _registry.all()


@router.get("/hub", response_class=HTMLResponse, include_in_schema=False)
async def hub_dashboard() -> str:
    return _HUB_HTML


# ── Background health-check ───────────────────────────────────────────────────

async def hub_health_loop() -> None:
    """Prüft alle registrierten Projektserver periodisch auf Erreichbarkeit."""
    async with httpx.AsyncClient(timeout=_HEALTH_TIMEOUT, verify=False) as client:
        while True:
            await asyncio.sleep(_HEALTH_INTERVAL)
            for server in _registry.all():
                port = server["port"]
                scheme = server.get("scheme", "http")
                try:
                    r = await client.get(f"{scheme}://localhost:{port}/api/server-info",
                                         follow_redirects=True)
                    _registry.set_status(port, "online" if r.status_code == 200 else "offline")
                except Exception:
                    _registry.set_status(port, "offline")


# ── Dashboard HTML ────────────────────────────────────────────────────────────

_HUB_HTML = """<!doctype html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SDD Hub</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: system-ui, -apple-system, sans-serif;
      background: #0d1117; color: #e6edf3;
      padding: 2rem; min-height: 100vh;
    }
    header {
      display: flex; align-items: center; gap: .75rem;
      margin-bottom: 2rem; padding-bottom: 1rem;
      border-bottom: 1px solid #21262d;
    }
    header h1 { font-size: 1.25rem; font-weight: 600; color: #58a6ff; }
    header .version { font-size: .75rem; color: #8b949e; margin-left: auto; }
    .grid {
      display: grid; gap: 1rem;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    }
    .card {
      background: #161b22; border: 1px solid #30363d;
      border-radius: 10px; padding: 1.25rem;
      display: flex; flex-direction: column; gap: .5rem;
      transition: border-color .15s;
    }
    .card.online  { border-left: 3px solid #3fb950; }
    .card.offline { border-left: 3px solid #f85149; opacity: .65; }
    .card-name { font-weight: 600; font-size: 1rem; }
    .card-root { font-size: .75rem; color: #8b949e; word-break: break-all; }
    .card-footer { display: flex; align-items: center; gap: .6rem; margin-top: .5rem; }
    .badge {
      display: inline-flex; align-items: center; gap: .35rem;
      padding: .2rem .6rem; border-radius: 20px; font-size: .72rem; font-weight: 500;
    }
    .badge.online  { background: #1a3a26; color: #3fb950; }
    .badge.offline { background: #3a1a1a; color: #f85149; }
    .dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
    a.btn {
      margin-left: auto;
      display: inline-block; padding: .35rem .9rem;
      background: #21262d; border: 1px solid #30363d;
      border-radius: 6px; color: #58a6ff;
      text-decoration: none; font-size: .82rem;
      transition: background .12s;
    }
    a.btn:hover { background: #30363d; }
    .empty {
      grid-column: 1 / -1; text-align: center;
      padding: 3rem; color: #8b949e; font-size: .9rem; line-height: 1.8;
    }
    .empty code {
      background: #161b22; border: 1px solid #30363d;
      padding: .15rem .45rem; border-radius: 4px;
      font-family: monospace; font-size: .85em; color: #e6edf3;
    }
  </style>
</head>
<body>
  <header>
    <svg width="20" height="20" viewBox="0 0 16 16" fill="#58a6ff">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38
               0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13
               -.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66
               .07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95
               0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12
               0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27
               1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12
               .51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95
               .29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2
               0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
    </svg>
    <h1>SDD Hub</h1>
    <span class="version" id="refresh-hint">Aktualisiert alle 5 s</span>
  </header>
  <div class="grid" id="grid">
    <div class="empty">Lade…</div>
  </div>
  <script>
    async function load() {
      const res = await fetch('/api/hub/projects').catch(() => null);
      if (!res || !res.ok) return;
      const projects = await res.json();
      const grid = document.getElementById('grid');
      if (!projects.length) {
        grid.innerHTML = `<div class="empty">
          Keine aktiven Projektserver registriert.<br><br>
          Starte einen Projektserver über die VS Code Extension<br>
          oder mit <code>sdd ui --project &lt;pfad&gt;</code>.
        </div>`;
        return;
      }
      grid.innerHTML = projects.map(p => `
        <div class="card ${p.status}">
          <div class="card-name">${p.name}</div>
          <div class="card-root">${p.root}</div>
          <div class="card-footer">
            <span class="badge ${p.status}">
              <span class="dot"></span>
              ${p.status === 'online' ? 'Online' : 'Offline'}
            </span>
            <span style="font-size:.75rem;color:#8b949e">:${p.port}</span>
            ${p.status === 'online'
              ? `<a class="btn" href="${p.scheme || 'http'}://localhost:${p.port}/" target="_blank">UI öffnen ↗</a>`
              : ''}
          </div>
        </div>`).join('');
    }
    load();
    setInterval(load, 5000);
  </script>
</body>
</html>
"""
