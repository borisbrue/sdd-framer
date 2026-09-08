"""Die Container-Runtime wird erkannt statt behauptet.

Das Blueprint setzte `docker.runtime: docker` fest. Auf einem System, auf dem
nur Podman installiert ist, scheiterte damit jedes frisch initialisierte
Projekt beim ersten Container-Schritt — obwohl eine funktionierende Runtime da
war. Fuenf Stellen lasen den Wert mit demselben hartkodierten Rueckfall, keine
davon prueft, ob das Binary existiert.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

# Lazy: sonst scheitert schon das Einsammeln des Moduls gegen einen Stand ohne
# die neuen Funktionen, und der RED-Nachweis waere nur ein ImportError.


def detect_runtime():
    from sdd_cli.dev_container import detect_runtime as _impl
    return _impl()


def resolve_runtime(raw):
    from sdd_cli.dev_container import resolve_runtime as _impl
    return _impl(raw)

_ROOT = Path(__file__).resolve().parents[2]


def _installed(*namen: str):
    """Patcht shutil.which so, dass nur `namen` als installiert gelten."""
    from sdd_cli import dev_container
    return patch.object(dev_container.shutil, "which",
                        lambda n: f"/usr/bin/{n}" if n in namen else None)


class TestDetection:
    def test_docker_wins_when_both_exist(self):
        """Wo bisher alles lief, aendert sich nichts."""
        with _installed("docker", "podman"):
            assert detect_runtime() == "docker"

    def test_podman_when_docker_is_missing(self):
        with _installed("podman"):
            assert detect_runtime() == "podman"

    def test_docker_when_only_docker_exists(self):
        with _installed("docker"):
            assert detect_runtime() == "docker"

    def test_falls_back_to_docker_when_nothing_is_installed(self):
        """Der Fehler gehoert in den Aufruf, nicht in die Erkennung."""
        with _installed():
            assert detect_runtime() == "docker"


class TestExplicitConfigWins:
    def test_configured_docker_is_kept_on_a_podman_only_host(self):
        with _installed("podman"):
            assert resolve_runtime({"docker": {"runtime": "docker"}}) == "docker"

    def test_configured_podman_is_kept(self):
        with _installed("docker", "podman"):
            assert resolve_runtime({"docker": {"runtime": "podman"}}) == "podman"

    def test_detection_applies_without_a_configured_value(self):
        with _installed("podman"):
            assert resolve_runtime({}) == "podman"
            assert resolve_runtime({"docker": {}}) == "podman"

    def test_empty_string_counts_as_unset(self):
        with _installed("podman"):
            assert resolve_runtime({"docker": {"runtime": ""}}) == "podman"


class TestBlueprintLeavesItOpen:
    def test_blueprint_does_not_pin_the_runtime(self):
        """Sonst greift die Erkennung bei neuen Projekten gar nicht."""
        cfg = yaml.safe_load(
            (_ROOT / "tool" / "sdd_cli" / "blueprint" / "config.yaml").read_text(
                encoding="utf-8"))
        assert "runtime" not in cfg["docker"], (
            "Ein fester Wert im Blueprint macht die Erkennung wirkungslos"
        )

    def test_blueprint_still_documents_the_option(self):
        text = (_ROOT / "tool" / "sdd_cli" / "blueprint" / "config.yaml").read_text(
            encoding="utf-8")
        assert "# runtime: docker" in text, "Die Wahl muss auffindbar bleiben"


class TestMissingRuntimeIsHandled:
    """Verfuegbarkeit gehoert nicht in die Factory.

    get_runtime() bildet nur Name -> Klasse ab und bleibt umgebungsunabhaengig
    (TST-0079 TC-08 prueft genau das). Ob das Binary existiert, klaert
    runtime_available() — und das stuerzte bisher ab, statt False zu liefern:
    subprocess.run wirft FileNotFoundError, wenn der Befehl nicht existiert.
    """

    def _manager(self, runtime: str):
        from sdd_cli.config import SddConfig
        from sdd_cli.dev_container import DevContainerManager
        return DevContainerManager(
            SddConfig(root=Path("/tmp"), raw={"docker": {"runtime": runtime}}))

    def test_factory_stays_environment_independent(self):
        from sdd_cli.config import SddConfig
        from sdd_cli.dev_container import DockerRuntime, get_runtime

        cfg = SddConfig(root=Path("/tmp"), raw={"docker": {"runtime": "docker"}})
        with _installed("podman"):   # docker fehlt
            assert isinstance(get_runtime(cfg), DockerRuntime)

    def test_available_returns_false_instead_of_raising(self):
        from sdd_cli import dev_container

        with patch.object(dev_container.subprocess, "run",
                          side_effect=FileNotFoundError("docker")):
            assert self._manager("docker").runtime_available() is False

    def test_hint_names_the_installed_alternative(self):
        with _installed("podman"):
            hinweis = self._manager("docker").missing_runtime_hint()
        assert "podman" in hinweis and "docker.runtime" in hinweis

    def test_hint_says_so_when_nothing_is_installed(self):
        with _installed():
            hinweis = self._manager("docker").missing_runtime_hint()
        assert "Weder docker noch podman" in hinweis
