"""Eval-Container-Lifecycle für Holdout-Evaluation.

Startet einen kurzlebigen Container mit dem Projektcode,
wartet auf den Health-Endpoint und stellt ihn für den Runner bereit.
Nach den Tests wird der Container gestoppt und entfernt.

Context-Manager-Nutzung:
    with EvalContainer(cfg) as (base_url, container_name):
        run_structured_evaluation(cfg, base_url, container_name=container_name)
"""
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class EvalContainerConfig:
    runtime: str           # "docker" | "podman"
    image: str             # z.B. "sdd-dev:latest"
    dockerfile: str        # z.B. ".sdd/Dockerfile"
    start_command: list[str]  # Befehl zum Starten der App im Container
    app_port: int          # Port der App im Container (z.B. 8080)
    host_port: int         # Freigegebener Port auf dem Host
    host: str              # Adresse, unter der der Port erreichbar ist
    health_path: str       # Pfad für Health-Check (z.B. "/health")
    health_timeout: int    # Sekunden bis Timeout (z.B. 30)
    env: dict[str, str]    # Zusätzliche Env-Vars für den Container
    workspace: str         # Workspace-Pfad im Container


def load_eval_container_config(cfg: Any) -> EvalContainerConfig:
    """Lädt die Eval-Container-Konfiguration aus config.yaml."""
    from .dev_container import resolve_runtime as _resolve_runtime

    raw = cfg.raw
    docker = raw.get("docker", {})
    evaluator = raw.get("evaluator", {})
    container_cfg = evaluator.get("container", {})

    return EvalContainerConfig(
        runtime=_resolve_runtime(raw),
        image=docker.get("image", "sdd-dev:latest"),
        dockerfile=docker.get("dockerfile", ".sdd/Dockerfile"),
        start_command=container_cfg.get("start_command", ["tail", "-f", "/dev/null"]),
        app_port=container_cfg.get("app_port", 8080),
        host_port=container_cfg.get("host_port", 18080),
        # 127.0.0.1 statt "localhost": der Port wird per -p auf IPv4
        # veroeffentlicht. Wo localhost nur nach ::1 aufloest (rootless Podman
        # mit netavark ist ein Fall davon), war der Health-Check unerreichbar.
        host=container_cfg.get("host", "127.0.0.1"),
        health_path=container_cfg.get("health_path", "/health"),
        health_timeout=container_cfg.get("health_timeout_secs", 30),
        env=container_cfg.get("env", {}),
        workspace=container_cfg.get("workspace", "/workspace"),
    )


_EVAL_CONTAINER_NAME = "sdd-eval-runner"


class EvalContainer:
    """Context-Manager: Container starten → Health-Check → Tests → stoppen."""

    def __init__(self, cfg: Any, *, build: bool = False) -> None:
        self.cfg = cfg
        self.build = build
        self._ecfg = load_eval_container_config(cfg)
        self._started = False

    def __enter__(self) -> tuple[str, str]:
        self._start()
        base_url = f"http://{self._ecfg.host}:{self._ecfg.host_port}"
        return base_url, _EVAL_CONTAINER_NAME

    def __exit__(self, *_: Any) -> None:
        self._stop()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _run(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            [self._ecfg.runtime] + args,
            capture_output=True,
            text=True,
            check=check,
        )

    def image_exists(self) -> bool:
        r = self._run(["image", "inspect", self._ecfg.image], check=False)
        return r.returncode == 0

    def _build_image(self) -> None:
        print(f"  ▶ Baue Image '{self._ecfg.image}' …", flush=True)
        subprocess.run(
            [self._ecfg.runtime, "build",
             "-t", self._ecfg.image,
             "-f", self._ecfg.dockerfile,
             "."],
            check=True,
        )
        print(f"  ✓ Image gebaut: {self._ecfg.image}", flush=True)

    def _stop_existing(self) -> None:
        self._run(["stop", _EVAL_CONTAINER_NAME], check=False)
        self._run(["rm", "-f", _EVAL_CONTAINER_NAME], check=False)

    def _start(self) -> None:
        ecfg = self._ecfg
        import os

        if self.build or not self.image_exists():
            self._build_image()

        self._stop_existing()

        env_args: list[str] = []
        for k, v in ecfg.env.items():
            env_args += ["-e", f"{k}={v}"]

        # LLM-Keys vom Host durchreichen (für CLI-Holdouts die LLM brauchen)
        for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
            if (v := os.environ.get(k)):
                env_args += ["-e", f"{k}={v}"]

        workspace_volume = f"{os.getcwd()}:{ecfg.workspace}"
        port_mapping = f"{ecfg.host_port}:{ecfg.app_port}"

        cmd = (
            [ecfg.runtime, "run", "-d",
             "--name", _EVAL_CONTAINER_NAME,
             "-v", workspace_volume,
             "-p", port_mapping]
            + env_args
            + [ecfg.image]
            + ecfg.start_command
        )

        print(f"  ▶ Starte Eval-Container auf Port {ecfg.host_port} …", flush=True)
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(
                f"Container-Start fehlgeschlagen:\n{r.stderr.strip()}"
            )
        self._started = True

        self._wait_healthy()

    def _health_urls(self) -> list[str]:
        """Zu pruefende Health-URLs, konfigurierter Host zuerst.

        Beide Adressfamilien werden probiert: eine feste Wahl schlaegt fehl,
        sobald der Host die andere bedient. Auf Systemen, auf denen beide
        funktionieren, aendert sich nichts — die erste Antwort gewinnt.
        """
        ecfg = self._ecfg
        hosts = [ecfg.host]
        for fallback in ("127.0.0.1", "[::1]"):
            if fallback not in hosts:
                hosts.append(fallback)
        return [f"http://{h}:{ecfg.host_port}{ecfg.health_path}" for h in hosts]

    def _wait_healthy(self) -> None:
        import urllib.request

        ecfg = self._ecfg
        urls = self._health_urls()
        deadline = time.monotonic() + ecfg.health_timeout

        print(f"  ▶ Warte auf Health-Check: {' oder '.join(urls)}", flush=True)
        while time.monotonic() < deadline:
            for url in urls:
                try:
                    with urllib.request.urlopen(url, timeout=2) as resp:
                        if resp.status == 200:
                            print(f"  ✓ Container ist bereit ({url}).", flush=True)
                            return
                except Exception:
                    continue
            time.sleep(1)

        # Logs holen, bevor der Container weg ist. Vorher stand self._stop()
        # davor, und der f-String wurde erst danach ausgewertet — die
        # Fehlermeldung enthielt deshalb zuverlaessig "no such container"
        # statt der Diagnose, fuer die sie gedacht war.
        logs = self._fetch_logs()
        self._stop()
        raise RuntimeError(
            f"Container hat Health-Check nicht bestanden innerhalb {ecfg.health_timeout}s "
            f"({', '.join(urls)}). Logs:\n{logs}"
        )

    def _stop(self) -> None:
        if self._started:
            print("  ▶ Stoppe Eval-Container …", flush=True)
            self._stop_existing()
            self._started = False

    def _fetch_logs(self, lines: int = 30) -> str:
        r = self._run(["logs", "--tail", str(lines), _EVAL_CONTAINER_NAME], check=False)
        return r.stdout + r.stderr
