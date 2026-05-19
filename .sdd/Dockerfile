FROM python:3.12-slim

LABEL org.opencontainers.image.title="sdd-dev"
LABEL org.opencontainers.image.description="SDD Dev-Container – isolierte Entwicklungsumgebung pro Spec"

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Install project dependencies from the volume-mounted workspace at runtime.
# The entrypoint installs deps and then runs the given command.
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["tail", "-f", "/dev/null"]
