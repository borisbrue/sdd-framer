"""mypy `--output json` (eine JSON-Zeile je Befund) → SARIF 2.1.0 auf stdout (Vorlage python-cli)."""
from __future__ import annotations

import json
import sys

LEVEL = {"error": "error", "warning": "warning", "note": "note"}


def main() -> int:
    results = []
    for zeile in sys.stdin:
        zeile = zeile.strip()
        if not zeile.startswith("{"):
            continue
        d = json.loads(zeile)
        region = {"startLine": max(int(d.get("line") or 1), 1)}
        if isinstance(d.get("column"), int) and d["column"] >= 0:
            region["startColumn"] = d["column"] + 1
        results.append({
            "ruleId": d.get("code") or "mypy",
            "level": LEVEL.get(d.get("severity"), "warning"),
            "message": {"text": d.get("message", "")},
            "locations": [{"physicalLocation": {"artifactLocation": {"uri": d.get("file", "")},
                                                "region": region}}],
        })
    json.dump({"version": "2.1.0",
               "runs": [{"tool": {"driver": {"name": "mypy"}}, "results": results}]}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
