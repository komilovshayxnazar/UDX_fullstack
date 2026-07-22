# syntax=docker/dockerfile:1.7

# ── Stage 1 · builder ───────────────────────────────────────────────────
# Compile wheels for anything with C extensions (bcrypt, cryptography,
# numpy, scikit-learn) so the runtime image doesn't need gcc / g++.
FROM python:3.12-slim-bookworm AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libssl-dev \
        libbz2-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
RUN pip wheel --wheel-dir=/wheels -r requirements.txt


# ── Stage 2 · runtime ───────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# curl is used by the compose healthcheck fallback; tini reaps orphan
# child processes when uvicorn spawns worker greenlets.
RUN apt-get update \
 && apt-get install -y --no-install-recommends tini curl \
 && rm -rf /var/lib/apt/lists/*

# Non-root user. UID 10001 is arbitrary but stable so bind-mounted
# volumes get consistent ownership across restarts.
RUN groupadd --system --gid 10001 udx \
 && useradd  --system --uid 10001 --gid udx --home /app udx

WORKDIR /app
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
 && rm -rf /wheels

# Copy the source last so re-installs don't bust the wheel cache.
COPY --chown=udx:udx . /app

# Runtime state lives in named volumes attached by docker-compose so a
# writable dir must exist even when volumes are absent. /app/logs holds
# the JSON-line log tailed by the Distributed Log Aggregator's agent.
RUN mkdir -p /app/uploads /app/state /app/logs \
 && chown -R udx:udx /app

USER udx

EXPOSE 8000

ENTRYPOINT ["/usr/bin/tini", "--"]

# Apply pending Alembic migrations before serving traffic — schema is
# owned by Alembic, not app startup, so this runs once per container
# start rather than racing across the 4 uvicorn workers below.
# --proxy-headers so X-Forwarded-For / X-Forwarded-Proto from the
# nginx front-end are trusted for logging + audit.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers --forwarded-allow-ips '*'"]
