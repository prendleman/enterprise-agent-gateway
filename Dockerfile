# syntax=docker/dockerfile:1

# --- builder: install dependencies into a virtualenv ---
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir uv \
    && uv venv /opt/venv \
    && uv pip install --python /opt/venv/bin/python ".[providers]"

# --- runtime: non-root, minimal image ---
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_HOME=/app

WORKDIR ${APP_HOME}

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app \
    && mkdir -p ${APP_HOME}/artifacts ${APP_HOME}/datasets ${APP_HOME}/config \
    && chown -R app:app ${APP_HOME}

COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app config ./config
COPY --chown=app:app datasets ./datasets
COPY --chown=app:app src ./src

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health/live || exit 1

CMD ["uvicorn", "agent_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
