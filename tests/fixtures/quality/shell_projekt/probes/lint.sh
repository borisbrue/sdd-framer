#!/bin/sh
cat <<'JSON'
{"format": "sdd-findings", "version": 1, "tool": {"name": "shell-lint"}, "findings": [
  {"rule": "SC2034", "message": "unbenutzte Variable", "file": "lib/util.sh", "line": 3, "severity": "warning"},
  {"rule": "SC2154", "message": "nicht zugewiesen", "file": "lib/util.sh", "line": 4, "severity": "warning"}]}
JSON
