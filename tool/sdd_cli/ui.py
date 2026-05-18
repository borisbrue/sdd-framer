"""Startet den SDD Web UI Server (FastAPI + optionaler Vite-Dev-Server)."""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path
from typing import Callable


def _web_root() -> Path:
    # tool/sdd_cli/ui.py → parents[2] = repo root
    return Path(__file__).resolve().parents[2] / "web"


def _api_python(api_dir: Path) -> str:
    """Findet einen Python-Interpreter mit uvicorn."""
    # 1. web/api/.venv (falls vorhanden)
    venv_py = api_dir / ".venv" / "bin" / "python"
    if venv_py.exists():
        return str(venv_py)

    # 2. sys.executable testen
    import subprocess as _sp
    try:
        _sp.run([sys.executable, "-c", "import uvicorn"], check=True,
                capture_output=True, timeout=5)
        return sys.executable
    except Exception:
        pass

    # 3. Bekannte uv-Tool-Pfade (Flatpak-Sandbox und Host)
    _candidates = [
        Path("/var/data/uv/tools/sdd-framer/bin/python3"),
        Path.home() / ".var/app/com.visualstudio.code/data/uv/tools/sdd-framer/bin/python3",
        Path.home() / ".local/share/uv/tools/sdd-framer/bin/python3",
    ]
    for p in _candidates:
        if p.exists():
            return str(p)

    return sys.executable


def _stream(proc: subprocess.Popen, prefix: str, on_ready: Callable | None = None) -> None:
    assert proc.stdout
    for line in proc.stdout:
        sys.stdout.write(f"[{prefix}] {line}")
        sys.stdout.flush()
        if on_ready and "Application startup complete" in line:
            on_ready()
            on_ready = None


def _hub_register(port: int, name: str, root: str, hub_port: int = 8000, scheme: str = "http") -> None:
    """Registriert diesen Projektserver beim Hub (fire-and-forget)."""
    try:
        data = json.dumps({"port": port, "name": name, "root": root, "scheme": scheme}).encode()
        req = urllib.request.Request(
            f"http://localhost:{hub_port}/api/hub/register",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass


def _hub_deregister(port: int, hub_port: int = 8000) -> None:
    """Meldet diesen Projektserver beim Hub ab."""
    try:
        data = json.dumps({"port": port}).encode()
        req = urllib.request.Request(
            f"http://localhost:{hub_port}/api/hub/deregister",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass


def start_hub(port: int = 8000, open_browser: bool = True) -> None:
    """Startet den SDD Hub (Multi-Projekt-Dashboard) auf dem angegebenen Port."""
    web = _web_root()
    api_dir = web / "api"

    if not api_dir.exists():
        print(f"✗ Web-API-Verzeichnis nicht gefunden: {api_dir}", file=sys.stderr)
        sys.exit(1)

    env = os.environ.copy()
    env.pop("SDD_PROJECT_ROOT", None)   # Hub läuft ohne Projektkontext
    env["SDD_HUB_MODE"] = "1"

    procs: list[subprocess.Popen] = []

    def stop_all(signum=None, frame=None) -> None:
        for p in procs:
            try:
                p.terminate()
            except ProcessLookupError:
                pass
        sys.exit(0)

    signal.signal(signal.SIGINT, stop_all)
    signal.signal(signal.SIGTERM, stop_all)

    proc = subprocess.Popen(
        [_api_python(api_dir), "-m", "uvicorn", "main:app",
         "--host", "0.0.0.0", "--port", str(port)],
        cwd=api_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    procs.append(proc)
    threading.Thread(target=_stream, args=(proc, "hub"), daemon=True).start()

    url = f"http://localhost:{port}/"
    print(f"▶ SDD Hub gestartet → {url}")
    print(f"  Projektserver registrieren sich automatisch über die Extension.")
    print(f"  Stoppen mit Ctrl+C\n")

    if open_browser:
        import time
        import webbrowser
        time.sleep(1.5)
        webbrowser.open(url)

    for p in procs:
        p.wait()


def start_server(
    project_root: str,
    port: int = 8000,
    watch: bool = False,
    open_browser: bool = True,
    hub_port: int = 8000,
    external_url: str = "",
) -> None:
    web = _web_root()
    api_dir = web / "api"
    ui_dir = web / "ui"

    if not api_dir.exists():
        print(f"✗ Web-API-Verzeichnis nicht gefunden: {api_dir}", file=sys.stderr)
        sys.exit(1)

    root_resolved = str(Path(project_root).resolve())
    project_name = Path(project_root).resolve().name

    if port == 0:
        import socket as _socket
        with _socket.socket() as _s:
            _s.bind(("", 0))
            port = _s.getsockname()[1]

    env = os.environ.copy()
    env["SDD_PROJECT_ROOT"] = root_resolved
    env["SDD_PORT"] = str(port)
    if external_url:
        env["SDD_EXTERNAL_URL"] = external_url

    # CORS: LAN-IP-Origins für PWA-Dev (Ports 5173/5174) automatisch erlauben
    cert_dir = Path(__file__).resolve().parents[2] / ".certs"
    scheme = "https" if (cert_dir / "cert.pem").exists() else "http"
    try:
        import socket as _sock
        with _sock.socket(_sock.AF_INET, _sock.SOCK_DGRAM) as _s:
            _s.connect(("8.8.8.8", 80))
            _lan_ip = _s.getsockname()[0]
        if not _lan_ip.startswith("127."):
            _origins = [
                f"http://localhost:5173", f"http://localhost:8000",
                f"http://localhost:{port}", f"{scheme}://localhost:{port}",
                *[f"{scheme}://{_lan_ip}:{p}" for p in (5173, 5174, port)],
            ]
            env["SDD_ALLOWED_ORIGINS"] = ",".join(dict.fromkeys(_origins))
    except Exception:
        pass

    procs: list[subprocess.Popen] = []

    def stop_all(signum=None, frame=None) -> None:
        _hub_deregister(port, hub_port)
        for p in procs:
            try:
                p.terminate()
            except ProcessLookupError:
                pass
        sys.exit(0)

    signal.signal(signal.SIGINT, stop_all)
    signal.signal(signal.SIGTERM, stop_all)

    if watch:
        if not shutil.which("npm"):
            print("✗ npm nicht gefunden. Bitte Node.js installieren.", file=sys.stderr)
            sys.exit(1)

        vite = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=ui_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        procs.append(vite)
        threading.Thread(target=_stream, args=(vite, "ui "), daemon=True).start()

        api = subprocess.Popen(
            [_api_python(api_dir), "-m", "uvicorn", "main:app",
             "--reload", "--host", "0.0.0.0", "--port", "8000"],
            cwd=api_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        procs.append(api)
        on_ready = lambda: _hub_register(port, project_name, root_resolved, hub_port)
        threading.Thread(target=_stream, args=(api, "api", on_ready), daemon=True).start()

        url = "http://localhost:5173"
        print(f"▶ Watch-Modus gestartet")
        print(f"  Frontend (HMR) → {url}")
        print(f"  API-Backend    → http://localhost:8000")
        print(f"  Stoppen mit Ctrl+C\n")
    else:
        dist = ui_dir / "dist"
        if not dist.exists():
            print("⚠ web/ui/dist/ nicht gefunden – Frontend noch nicht gebaut.")
            print("  Führe zuerst aus:  cd web/ui && npm run build")
            print("  Oder starte mit:   sdd ui --watch")
            sys.exit(1)

        cert_dir = Path(__file__).resolve().parents[2] / ".certs"
        ssl_args = []
        scheme = "http"
        if (cert_dir / "cert.pem").exists() and (cert_dir / "key.pem").exists():
            ssl_args = [
                "--ssl-certfile", str(cert_dir / "cert.pem"),
                "--ssl-keyfile",  str(cert_dir / "key.pem"),
            ]
            scheme = "https"

        api = subprocess.Popen(
            [_api_python(api_dir), "-m", "uvicorn", "main:app",
             "--host", "0.0.0.0", "--port", str(port)] + ssl_args,
            cwd=api_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        procs.append(api)
        on_ready = lambda: _hub_register(port, project_name, root_resolved, hub_port, scheme)
        threading.Thread(target=_stream, args=(api, "api", on_ready), daemon=True).start()

        url = f"{scheme}://localhost:{port}"
        print(f"▶ Server gestartet → {url}")
        print(f"  Stoppen mit Ctrl+C\n")

    if open_browser:
        import time
        import webbrowser
        time.sleep(1.5)
        webbrowser.open(url)

    for p in procs:
        p.wait()
