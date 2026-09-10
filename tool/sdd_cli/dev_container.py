"""sdd dev – Isolierte Docker-Entwicklungsumgebung pro Spec (SPEC-0021/0022).

Facade Pattern: DevContainerManager kapselt docker/git-Befehle.
Strategy Pattern:
  - PRStrategy: austauschbar (local → github via GhFallbackPRStrategy)
  - ContainerRuntime: docker | podman, Runtime-Auswahl über config.yaml
Observer Pattern: LogStreamer → LogEventBus → WebSocket-Clients (SPEC-0022)
"""
from __future__ import annotations

import abc
import datetime
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from .config import SddConfig

if TYPE_CHECKING:
    from .log_streamer import LogStreamer


# ── Naming conventions ────────────────────────────────────────────────────────

# Pfad des venv im Container. Muss ausserhalb des bind-gemounteten Workspace
# liegen, sonst schreibt uv in das Verzeichnis des Hosts.
CONTAINER_VENV = "/opt/sdd-venv"


def venv_guard_args(workspace: str = "/workspace") -> list[str]:
    """Schuetzt das Host-venv vor dem Container.

    {root}:/workspace ist ein Bind-Mount. Legt im Container irgendein Befehl ein
    venv an — `uv run` tut das ungefragt —, landet es unter /workspace/.venv und
    damit im Arbeitsverzeichnis des Hosts. Danach zeigt .venv/bin/python auf ein
    Python, das es nur im Container gibt; auf dem Host laeuft nichts mehr.

    Zwei Massnahmen, weil eine allein nicht reicht:

    - UV_PROJECT_ENVIRONMENT lenkt uv aus dem Mount heraus. Greift nicht bei
      `python -m venv .venv`.
    - Ein anonymes Volume auf {workspace}/.venv ueberdeckt den Bind-Mount an
      genau dieser Stelle. Was dort entsteht, bleibt im Container.
    """
    return ["-v", f"{workspace}/.venv", "-e", f"UV_PROJECT_ENVIRONMENT={CONTAINER_VENV}"]


def container_name(spec_id: str) -> str:
    return f"sdd-dev-{spec_id.lower().replace('_', '-')}"


def branch_name(spec_id: str, *, prefix: str = "dev") -> str:
    """Bildet den Branchnamen. Einzige Stelle, an der das Schema entsteht.

    Es gibt zwei Konventionen: `dev/` fuer den Entwicklungscontainer (SPEC-0021)
    und `feat/` fuer finalize. Vorher berechneten finalize.py und dieses Modul den
    Namen unabhaengig voneinander — und liefen auseinander: committet wurde auf
    feat/, der PR entstand von dev/, ohne die Arbeit zu enthalten.
    """
    return f"{prefix}/{spec_id}"


# ── LLM env-var forwarding ───────────────────────────────────────────────────

_LLM_ENV_VARS = [
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "SDD_EVAL_BASE_URL",
    "SDD_LLM_BASE_URL",
]


def _llm_env_vars() -> dict[str, str]:
    """Sammelt LLM-API-Keys vom Host und gibt sie als Env-Dict zurück."""
    import os
    return {k: v for k in _LLM_ENV_VARS if (v := os.environ.get(k))}


# ── Shell helpers ─────────────────────────────────────────────────────────────

def _run(args: list[str], *, capture: bool = False, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        capture_output=capture,
        text=True,
        check=check,
    )


def _git(args: list[str], *, capture: bool = False, check: bool = True) -> subprocess.CompletedProcess:
    return _run(["git"] + args, capture=capture, check=check)


# ── ContainerRuntime (Strategy Pattern) ──────────────────────────────────────

class ContainerRuntime(abc.ABC):
    @abc.abstractmethod
    def cli(self) -> str:
        """Returns the CLI executable name: 'docker' or 'podman'."""

    def _cmd(self, args: list[str], *, capture: bool = False, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            [self.cli()] + args,
            capture_output=capture,
            text=True,
            check=check,
        )

    def inspect_status(self, name: str) -> str | None:
        result = self._cmd(
            ["inspect", "--format", "{{.State.Status}}", name],
            capture=True, check=False,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip() or None

    def build(self, image: str, dockerfile: str) -> None:
        self._cmd(["build", "-t", image, "-f", dockerfile, "."])

    def push(self, target: str) -> None:
        self._cmd(["push", target])

    def compose_up(self, compose_file: str, *, build: bool = True) -> None:
        args = ["compose", "-f", compose_file, "up", "-d"]
        if build:
            args.append("--build")
        self._cmd(args)

    def compose_down(self, compose_file: str) -> None:
        self._cmd(["compose", "-f", compose_file, "down"])

    def start(self, name: str) -> None:
        self._cmd(["start", name])

    def stop(self, name: str, *, check: bool = False) -> None:
        self._cmd(["stop", name], check=check)

    def rm(self, name: str, *, check: bool = False) -> None:
        self._cmd(["rm", name], check=check)

    def run_container(
        self,
        name: str,
        image: str,
        *,
        volume: str,
        env: dict[str, str],
    ) -> None:
        args = ["run", "-d", "--name", name, "-v", volume]
        args += venv_guard_args(volume.split(":", 1)[-1])
        for k, v in env.items():
            args += ["-e", f"{k}={v}"]
        args += [image, "tail", "-f", "/dev/null"]
        self._cmd(args)

    def exec_in(self, name: str, cmd: list[str]) -> subprocess.CompletedProcess:
        return self._cmd(["exec", name] + cmd, capture=False, check=False)

    def logs_popen(self, name: str) -> subprocess.Popen:
        return subprocess.Popen(
            [self.cli(), "logs", "--follow", name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )


class DockerRuntime(ContainerRuntime):
    def cli(self) -> str:
        return "docker"


class PodmanRuntime(ContainerRuntime):
    def cli(self) -> str:
        return "podman"

    def run_container(
        self,
        name: str,
        image: str,
        *,
        volume: str,
        env: dict[str, str],
    ) -> None:
        args = ["run", "-d", "--name", name, "-v", volume]
        args += venv_guard_args(volume.split(":", 1)[-1])
        for k, v in env.items():
            args += ["-e", f"{k}={v}"]
        args += [image, "tail", "-f", "/dev/null"]
        self._cmd(args)


_RUNTIME_MAP: dict[str, type[ContainerRuntime]] = {
    "docker": DockerRuntime,
    "podman": PodmanRuntime,
}


def detect_runtime() -> str:
    """Ermittelt die installierte Container-Runtime.

    docker hat Vorrang, weil es der bisherige Default war — auf Systemen, auf
    denen beides liegt, aendert sich damit nichts. Ist keine von beiden im PATH,
    bleibt es bei "docker": der Fehler gehoert dann in den Aufruf, nicht in die
    Erkennung.
    """
    for name in ("docker", "podman"):
        if shutil.which(name):
            return name
    return "docker"


def resolve_runtime(cfg_raw: dict) -> str:
    """Runtime-Name aus der Konfiguration, sonst erkannt.

    Ein explizit gesetztes docker.runtime sticht die Erkennung immer. Ohne
    Angabe wurde bisher fest "docker" angenommen — eine Behauptung ueber die
    Umgebung, die sich pruefen laesst.
    """
    configured = (cfg_raw.get("docker") or {}).get("runtime")
    return str(configured).strip() if configured else detect_runtime()


def get_runtime(cfg: SddConfig) -> ContainerRuntime:
    runtime_name = resolve_runtime(cfg.raw)
    cls = _RUNTIME_MAP.get(runtime_name)
    if cls is None:
        print(
            f"✗ Ungültige Runtime '{runtime_name}'. Erlaubt: docker, podman",
            file=sys.stderr,
        )
        sys.exit(1)
    return cls()


def validate_docker_config(docker_cfg: dict) -> None:
    runtime = docker_cfg.get("runtime", "docker")
    if runtime not in _RUNTIME_MAP:
        raise ValueError(f"Ungültige Runtime '{runtime}'. Erlaubt: docker, podman")

    log_stream = docker_cfg.get("log_stream", {})
    max_lines = log_stream.get("max_lines", 500)
    if not (1 <= max_lines <= 10000):
        raise ValueError(f"log_stream.max_lines muss zwischen 1 und 10000 liegen, ist: {max_lines}")


# ── Git helpers ───────────────────────────────────────────────────────────────

def resolve_base_branch(cfg_raw: dict) -> str | None:
    """Abzweigpunkt fuer den Entwicklungsbranch.

    None bedeutet: vom aktuellen HEAD. Vorher stand hier fest `main`. Bei einer
    Kette aufeinander aufbauender Specs entstand der Entwicklungszweig damit
    ohne die Arbeit der noch nicht gemergten Vorgaenger-Spec.

    Der feste Wert hatte eine zweite Folge: `sdd start` schreibt vorher den
    Spec-Status und das audit.log. Wer nicht auf main stand, bekam beim Wechsel
    auf mains Baum

        Bitte committen oder stashen Sie Ihre Änderungen, bevor Sie Branches
        wechseln.

    — an Aenderungen, die `sdd start` selbst erzeugt hatte. Von HEAD abzuzweigen
    nimmt sie mit, statt sie zu gefaehrden.

    docker.base_branch setzt den alten Wert wieder, wo er richtig ist.
    """
    wert = (cfg_raw.get("docker") or {}).get("base_branch")
    return str(wert).strip() if wert else None


def _branch_exists(branch: str) -> bool:
    result = _git(["rev-parse", "--verify", branch], capture=True, check=False)
    return result.returncode == 0


# ── PR Strategy (Strategy Pattern) ───────────────────────────────────────────

class PRStrategy(abc.ABC):
    @abc.abstractmethod
    def create(self, spec_id: str, cfg: SddConfig, branch: str | None = None) -> None:
        """branch=None faellt auf branch_name(spec_id) zurueck (dev/-Schema).

        Aufrufer, die auf einem anderen Branch arbeiten, muessen ihn uebergeben —
        sonst leitet die Strategie einen eigenen ab und der PR zeigt woandershin.
        """
        ...


class GhFallbackPRStrategy(PRStrategy):
    """gh pr create wenn verfügbar, sonst LocalGitStrategy als Fallback."""

    def __init__(self, title: str = "", body: str = "") -> None:
        self._title = title
        self._body = body

    def create(self, spec_id: str, cfg: SddConfig, branch: str | None = None) -> str | None:
        branch = branch or branch_name(spec_id)
        title = self._title or f"feat({spec_id}): Implementierung via sdd finalize"
        body = self._body or (
            f"Automatisch generiert von `sdd finalize {spec_id}`.\n\n"
            f"Branch: `{branch}`"
        )
        try:
            result = subprocess.run(
                ["gh", "pr", "create",
                 "--title", title,
                 "--body", body,
                 "--head", branch,
                 "--base", "main"],
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            print("[WARN] 'gh' nicht gefunden – PR wird als lokale Datei abgelegt.",
                  file=sys.stderr)
            LocalGitStrategy().create(spec_id, cfg, branch)
            return None
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line.startswith("https://"):
                    return line.strip()
            return result.stdout.strip() or None
        # Grund sichtbar machen, statt still auf die lokale Datei auszuweichen.
        # Haeufigster Fall: der Branch liegt noch nicht auf dem Remote.
        reason = (result.stderr or result.stdout).strip().splitlines()
        print(f"[WARN] 'gh pr create' fehlgeschlagen (Branch {branch}) – "
              f"PR wird als lokale Datei abgelegt.", file=sys.stderr)
        for line in reason[:5]:
            print(f"       {line}", file=sys.stderr)
        LocalGitStrategy().create(spec_id, cfg, branch)
        return None


class LocalGitStrategy(PRStrategy):
    def create(self, spec_id: str, cfg: SddConfig, branch: str | None = None) -> None:
        branch = branch or branch_name(spec_id)

        result = _git(["diff", f"main..{branch}", "--stat"], capture=True, check=False)
        diff_stat = result.stdout.strip() if result.returncode == 0 else "(diff nicht verfügbar)"

        test_result, tests_passed, tests_total = _load_last_test_result(cfg, spec_id)
        merge_cmd = f"git checkout main && git merge {branch}"

        pr_dir = cfg.root / ".sdd" / "prs"
        pr_dir.mkdir(parents=True, exist_ok=True)
        pr_path = pr_dir / f"PR-{spec_id}.md"

        today = datetime.date.today().isoformat()
        pr_path.write_text(
            f"---\n"
            f"spec_id: {spec_id}\n"
            f"branch: {branch}\n"
            f"created: {today}\n"
            f"test_result: {test_result}\n"
            f"tests_passed: {tests_passed}\n"
            f"tests_total: {tests_total}\n"
            f'merge_command: "{merge_cmd}"\n'
            f"diff_stat: |\n  {diff_stat}\n"
            f"pr_strategy: local\n"
            f"---\n\n"
            f"# PR: {spec_id}\n\n"
            f"## Diff\n\n```\n{diff_stat}\n```\n\n"
            f"## Merge\n\n```bash\n{merge_cmd}\n```\n",
            encoding="utf-8",
        )
        print(f"✓ PR-Dokument erstellt: {pr_path}")
        print(f"\nMerge-Anleitung:\n  {merge_cmd}")


# ── Test-result persistence ───────────────────────────────────────────────────

def _test_result_path(cfg: SddConfig, spec_id: str) -> Path:
    return cfg.root / ".sdd" / "test-results" / f"{spec_id}.json"


def save_test_result(cfg: SddConfig, spec_id: str, *, passed: int, total: int) -> None:
    import json
    p = _test_result_path(cfg, spec_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    result = "passed" if passed == total and total > 0 else "failed"
    p.write_text(
        json.dumps({"spec_id": spec_id, "result": result, "passed": passed, "total": total}),
        encoding="utf-8",
    )


def _load_last_test_result(cfg: SddConfig, spec_id: str) -> tuple[str, int, int]:
    import json
    p = _test_result_path(cfg, spec_id)
    if not p.exists():
        return "skipped", 0, 0
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data.get("result", "skipped"), data.get("passed", 0), data.get("total", 0)
    except Exception:
        return "skipped", 0, 0


# ── DevContainerManager (Facade) ─────────────────────────────────────────────

class DevContainerManager:
    def __init__(
        self,
        cfg: SddConfig,
        pr_strategy: PRStrategy | None = None,
        runtime: ContainerRuntime | None = None,
        log_streamer: LogStreamer | None = None,
    ) -> None:
        self.cfg = cfg
        self._pr_strategy = pr_strategy or LocalGitStrategy()
        self._runtime = runtime or get_runtime(cfg)
        self._log_streamer = log_streamer

    def _docker_cfg(self) -> dict:
        return self.cfg.raw.get("docker", {})

    def _docker_image(self) -> str:
        return self._docker_cfg().get("image", "sdd-dev:latest")

    def _dockerfile(self) -> str:
        return self._docker_cfg().get("dockerfile", ".sdd/Dockerfile")

    def _compose_file(self) -> str:
        return self._docker_cfg().get("compose_file", "")

    def _registry_url(self) -> str:
        return self._docker_cfg().get("registry", {}).get("url", "")

    def _log_stream_enabled(self) -> bool:
        return self._docker_cfg().get("log_stream", {}).get("enabled", True)

    def image_exists(self) -> bool:
        result = subprocess.run(
            [self._runtime.cli(), "image", "inspect", self._docker_image()],
            capture_output=True,
        )
        return result.returncode == 0

    def runtime_available(self) -> bool:
        """False statt Absturz, wenn die Runtime fehlt.

        subprocess.run wirft FileNotFoundError, wenn das Binary nicht existiert —
        die Funktion konnte deshalb nie False liefern, sie brach ab.
        """
        try:
            result = subprocess.run([self._runtime.cli(), "info"], capture_output=True)
        except (FileNotFoundError, OSError):
            return False
        return result.returncode == 0

    def missing_runtime_hint(self) -> str:
        """Nennt eine installierte Alternative, falls es eine gibt."""
        konfiguriert = self._runtime.cli()
        vorhanden = [n for n in ("docker", "podman")
                     if n != konfiguriert and shutil.which(n)]
        if vorhanden:
            return (f"'{konfiguriert}' ist nicht verfügbar, '{vorhanden[0]}' schon — "
                    f"trage das unter docker.runtime in .sdd/config.yaml ein.")
        return "Weder docker noch podman ist verfügbar."

    # ── SPEC-0022 commands ────────────────────────────────────────────────────

    def build(self) -> None:
        dockerfile = self._dockerfile()
        if not Path(dockerfile).exists():
            print(f"✗ Dockerfile nicht gefunden: {dockerfile}", file=sys.stderr)
            sys.exit(1)
        image = self._docker_image()
        self._runtime.build(image, dockerfile)
        print(f"✓ Image gebaut: {image}")

    def push(self) -> None:
        registry_url = self._registry_url()
        if not registry_url:
            print("✗ Keine Registry konfiguriert (docker.registry.url)", file=sys.stderr)
            sys.exit(1)
        image = self._docker_image()
        target = f"{registry_url}/{image}"
        self._runtime.push(target)
        print(f"✓ Image gepusht: {target}")

    def up(self, spec_id: str, *, build: bool = True) -> None:
        compose_file = self._compose_file()
        if not compose_file:
            print(
                "✗ Kein compose_file konfiguriert (docker.compose_file). "
                "Container werden von sdd start und sdd finalize verwaltet.",
                file=sys.stderr,
            )
            sys.exit(1)
        self._runtime.compose_up(compose_file, build=build)
        print(f"✓ Compose-Stack gestartet für {spec_id}")
        if self._log_stream_enabled() and self._log_streamer is not None:
            cname = container_name(spec_id)
            self._log_streamer.attach(spec_id, cname)
            print(f"✓ LogStreamer aktiv für {spec_id}")

    def down(self, spec_id: str) -> None:
        compose_file = self._compose_file()
        if not compose_file:
            print(
                "✗ Kein compose_file konfiguriert (docker.compose_file).",
                file=sys.stderr,
            )
            sys.exit(1)
        self._runtime.compose_down(compose_file)
        print(f"✓ Compose-Stack gestoppt für {spec_id}")
        if self._log_streamer is not None:
            self._log_streamer.detach(spec_id)

    # ── SPEC-0021 commands ────────────────────────────────────────────────────

    def start(self, spec_id: str) -> None:
        if self._compose_file():
            self.up(spec_id)
            return

        cname = container_name(spec_id)
        bname = branch_name(spec_id)
        status = self._runtime.inspect_status(cname)

        if status == "running":
            print(f"[WARN] Container {cname} läuft bereits – kein zweiter Start.", file=sys.stderr)
            return

        if status == "exited":
            self._runtime.start(cname)
            print(f"✓ Container {cname} wieder gestartet (war gestoppt).")
            return

        branch_created = False
        try:
            if not _branch_exists(bname):
                base = resolve_base_branch(self.cfg.raw)
                # Ohne base: von HEAD. `git checkout -b` nimmt uncommittete
                # Aenderungen mit, der Wechsel auf einen fremden Baum nicht.
                _git(["checkout", "-b", bname] + ([base] if base else []))
                branch_created = True

            image = self._docker_image()
            self._runtime.run_container(
                cname,
                image,
                volume=f"{self.cfg.root}:/workspace",
                env={
                    "SPEC_ID": spec_id,
                    "GIT_BRANCH": bname,
                    **_llm_env_vars(),
                },
            )
            print(f"✓ Container {cname} gestartet | Branch {bname} | Image {image}")
        except subprocess.CalledProcessError as exc:
            if branch_created:
                # Zurueck auf den Ausgangspunkt, nicht pauschal auf main.
                _git(["checkout", "-"], check=False)
                _git(["branch", "-D", bname], check=False)
            print(f"✗ Runtime-Fehler – Rollback abgeschlossen: {exc}", file=sys.stderr)
            if not branch_created and resolve_base_branch(self.cfg.raw):
                # Der haeufigste Grund, wenn ein fester Abzweigpunkt gesetzt ist:
                # `sdd start` schreibt vorher Spec-Status und audit.log.
                print(
                    "  Uncommittete Aenderungen? Committe sie, oder entferne "
                    "docker.base_branch, damit von HEAD abgezweigt wird.",
                    file=sys.stderr,
                )
            sys.exit(1)

    def exec_cmd(self, spec_id: str, cmd: list[str]) -> None:
        cname = container_name(spec_id)
        if self._runtime.inspect_status(cname) != "running":
            print(
                f"✗ Container {cname} läuft nicht. Führe 'sdd start {spec_id}' aus.",
                file=sys.stderr,
            )
            sys.exit(1)
        result = self._runtime.exec_in(cname, cmd)
        sys.exit(result.returncode)

    def close(self, spec_id: str, *, delete_branch: bool = False) -> None:
        compose_file = self._compose_file()
        if compose_file:
            self._runtime.compose_down(compose_file)
            print(f"✓ Compose-Stack gestoppt für {spec_id}.")
        else:
            cname = container_name(spec_id)
            self._runtime.stop(cname)
            self._runtime.rm(cname)
            print(f"✓ Container {cname} gestoppt und entfernt.")
        if delete_branch:
            bname = branch_name(spec_id)
            if _branch_exists(bname):
                _git(["branch", "-D", bname])
                print(f"✓ Branch {bname} gelöscht.")

    def pr(self, spec_id: str) -> None:
        test_result, passed, total = _load_last_test_result(self.cfg, spec_id)

        if test_result == "skipped":
            print(
                f"✗ Kein Test-Ergebnis für {spec_id} – führe "
                f"'sdd finalize {spec_id}' aus.",
                file=sys.stderr,
            )
            sys.exit(1)

        if test_result == "failed":
            print(
                f"✗ Tests nicht grün – prüfe den Lauf aus 'sdd finalize {spec_id}'.",
                file=sys.stderr,
            )
            sys.exit(1)

        result = _run(["sdd", "validate"], capture=True, check=False)
        if result.returncode != 0:
            print("✗ sdd validate meldet Fehler:", file=sys.stderr)
            print(result.stdout, file=sys.stderr)
            sys.exit(1)

        uncommitted = _git(["status", "--porcelain"], capture=True, check=False)
        if uncommitted.stdout.strip():
            print("[WARN] Uncommitted changes vorhanden – bitte committen.", file=sys.stderr)

        self._pr_strategy.create(spec_id, self.cfg)
