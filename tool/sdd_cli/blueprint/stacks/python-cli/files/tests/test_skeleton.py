"""Walking Skeleton: ein FR-markierter Test, damit sdd stack verify die Test-Sonde prüfen kann."""
import pytest

from {{package_name}} import __version__
from {{package_name}}.__main__ import main


@pytest.mark.fr("FR-01")
def test_skeleton_startet(capsys):
    assert main() == 0
    assert __version__ in capsys.readouterr().out
