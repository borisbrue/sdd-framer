"""SPEC-0054 FR-08, CON-0196 (Formel Normierung)."""
from __future__ import annotations

import pytest

from sdd_cli.quality.normalize import BUILTIN_NORMALIZATION, normalize


@pytest.mark.parametrize(("good", "bad", "roh", "norm"), [
    (0, 10, 5, 0.5), (0, 10, 12, 0.0), (0, 10, 0, 1.0), (0, 10, -3, 1.0),
    (0.9, 0.5, 0.7, 0.5), (0.9, 0.5, 0.95, 1.0), (0.9, 0.5, 0.1, 0.0)])
def test_linear_und_begrenzt(good, bad, roh, norm):
    assert normalize(roh, good, bad) == pytest.approx(norm)


def test_gleiche_grenzen_sind_fehler():
    with pytest.raises(ValueError):
        normalize(1, 2, 2)


def test_eingebaute_normierungen():
    assert BUILTIN_NORMALIZATION == {"lint_per_kloc": (0, 10), "type_errors": (0, 20),
                                     "suppressions": (0, 10), "test_ratio": (1.0, 0.0)}
