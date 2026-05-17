FROM python:3.12-slim

LABEL org.opencontainers.image.title="sdd-dev"
LABEL org.opencontainers.image.description="SDD Dev-Container – isolierte Entwicklungsumgebung pro Spec"

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Install sdd-cli from the mounted workspace (development mode)
# This runs when the container starts with the project volume mounted.
# For CI builds, copy the tool directory instead:
# COPY tool/ /app/tool/
# RUN pip install -e /app/tool/[dev]

# Keep container running for `sdd dev exec` usage
CMD ["tail", "-f", "/dev/null"]
