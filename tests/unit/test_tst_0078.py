# TST-0078 – Performance: Container-Start SLO (CON-0068)
from __future__ import annotations


def test_slo_placeholder():
    """Platzhalter: Eine Zeitmessung für CON-0068 gibt es noch nicht.

    Geprüft werden nur die deterministischen Namen (CON-0065 INV-01/INV-02).
    Die Docstring nannte bis #123 einen Messlauf über `sdd dev exec` nach
    tests/performance/. Den Befehl gibt es seit SPEC-0044 nicht mehr, und die
    Messdatei wurde nie angelegt.
    """
    from sdd_cli.dev_container import branch_name, container_name
    assert container_name("SPEC-0021") == "sdd-dev-spec-0021"
    assert branch_name("SPEC-0021") == "dev/SPEC-0021"
