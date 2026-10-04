"""SpecFinalizer – einheitliche Finalisierungsphase für alle Implementierungspfade.

Wird verwendet von:
  - sdd finalize (CLI)
  - /sdd-implement (Skill, Schritt 5)
  - sdd orchestrate (nach Code-Generierung)
  - sdd distribute (nach Task-Loop)

Ablauf: git commit → Container-Check → Build (optional, #111) → Tests im Container
        → Container entfernen → PR
"""
from __future__ import annotations

import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .config import SddConfig
from .dev_container import (
    DevContainerManager,
    GhFallbackPRStrategy,
    branch_name,
    container_name,
    get_runtime,
    save_test_result,
)

FINALIZE_BRANCH_PREFIX = "feat"


@dataclass
class FinalizeReport:
    spec_id: str
    branch: str
    commit_hash: str | None
    tests_passed: bool
    test_output: str
    pr_url: str | None
    pr_path: Path | None
    error: str | None
    # Build vor den Tests (#111). None: kein Build-Kommando gesetzt.
    build_passed: bool | None = None
    build_output: str = ""


def _befehl_ausfuehren(befehl, *, cwd: Path, timeout: int, shell: bool = False) -> tuple[bool, str]:
    """Fuehrt den Build aus; (erfolgreich, Ausgabe). Ein Zeitlimit ist ein Fehlschlag."""
    try:
        r = subprocess.run(befehl, shell=shell, capture_output=True, text=True,
                           cwd=cwd, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"Zeitlimit von {timeout}s ueberschritten"
    return r.returncode == 0, (r.stdout + r.stderr).strip()


_PYTEST_STANDARD = ["tests/", "-x", "--tb=short"]


def _ist_pytest(teile: list[str]) -> bool:
    """`pytest`, `.venv/bin/pytest`, `uv run pytest`, `python -m pytest`."""
    if not teile:
        return False
    if Path(teile[-1]).name == "pytest":
        return True
    return "-m" in teile[:-1] and teile[teile.index("-m") + 1] == "pytest"


def testaufruf(test_cfg: dict, root: Path) -> list[str]:
    """Der Testaufruf der Finalisierung — einer fuer Container- und Compose-Weg.

    Vorher rechneten beide Wege verschieden (#117): der Container haengte fest
    `tests/ -x --tb=short` an jedes Kommando (npm-Projekte liefen als
    `npm tests/ -x`), der Compose-Weg gab ein mehrwortiges Kommando wie
    `uv run pytest` als einen Programmnamen weiter (FileNotFoundError).

    Die pytest-Standardargumente gelten fuer jedes pytest-artige Kommando — auch
    fuer das `command: pytest` des Blueprints, sonst saemmelte ein nacktes pytest
    ab der Projektwurzel. `npm` bekommt `test`, alles andere laeuft wie
    konfiguriert. `extra_args` kommt in jedem Fall dazu.
    """
    extra = [str(a) for a in (test_cfg.get("extra_args") or [])]
    eigenes = str(test_cfg.get("command") or "").strip()
    if eigenes:
        teile = shlex.split(eigenes)
    elif (root / "package.json").exists():
        teile = ["npm"]
    else:
        teile = ["pytest"]

    if _ist_pytest(teile):
        return teile + _PYTEST_STANDARD + extra
    if teile == ["npm"]:
        return teile + ["test"] + extra
    return teile + extra


def _git(args: list[str], *, cwd: Path, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + args, capture_output=capture, text=True, cwd=cwd)


def _image_exists(cli: str, image: str) -> bool:
    result = subprocess.run(
        [cli, "image", "inspect", image],
        capture_output=True,
    )
    return result.returncode == 0


def _runtime_available(cli: str) -> bool:
    """False statt Absturz, wenn die Runtime fehlt (vgl. DevContainerManager)."""
    try:
        result = subprocess.run([cli, "info"], capture_output=True)
    except (FileNotFoundError, OSError):
        return False
    return result.returncode == 0


class SpecFinalizer:
    def __init__(self, cfg: SddConfig, dry_run: bool = False) -> None:
        self._cfg = cfg
        self._dry_run = dry_run
        self._mgr = DevContainerManager(
            cfg,
            runtime=get_runtime(cfg),
        )

    def run(
        self,
        spec_id: str,
        *,
        commit_msg: str = "",
        no_commit: bool = False,
        branch: str | None = None,
        skip_container: bool = False,
        build_cmd: str | None = None,
    ) -> FinalizeReport:
        effective_branch = branch or branch_name(spec_id, prefix=FINALIZE_BRANCH_PREFIX)
        root = self._cfg.root

        # 1. Branch sicherstellen
        if not no_commit:
            existing = _git(["branch", "--list", effective_branch], cwd=root)
            if effective_branch not in existing.stdout:
                _git(["checkout", "-b", effective_branch], cwd=root)
            else:
                _git(["checkout", effective_branch], cwd=root)

        # 2. Commit (wenn Caller noch nicht committed hat)
        commit_hash: str | None = None
        if not no_commit:
            status = _git(["status", "--porcelain"], cwd=root)
            if status.stdout.strip():
                msg = commit_msg or f"feat({spec_id}): implementiert via sdd finalize"
                # Ein fehlgeschlagener add/commit (z. B. ohne Git-Identitaet) brach
                # nicht ab: rev-parse lieferte den alten HEAD, die Spec wurde
                # trotzdem implemented (#142).
                for args in (["add", "-A"], ["commit", "-m", msg]):
                    result = _git(args, cwd=root)
                    if result.returncode != 0:
                        meldung = (f"git {args[0]} fehlgeschlagen:\n"
                                   f"{(result.stdout + result.stderr).strip()}")
                        return FinalizeReport(
                            spec_id=spec_id,
                            branch=effective_branch,
                            commit_hash=None,
                            tests_passed=False,
                            test_output=meldung,
                            pr_url=None,
                            pr_path=None,
                            error=meldung,
                        )
            head = _git(["rev-parse", "HEAD"], cwd=root)
            commit_hash = head.stdout.strip() or None
        else:
            head = _git(["rev-parse", "HEAD"], cwd=root)
            commit_hash = head.stdout.strip() or None

        quality = self._quality_gates(spec_id)
        if quality is not None and quality.passed is False and quality.mode == "block":
            return FinalizeReport(
                spec_id=spec_id,
                branch=effective_branch,
                commit_hash=commit_hash,
                tests_passed=False,
                test_output=quality.message,
                pr_url=None,
                pr_path=None,
                error=quality.message,
            )

        if self._dry_run:
            return FinalizeReport(
                spec_id=spec_id,
                branch=effective_branch,
                commit_hash=commit_hash,
                tests_passed=True,
                test_output="dry-run: Tests übersprungen",
                pr_url="https://dry-run/pr/1",
                pr_path=None,
                error=None,
            )

        if skip_container:
            pr_url, pr_path, pr_error = self._create_pr(
                spec_id, effective_branch, commit_hash)
            return FinalizeReport(
                spec_id=spec_id,
                branch=effective_branch,
                commit_hash=commit_hash,
                tests_passed=pr_error is None,
                test_output="⚠ Container-Tests wurden übersprungen",
                pr_url=pr_url,
                pr_path=pr_path,
                error=pr_error,
            )

        docker_cfg = self._cfg.raw.get("docker", {})
        compose_file = docker_cfg.get("compose_file", "")
        test_cfg = self._cfg.raw.get("test_runner", {})
        timeout = test_cfg.get("timeout_per_spec", 120)
        argv = testaufruf(test_cfg, root)

        # Build-Kommando: Argument (--build-cmd) vor orchestrator.build_command.
        # SPEC-0026 hatte den Build-Schritt aus dem Orchestrator entfernt, ohne ihn
        # hier anzubinden — Option und Config-Schluessel wirkten seither nicht
        # (#111). Er laeuft auf demselben Weg wie die Tests, unmittelbar davor.
        if build_cmd is None:
            build_cmd = str((self._cfg.raw.get("orchestrator") or {}).get("build_command") or "")
        build_cmd = build_cmd.strip() or None
        build_passed: bool | None = None
        build_output = ""

        if compose_file:
            # Container-Stack muss bereits laufen
            if build_cmd:
                build_passed, build_output = _befehl_ausfuehren(
                    build_cmd, cwd=root, timeout=timeout, shell=True)
                if not build_passed:
                    return self._build_fehlgeschlagen(
                        spec_id, effective_branch, commit_hash, build_output)
            try:
                test_result = subprocess.run(
                    argv,
                    capture_output=True,
                    text=True,
                    cwd=root,
                    timeout=timeout,
                )
            except FileNotFoundError as exc:
                raise RuntimeError(
                    f"✗ Test-Runner '{argv[0]}' nicht gefunden. "
                    f"Setze 'test_runner.command' in .sdd/config.yaml oder nutze --skip-container."
                ) from exc
        else:
            # Container muss bereits laufen
            runtime = get_runtime(self._cfg)
            cname = container_name(spec_id)
            status_now = runtime.inspect_status(cname)
            if status_now != "running":
                raise RuntimeError(
                    f"✗ Dev-Container nicht gefunden – starte ihn mit 'sdd start {spec_id}'"
                )

            if build_cmd:
                build_passed, build_output = _befehl_ausfuehren(
                    [runtime.cli(), "exec", cname, "bash", "-c", f"cd /workspace && {build_cmd}"],
                    cwd=root, timeout=timeout)
                if not build_passed:
                    # Der Container bleibt stehen — wie bei roten Tests, damit man
                    # hineinschauen kann.
                    return self._build_fehlgeschlagen(
                        spec_id, effective_branch, commit_hash, build_output)

            inner_cmd = "cd /workspace && " + shlex.join(argv)
            test_result = subprocess.run(
                [runtime.cli(), "exec", cname, "bash", "-c", inner_cmd],
                capture_output=True,
                text=True,
                cwd=root,
                timeout=timeout,
            )

        test_output = (test_result.stdout + test_result.stderr).strip()
        tests_passed = test_result.returncode == 0

        passed_count, total_count = _parse_pytest_counts(test_output)
        save_test_result(self._cfg, spec_id, passed=passed_count, total=total_count)

        # Der Container bleibt stehen, wenn die Tests rot sind: bei einem
        # Fehlschlag will man hineinschauen koennen. Vorher wurde er hier
        # entfernt, bevor finalize ueberhaupt scheitern konnte — und der
        # Hinweis "starte ihn mit sdd start" fuehrte ins Leere.
        if not compose_file and tests_passed:
            self._mgr.close(spec_id)

        pr_url: str | None = None
        pr_path: Path | None = None
        error: str | None = None

        if tests_passed:
            # FR-06/CON-0153: Compliance-Kette vor _mark_implemented
            compliance_error = self._run_compliance_check(spec_id)
            if compliance_error:
                return FinalizeReport(
                    spec_id=spec_id,
                    branch=effective_branch,
                    commit_hash=commit_hash,
                    tests_passed=False,
                    test_output=test_output,
                    pr_url=None,
                    pr_path=None,
                    error=compliance_error,
                    build_passed=build_passed,
                    build_output=build_output,
                )
            pr_url, pr_path, pr_error = self._create_pr(
                spec_id, effective_branch, commit_hash)
            if pr_error:
                error = pr_error
                tests_passed = False
        else:
            error = f"Tests fehlgeschlagen im Container:\n{test_output[:1000]}"

        return FinalizeReport(
            spec_id=spec_id,
            branch=effective_branch,
            commit_hash=commit_hash,
            tests_passed=tests_passed,
            test_output=test_output,
            pr_url=pr_url,
            pr_path=pr_path,
            error=error,
            build_passed=build_passed,
            build_output=build_output,
        )

    def _build_fehlgeschlagen(
        self, spec_id: str, branch: str, commit_hash: str | None, ausgabe: str,
    ) -> FinalizeReport:
        return FinalizeReport(
            spec_id=spec_id,
            branch=branch,
            commit_hash=commit_hash,
            tests_passed=False,
            test_output="",
            pr_url=None,
            pr_path=None,
            error=f"Build fehlgeschlagen:\n{ausgabe[:1000]}",
            build_passed=False,
            build_output=ausgabe,
        )

    def _run_compliance_check(self, spec_id: str) -> str | None:
        """Gibt None zurück wenn Compliance OK, sonst formatierten Fehlertext."""
        from .compliance import run_compliance_chain
        from .decompose import TaskDecomposer
        from .frontmatter import parse_safe

        spec_doc = None
        for md in self._cfg.specs_dir.rglob("*.md"):
            doc = parse_safe(md)
            if doc and doc.frontmatter.get("id") == spec_id:
                spec_doc = doc
                break
        if spec_doc is None:
            return None

        tasks = TaskDecomposer().load(spec_id, self._cfg)
        issues = run_compliance_chain(
            spec=spec_doc,
            tasks=tasks,
            cfg_raw=self._cfg.raw,
            tests_dir=self._cfg.tests_dir,
            project_root=self._cfg.root,
            strict=True,
        )
        errors = [i for i in issues if i.severity == "error"]
        if not errors:
            return None

        lines = ["✗ Compliance-Gate blockiert finalize:"]
        for issue in errors:
            lines.append(f"  • {issue.message}")
            if issue.hint:
                lines.append(f"    → {issue.hint}")
        return "\n".join(lines)

    def _quality_gates(self, spec_id: str):
        """SPEC-0054 FR-10: quality.finalize warn|block|off; warn nur als Hinweis."""
        from .quality import gate_integration

        entscheidung = gate_integration.check_quality_gates(self._cfg.root, spec_id, self._cfg.raw)
        if entscheidung.passed is False and entscheidung.mode == "warn":
            print(f"⚠ {entscheidung.message}", file=sys.stderr)
        return entscheidung

    def _create_pr(
        self, spec_id: str, branch: str, commit_hash: str | None
    ) -> tuple[str | None, Path | None, str | None]:
        """Erstellt den PR vom finalisierten Branch. Gibt (url, pfad, fehler) zurueck.

        Der Branch wird uebergeben, nicht erneut abgeleitet. Vorher rief diese
        Methode strategy.create(spec_id, cfg) auf, worauf die Strategie sich ihren
        Branch selbst bildete — ueber das dev/-Schema. Committet wurde aber auf
        feat/, sodass der PR die finalisierte Arbeit nicht enthielt.
        """
        guard = self._branch_missing_commit(branch, commit_hash)
        if guard:
            # Kein PR und kein implemented-Status: ein PR ohne die finalisierte
            # Arbeit ist schlimmer als ein Abbruch, weil er beim Merge nichts
            # liefert und die Spec trotzdem Vollzug meldet.
            return None, None, guard

        push_fehler = self._push_branch(branch)
        if push_fehler:
            # Ohne Remote-Branch kann gh pr create nicht greifen ("No commits
            # between main and <branch>"). Der Lauf faellt dann auf die lokale
            # PR-Datei zurueck — mit dem Grund, statt nur mit dem Ergebnis.
            print(push_fehler, file=sys.stderr)

        strategy = GhFallbackPRStrategy()
        pr_url = strategy.create(spec_id, self._cfg, branch=branch)
        pr_path = None if pr_url else self._cfg.root / ".sdd" / "prs" / f"PR-{spec_id}.md"
        self._mark_implemented(spec_id)
        return pr_url, pr_path, None

    def _push_branch(self, branch: str) -> str | None:
        """Schiebt den finalisierten Branch aufs Remote. Gibt den Fehler zurueck.

        `gh pr create` verlangt einen Branch, den es auf origin gibt. finalize
        legte ihn nur lokal an, weshalb der Aufruf zuverlaessig scheiterte:

            No commits between main and feat/SPEC-0002,
            Head ref must be a branch (createPullRequest)

        Der PR landete als lokale Datei, und der Zweck des Kommandos — Spec zu
        PR ohne Handgriffe — war verfehlt. Ohne Remote (kein origin, kein
        Netz) bleibt der lokale Rueckfall unveraendert bestehen; der Push ist
        kein Abbruchgrund.
        """
        if _git(["remote", "get-url", "origin"], cwd=self._cfg.root).returncode != 0:
            return "  ⚠ Kein 'origin' konfiguriert – Branch wird nicht gepusht."

        result = _git(["push", "-u", "origin", branch], cwd=self._cfg.root)
        if result.returncode == 0:
            print(f"  ✓ Branch '{branch}' nach origin gepusht.")
            return None
        grund = (result.stderr or result.stdout or "").strip().splitlines()
        return (f"  ⚠ Push von '{branch}' fehlgeschlagen – PR wird lokal abgelegt."
                + ("\n    " + "\n    ".join(grund[-3:]) if grund else ""))

    def _branch_missing_commit(self, branch: str, commit_hash: str | None) -> str | None:
        """Prueft, ob der PR-Head den Finalize-Commit enthaelt."""
        if not commit_hash:
            return None
        result = _git(
            ["merge-base", "--is-ancestor", commit_hash, branch],
            cwd=self._cfg.root,
        )
        if result.returncode == 0:
            return None
        return (
            f"✗ Branch '{branch}' enthaelt den Finalize-Commit {commit_hash[:12]} nicht — "
            f"kein PR erstellt.\n"
            f"  Ein PR von diesem Branch wuerde die finalisierte Arbeit nicht enthalten.\n"
            f"  Pruefe: git log --oneline {branch} | head"
        )

    def _mark_implemented(self, spec_id: str) -> None:
        from .frontmatter import parse_safe, patch_status
        for md in self._cfg.specs_dir.rglob("*.md"):
            doc = parse_safe(md)
            if doc and doc.frontmatter.get("id") == spec_id:
                patch_status(md, "implemented")
                break


def _parse_pytest_counts(output: str) -> tuple[int, int]:
    """Extrahiert (passed, total) aus pytest-Output. Gibt (0, 0) bei Fehler."""
    import re
    m = re.search(r"(\d+) passed", output)
    passed = int(m.group(1)) if m else 0
    m2 = re.search(r"(\d+) failed", output)
    failed = int(m2.group(1)) if m2 else 0
    return passed, passed + failed
