"""Startet den SDD Web UI Server (FastAPI + optionaler Vite-Dev-Server)."""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import threading
from pathlib import Path


def _web_root() -> Path:
    # tool/sdd_cli/ui.py → parents[2] = repo root
    return Path(__file__).resolve().parents[2] / "web"


def _api_python(api_dir: Path) -> str:
    """Gibt den Python-Interpreter der web/api-.venv zurück, falls vorhanden."""
    candidate = api_dir / ".venv" / "bin" / "python"
    if candidate.exists():
        return str(candidate)
    return sys.executable


def _stream(proc: subprocess.Popen, prefix: str) -> None:
    assert proc.stdout
    for line in proc.stdout:
        sys.stdout.write(f"[{prefix}] {line}")
        sys.stdout.flush()


def start_server(
    project_root: str,
    port: int = 8000,
    watch: bool = False,
    open_browser: bool = True,
) -> None:
    web = _web_root()
    api_dir = web / "api"
    ui_dir = web / "ui"

    if not api_dir.exists():
        print(f"✗ Web-API-Verzeichnis nicht gefunden: {api_dir}", file=sys.stderr)
        sys.exit(1)

    env = os.environ.copy()
    env["SDD_PROJECT_ROOT"] = str(Path(project_root).resolve())

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
        threading.Thread(target=_stream, args=(api, "api"), daemon=True).start()

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

        api = subprocess.Popen(
            [_api_python(api_dir), "-m", "uvicorn", "main:app",
             "--host", "0.0.0.0", "--port", str(port)],
            cwd=api_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        procs.append(api)
        threading.Thread(target=_stream, args=(api, "api"), daemon=True).start()

        url = f"http://localhost:{port}"
        print(f"▶ Server gestartet → {url}")
        print(f"  Stoppen mit Ctrl+C\n")

    if open_browser:
        import time
        import webbrowser
        time.sleep(1.5)
        webbrowser.open(url)

    for p in procs:
        p.wait()
