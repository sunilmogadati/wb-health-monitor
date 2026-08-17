# wb-health-monitor API image.
FROM python:3.11-slim-bookworm

# Fail fast and log unbuffered: a service that dies during startup must say why in the container log
# rather than buffering the reason and exiting silently.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# /workspace/backend, mirroring the repository layout, so tests/ stays a SIBLING of backend/ inside
# the container and pytest's `../tests` testpath resolves the same in both places.
WORKDIR /workspace/backend
ENV PYTHONPATH=/workspace/backend:/workspace

# curl is present for the container healthcheck only. Kept minimal — every package here is surface
# area for a container scan.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

# Dependencies are installed from the manifest alone, before the source is copied, so a source edit
# does not invalidate the dependency layer on every rebuild.
COPY pyproject.toml ./
RUN pip install --upgrade pip setuptools wheel \
 && pip install -e ".[dev]"

COPY . .

# Runs as a non-root user: a container running as root is a finding at any security review and it is
# free to avoid at build time.
RUN useradd --create-home --uid 10001 app && chown -R app:app /workspace
USER app

EXPOSE 8000

# --reload is correct for local development (the source tree is bind-mounted). Production runs this
# image without it, and that difference lives in the compose command, not in the image.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
