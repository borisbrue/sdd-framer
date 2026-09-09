#!/bin/bash
# Installiert die Projektabhaengigkeiten aus dem gemounteten Workspace und
# fuehrt dann den uebergebenen Befehl aus.
#
# Zur Laufzeit statt im Image, damit eine geaenderte Abhaengigkeit keinen
# Neubau erzwingt. Projektunabhaengig: es wird installiert, was da ist.
set -e

cd /workspace 2>/dev/null || true

if [ -f /workspace/uv.lock ]; then
    uv sync --frozen 2>/dev/null || uv sync 2>/dev/null || true
elif [ -f /workspace/pyproject.toml ]; then
    pip install -q -e /workspace 2>/dev/null || true
elif [ -f /workspace/requirements.txt ]; then
    pip install -q -r /workspace/requirements.txt 2>/dev/null || true
fi

exec "$@"
