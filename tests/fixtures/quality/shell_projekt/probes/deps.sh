#!/bin/sh
cat <<'JSON'
{"format": "sdd-deps", "version": 1, "kinds_provided": ["import"], "edges": [
  {"from": "app/main.sh", "to": "lib/util.sh", "kind": "import", "symbol": "util.sh", "file": "app/main.sh", "line": 2},
  {"from": "lib/util.sh", "to": "app/main.sh", "kind": "import", "symbol": "main.sh", "file": "lib/util.sh", "line": 2}]}
JSON
