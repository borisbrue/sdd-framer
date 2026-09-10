# SDD Dev-Container – isolierte Entwicklungsumgebung pro Spec.
#
# Gebaut wird mit dem Projektwurzelverzeichnis als Kontext:
#   <runtime> build -t sdd-dev:latest -f .sdd/Dockerfile .
# Deshalb sind alle COPY-Pfade relativ zur Projektwurzel, nicht zu dieser Datei.
#
# ── Anpassungspunkte ─────────────────────────────────────────────────────────
# 1. Basis-Image: Fuer ein Node- oder Go-Projekt hier tauschen.
# 2. Systempakete: git und curl braucht der Container immer, der Rest haengt am
#    Projekt (build-essential nur fuer Pakete, die C-Erweiterungen bauen).
# 3. Abhaengigkeiten: installiert der entrypoint zur Laufzeit aus dem gemounteten
#    Workspace — nicht hier, sonst muesste das Image bei jeder Aenderung neu
#    gebaut werden.

FROM python:3.12-slim

LABEL org.opencontainers.image.title="sdd-dev"
LABEL org.opencontainers.image.description="SDD Dev-Container – isolierte Entwicklungsumgebung pro Spec"

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# uv, falls das Projekt eine uv.lock mitbringt. Ohne sie ungenutzt und billig.
RUN pip install --no-cache-dir uv

# Zielort des Projekt-venv im Container. Muss zu CONTAINER_VENV in
# dev_container.py passen: der Aufruf mountet ein leeres Volume ueber
# /workspace/.venv, damit das venv des Hosts unangetastet bleibt (#60).
ENV UV_PROJECT_ENVIRONMENT=/opt/sdd-venv
ENV PATH="/opt/sdd-venv/bin:${PATH}"

WORKDIR /workspace

COPY .sdd/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["tail", "-f", "/dev/null"]
