"""Der Container darf das .venv des Hosts nicht ueberschreiben.

`{root}:/workspace` ist ein Bind-Mount. Legt im Container irgendein Befehl ein
venv an — `uv run` tut das ungefragt —, landet es unter `/workspace/.venv` und
damit im Arbeitsverzeichnis des Hosts. Danach zeigt `.venv/bin/python` auf ein
Python, das es nur im Container gibt.

Aufgetreten bei `sdd finalize SPEC-0005`: der Testlauf im Container ersetzte das
Python 3.13 des Hosts durch das 3.12 des Images, und finalize meldete daraufhin
"Tests fehlgeschlagen" — ein Infrastrukturproblem, das als Testfehler erschien.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

# DockerRuntime/PodmanRuntime gibt es in beiden Staenden; die neuen Symbole
# lazy, damit die Runtime-Tests auch gegen einen Stand ohne sie laufen und der
# RED-Nachweis nicht auf einen Collection-Error zusammenfaellt.
from sdd_cli.dev_container import DockerRuntime, PodmanRuntime


def venv_guard_args(workspace: str = "/workspace"):
    from sdd_cli.dev_container import venv_guard_args as _impl
    return _impl(workspace)


def _container_venv() -> str:
    from sdd_cli.dev_container import CONTAINER_VENV
    return CONTAINER_VENV


class TestSchutzargumente:
    def test_anonymes_volume_ueberdeckt_den_mount(self):
        assert "-v" in venv_guard_args() and "/workspace/.venv" in venv_guard_args()

    def test_uv_wird_aus_dem_mount_gelenkt(self):
        assert f"UV_PROJECT_ENVIRONMENT={_container_venv()}" in venv_guard_args()

    def test_zielpfad_liegt_ausserhalb_des_workspace(self):
        """Sonst waere die Umlenkung wirkungslos."""
        assert not _container_venv().startswith("/workspace")

    def test_abweichender_workspace_wird_beruecksichtigt(self):
        args = venv_guard_args("/code")
        assert "/code/.venv" in args and "/workspace/.venv" not in args

    def test_beide_massnahmen_zusammen(self):
        """Die Env-Variable allein greift nicht bei `python -m venv .venv`,
        das Volume allein nicht, wenn uv woanders hin schreiben soll."""
        args = venv_guard_args()
        assert args.count("-v") == 1 and args.count("-e") == 1


class TestBeideRuntimesSchuetzen:
    def _aufruf(self, runtime) -> list[str]:
        erfasst: list[str] = []
        with patch.object(runtime, "_cmd", lambda args, **kw: erfasst.extend(args)):
            runtime.run_container("c", "img", volume="/host:/workspace", env={})
        return erfasst

    def test_docker(self):
        args = self._aufruf(DockerRuntime())
        assert "/workspace/.venv" in args
        assert f"UV_PROJECT_ENVIRONMENT={_container_venv()}" in args

    def test_podman(self):
        args = self._aufruf(PodmanRuntime())
        assert "/workspace/.venv" in args
        assert f"UV_PROJECT_ENVIRONMENT={_container_venv()}" in args

    def test_der_workspace_mount_bleibt(self):
        args = self._aufruf(PodmanRuntime())
        assert "/host:/workspace" in args, "Der eigentliche Bind-Mount muss bleiben"

    def test_reihenfolge_volume_vor_image(self):
        """Das Image ist das letzte Argument vor dem Kommando."""
        args = self._aufruf(DockerRuntime())
        assert args.index("/workspace/.venv") < args.index("img")

    def test_uebergebene_env_bleibt_erhalten(self):
        erfasst: list[str] = []
        rt = PodmanRuntime()
        with patch.object(rt, "_cmd", lambda args, **kw: erfasst.extend(args)):
            rt.run_container("c", "img", volume="/host:/workspace",
                             env={"SPEC_ID": "SPEC-0001"})
        assert "SPEC_ID=SPEC-0001" in erfasst


class TestEvalContainerEbenfalls:
    def test_eval_container_nutzt_denselben_schutz(self):
        import inspect

        from sdd_cli import eval_container
        src = inspect.getsource(eval_container)
        assert "_venv_guard(ecfg.workspace)" in src, (
            "Der Eval-Container mountet denselben Workspace und braucht denselben Schutz"
        )
