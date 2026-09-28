"""pytest-Plugin der Vorlage python-cli (SPEC-0054 FR-14).

`@pytest.mark.fr("FR-03")` ordnet einen Test einer Anforderung zu. Das Plugin schreibt die
Zuordnung als JUnit-Property `fr`, die `sdd quality measure` auswertet.

Aktivieren: `PYTHONPATH=.sdd/quality python3 -m pytest -p sdd_fr_marker --junitxml=…`
"""
from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "fr(*ids): ordnet den Test FR-IDs der Spec zu (sdd)")


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    for marker in item.iter_markers("fr"):
        for fr in marker.args:
            item.user_properties.append(("fr", str(fr)))
