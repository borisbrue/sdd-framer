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
    from importlib.resources import files as _pkg_files
    return Path(str(_pkg_files("sdd_cli").joinpath("web")))


def _find_free_port(start: int = 8080, exclude: set[int] | None = None) -> int:
    import socket as _socket
    exclude = exclude or {4711, 8000, 5173}
    port = start
    while True:
        if port not in exclude:
            with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as s:
                s.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
                if s.connect_ex(("127.0.0.1", port)) != 0:
                    return port
        port += 1


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


def _hub_scheme() -> str:
    # Hub läuft immer auf HTTP (zusätzlich HTTPS wenn Certs vorhanden → port+1)
    return "http"


def _hub_urlopen(req: urllib.request.Request) -> None:
    """Öffnet eine Hub-URL; ignoriert TLS-Verifikation für localhost (self-signed)."""
    if req.full_url.startswith("https"):
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        urllib.request.urlopen(req, timeout=2, context=ctx)
    else:
        urllib.request.urlopen(req, timeout=2)


def _hub_register(port: int, name: str, root: str, hub_port: int = 8000,
                  scheme: str = "http", external_url: str = "") -> None:
    """Registriert diesen Projektserver beim Hub (fire-and-forget)."""
    try:
        data = json.dumps({
            "port": port, "name": name, "root": root,
            "scheme": scheme, "externalUrl": external_url,
        }).encode()
        req = urllib.request.Request(
            f"{_hub_scheme()}://localhost:{hub_port}/api/hub/register",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        _hub_urlopen(req)
    except Exception:
        pass


def _hub_deregister(port: int, hub_port: int = 8000) -> None:
    """Meldet diesen Projektserver beim Hub ab."""
    try:
        data = json.dumps({"port": port}).encode()
        req = urllib.request.Request(
            f"{_hub_scheme()}://localhost:{hub_port}/api/hub/deregister",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        _hub_urlopen(req)
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

    global_certs = Path.home() / ".local/share/sdd/certs"
    has_certs = (global_certs / "cert.pem").exists() and (global_certs / "key.pem").exists()
    https_port = port + 1 if has_certs else None

    # CORS: immer beide Schemata für LAN und localhost
    try:
        import socket as _sock
        with _sock.socket(_sock.AF_INET, _sock.SOCK_DGRAM) as _s:
            _s.connect(("8.8.8.8", 80))
            _lan_ip = _s.getsockname()[0]
        if not _lan_ip.startswith("127."):
            _origins = [
                "http://localhost:5173", "http://localhost:5174",
                f"http://localhost:{port}",
                *([f"https://localhost:{https_port}"] if https_port else []),
                *[f"http://{_lan_ip}:{p}" for p in (5173, 5174)],
                *[f"https://{_lan_ip}:{p}" for p in (5173, 5174)],
                f"http://{_lan_ip}:{port}",
                *([f"https://{_lan_ip}:{https_port}"] if https_port else []),
            ]
            env["SDD_ALLOWED_ORIGINS"] = ",".join(dict.fromkeys(_origins))
    except Exception:
        pass

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

    _python = _api_python(api_dir)

    # HTTP immer
    proc = subprocess.Popen(
        [_python, "-m", "uvicorn", "main:app",
         "--host", "0.0.0.0", "--port", str(port)],
        cwd=api_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    procs.append(proc)
    threading.Thread(target=_stream, args=(proc, "hub"), daemon=True).start()

    # HTTPS zusätzlich wenn Certs vorhanden
    if has_certs:
        proc_ssl = subprocess.Popen(
            [_python, "-m", "uvicorn", "main:app",
             "--host", "0.0.0.0", "--port", str(https_port),
             "--ssl-certfile", str(global_certs / "cert.pem"),
             "--ssl-keyfile",  str(global_certs / "key.pem")],
            cwd=api_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        procs.append(proc_ssl)
        threading.Thread(target=_stream, args=(proc_ssl, "hub/s"), daemon=True).start()

    print(f"▶ SDD Hub gestartet → http://localhost:{port}/")
    if has_certs and https_port:
        print(f"  HTTPS (LAN/Smartphone) → https://localhost:{https_port}/")
    print(f"  Projektserver registrieren sich automatisch über die Extension.")
    print(f"  Stoppen mit Ctrl+C\n")

    if open_browser:
        import time
        import webbrowser
        time.sleep(1.5)
        webbrowser.open(f"http://localhost:{port}/")

    for p in procs:
        p.wait()


def start_pwa(port: int = 0, open_browser: bool = True) -> None:
    """Startet die SDD PWA als statischer Server."""
    if port == 0:
        port = _find_free_port(start=8080)
    web = _web_root()
    pwa_dir = web / "pwa"

    if not (pwa_dir / "dist" / "index.html").exists():
        print(f"✗ PWA-Build nicht gefunden: {pwa_dir / 'dist'}", file=sys.stderr)
        print("  Bitte zuerst: cd web/pwa && npm run build", file=sys.stderr)
        sys.exit(1)

    global_certs = Path.home() / ".local/share/sdd/certs"
    has_certs = (global_certs / "cert.pem").exists() and (global_certs / "key.pem").exists()
    https_port = port + 1 if has_certs else None

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

    _python = _api_python(web / "api")

    # HTTP immer
    proc = subprocess.Popen(
        [_python, "-m", "uvicorn", "server:app",
         "--host", "0.0.0.0", "--port", str(port)],
        cwd=pwa_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    procs.append(proc)
    threading.Thread(target=_stream, args=(proc, "pwa"), daemon=True).start()

    # HTTPS zusätzlich wenn Certs vorhanden
    if has_certs:
        proc_ssl = subprocess.Popen(
            [_python, "-m", "uvicorn", "server:app",
             "--host", "0.0.0.0", "--port", str(https_port),
             "--ssl-certfile", str(global_certs / "cert.pem"),
             "--ssl-keyfile",  str(global_certs / "key.pem")],
            cwd=pwa_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        procs.append(proc_ssl)
        threading.Thread(target=_stream, args=(proc_ssl, "pwa/s"), daemon=True).start()

    try:
        import socket as _sock
        with _sock.socket(_sock.AF_INET, _sock.SOCK_DGRAM) as _s:
            _s.connect(("8.8.8.8", 80))
            _lan_ip = _s.getsockname()[0]
    except Exception:
        _lan_ip = None

    print(f"▶ SDD PWA gestartet → http://localhost:{port}/")
    if has_certs and https_port:
        if _lan_ip and not _lan_ip.startswith("127."):
            print(f"  HTTPS (LAN/Smartphone) → https://{_lan_ip}:{https_port}/")
        else:
            print(f"  HTTPS → https://localhost:{https_port}/")
    elif _lan_ip and not _lan_ip.startswith("127."):
        print(f"  Im LAN: http://{_lan_ip}:{port}/")
    print(f"  Stoppen mit Ctrl+C\n")

    if open_browser:
        import time
        import webbrowser
        time.sleep(1.5)
        webbrowser.open(f"http://localhost:{port}/")

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

    # CORS: immer beide Schemata für LAN und localhost erlauben
    _lan_ip = ""
    try:
        import socket as _sock
        with _sock.socket(_sock.AF_INET, _sock.SOCK_DGRAM) as _s:
            _s.connect(("8.8.8.8", 80))
            _lan_ip = _s.getsockname()[0]
        if not _lan_ip.startswith("127."):
            _origins = [
                f"http://localhost:5173", f"http://localhost:8000",
                f"http://localhost:{port}", f"https://localhost:{port + 1}",
                # PWA-Dev (Vite) und PWA-Server (sdd pwa start) – beide Varianten erlauben
                *[f"http://{_lan_ip}:{p}" for p in (5173, 5174, 8080, 8081, 8082, 8083)],
                *[f"https://{_lan_ip}:{p}" for p in (5173, 5174, 8080, 8081, 8082, 8083)],
                f"http://{_lan_ip}:{port}",
                f"https://{_lan_ip}:{port + 1}",
            ]
            env["SDD_ALLOWED_ORIGINS"] = ",".join(dict.fromkeys(_origins))
    except Exception:
        pass

    # Hub-URL für QR-Code (gleiche LAN-IP, fixer Hub-Port) – Hub immer HTTP
    if _lan_ip and not _lan_ip.startswith("127."):
        env["SDD_HUB_URL"] = f"http://{_lan_ip}:{hub_port}"

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
        _ext = f"http://localhost:{port}"
        on_ready = lambda: _hub_register(port, project_name, root_resolved, hub_port, "http", _ext)
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

        cert_dir = Path(root_resolved) / ".certs"
        has_certs = (cert_dir / "cert.pem").exists() and (cert_dir / "key.pem").exists()
        https_port = port + 1 if has_certs else None

        _ext_url = (
            f"https://{_lan_ip}:{https_port}" if _lan_ip and not _lan_ip.startswith("127.") and has_certs
            else f"http://{_lan_ip}:{port}" if _lan_ip and not _lan_ip.startswith("127.")
            else f"http://localhost:{port}"
        )

        _python = _api_python(api_dir)
        api = subprocess.Popen(
            [_python, "-m", "uvicorn", "main:app",
             "--host", "0.0.0.0", "--port", str(port)],
            cwd=api_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        procs.append(api)
        on_ready = lambda: _hub_register(port, project_name, root_resolved, hub_port, "http", _ext_url)
        threading.Thread(target=_stream, args=(api, "api", on_ready), daemon=True).start()

        if has_certs:
            api_ssl = subprocess.Popen(
                [_python, "-m", "uvicorn", "main:app",
                 "--host", "0.0.0.0", "--port", str(https_port),
                 "--ssl-certfile", str(cert_dir / "cert.pem"),
                 "--ssl-keyfile",  str(cert_dir / "key.pem")],
                cwd=api_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
            )
            procs.append(api_ssl)
            threading.Thread(target=_stream, args=(api_ssl, "api/s"), daemon=True).start()

        url = f"http://localhost:{port}"
        print(f"▶ Server gestartet → {url}")
        if has_certs and https_port:
            if _lan_ip and not _lan_ip.startswith("127."):
                print(f"  HTTPS (LAN/Smartphone) → https://{_lan_ip}:{https_port}")
            else:
                print(f"  HTTPS → https://localhost:{https_port}")
        print(f"  Stoppen mit Ctrl+C\n")

    if open_browser:
        import time
        import webbrowser
        time.sleep(1.5)
        webbrowser.open(url)

    for p in procs:
        p.wait()
