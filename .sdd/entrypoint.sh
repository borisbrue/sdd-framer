#!/bin/bash
set -e

# Install project in development mode if pyproject.toml exists
if [ -f /workspace/pyproject.toml ] && [ -f /workspace/tool/sdd_cli/__init__.py ]; then
    pip install -q -e /workspace/tool/[dev] 2>/dev/null || \
    pip install -q pytest pytest-cov 2>/dev/null
fi

exec "$@"
