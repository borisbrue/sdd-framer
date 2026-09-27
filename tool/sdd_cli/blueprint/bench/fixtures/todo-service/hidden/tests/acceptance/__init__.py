"""Versteckte Akzeptanztests des Benchmark-Fixtures todo-service (SPEC-0063 FR-05).

Jeder Testname trägt den Marker `spec000N_frNN`. Die Tests nutzen nur die öffentliche API aus den
Specs (`todo.domain`, `todo.service`, `todo.persistence`) und die CLI `python -m todo`; Importe
stehen in den Tests, damit im Startstand jeder Test einzeln rot ist.
"""
