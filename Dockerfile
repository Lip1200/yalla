# syntax=docker/dockerfile:1.7
#
# Yalla backend container.
#
# Built around `uv` because that's what the project uses locally. We pull
# the official uv binary from its publisher image, install deps into a
# project-local virtualenv (which lives in /app/.venv), and run uvicorn
# as a non-root user.
#
# Build:    docker build -t yalla-backend .
# Run dev:  docker run --rm -p 8000:8000 --env-file .env yalla-backend
# Run prod: docker run -d --restart unless-stopped -p 80:8000 \
#               -e SUPABASE_URL=... -e SUPABASE_KEY=... \
#               -e API_SECRET_TOKEN=... -e CORS_ORIGINS=... \
#               yalla-backend

FROM python:3.13-slim AS base

# Avoid python writing .pyc files and buffering stdout (so logs stream
# correctly to the host).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy

# uv ships a tiny static binary in its publisher image — copy it instead
# of pip-installing uv (faster and simpler).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Step 1 — install dependencies only. Keeps this layer cacheable across
# source-only changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Step 2 — copy application source and install the project itself.
# Migrations are copied too so an operator inside the container can
# inspect / apply them via the Supabase SQL editor without leaving the
# image.
COPY src/ ./src/
COPY supabase/ ./supabase/
RUN uv sync --frozen --no-dev

# Run as a non-root user with a stable UID for OpenShift-style platforms.
RUN useradd --uid 1001 --create-home --shell /bin/bash yalla \
    && chown -R yalla:yalla /app
USER yalla

# Put the project venv first on PATH so `uvicorn` resolves to the one we
# just installed.
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Default to a single worker — most PaaS hosts (Fly, Railway, Render)
# scale via instances, not workers. Override with `--workers N` for a
# bigger VPS or by passing CMD args at `docker run`.
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
