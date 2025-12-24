# syntax=docker/dockerfile:1.7

########################
# Base image with common env
########################
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  PYTHONPATH=/app

WORKDIR /app

# System deps reused by all stages (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Install uv (fast installer)
RUN pip install --upgrade pip && pip install uv==0.4.17

########################
# Builder: install deps + run tests
########################
FROM base AS builder

# Use a local SQLite database for the test stage so the build doesn't require
# external DATABASE_URL secrets.
ENV DATABASE_URL=sqlite:////tmp/pytest.db

COPY requirements.txt ./
RUN uv pip install --system -r requirements.txt

COPY app ./app
COPY tests ./tests

# Run test suite; if it fails the build stops.
RUN pytest --maxfail=1 --disable-warnings -q

########################
# Runtime image (slim, non-root)
########################
FROM python:3.11-slim AS runtime

ARG UID=1000
ARG GID=1000

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  PYTHONPATH=/app

WORKDIR /app

# System deps for runtime (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Copy installed packages and binaries from builder to avoid reinstall
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy only necessary project files
COPY app ./app

# Create non-root user with configurable uid/gid
RUN groupadd -g ${GID} appgroup && \
  useradd -m -u ${UID} -g appgroup appuser && \
  chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
