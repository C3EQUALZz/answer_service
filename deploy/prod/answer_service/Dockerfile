# syntax=docker/dockerfile:1.7
#
# One image, three processes: api, worker and scheduler differ only in command.
# The healthcheck lives on the api service in compose, not here.

ARG PYTHON_VERSION=3.14

FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# hatch-vcs reads the version from git; without it the image reports 0.1.dev0.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && apt-get install --no-install-recommends -y git

# Keyed on the lockfile alone, so it survives every change to src/.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

RUN useradd --create-home --uid 1000 app

WORKDIR /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
# alembic reads revisions from disk, not from the installed package.
COPY --from=builder --chown=app:app /app/alembic.ini /app/alembic.ini
COPY --from=builder --chown=app:app /app/src /app/src

# Written by the api, read back later by the worker: must be a shared volume.
# logs/ too, because the process runs as `app` while /app belongs to root.
RUN mkdir -p /app/var/uploads /app/var/logs && chown -R app:app /app/var

USER app

EXPOSE 8080

CMD ["uvicorn", "answer_service.fastapi_app:create_fastapi_app", \
     "--factory", "--host", "0.0.0.0", "--port", "8080"]
