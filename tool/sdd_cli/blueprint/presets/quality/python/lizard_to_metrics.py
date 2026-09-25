"""lizard `--csv` → sdd-metrics auf stdout (sdd-Preset `python`).

Metriken: complexity_mean, complexity_max, complex_function_share (CCN > 10),
long_function_share (Länge > 60 Zeilen).
"""
from __future__ import annotations

import csv
import json
import sys

COMPLEX_CCN = 10
LONG_LINES = 60


def main() -> int:
    ccn, laengen = [], []
    for zeile in csv.reader(sys.stdin):
        if len(zeile) < 5 or not zeile[1].strip().isdigit():
            continue
        ccn.append(int(zeile[1]))
        laengen.append(int(zeile[4]))
    n = len(ccn)
    metrics = [
        {"name": "complexity_mean", "value": sum(ccn) / n if n else 0.0},
        {"name": "complexity_max", "value": max(ccn) if n else 0},
        {"name": "complex_function_share", "value": sum(c > COMPLEX_CCN for c in ccn) / n if n else 0.0},
        {"name": "long_function_share", "value": sum(lg > LONG_LINES for lg in laengen) / n if n else 0.0},
    ]
    json.dump({"format": "sdd-metrics", "version": 1, "tool": {"name": "lizard"},
               "metrics": metrics}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
