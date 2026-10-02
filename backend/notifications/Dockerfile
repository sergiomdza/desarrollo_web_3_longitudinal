# ==========================================
# ETAPA 1 - Builder
# ==========================================
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=2.4.1 \
    POETRY_HOME=/opt/poetry \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    PATH="/opt/poetry/bin:$PATH"

WORKDIR /app

RUN python -m pip install --no-cache-dir \
    "poetry==${POETRY_VERSION}"

COPY pyproject.toml poetry.lock ./

RUN poetry install \
    --only main \
    --no-root


# ==========================================
# ETAPA 2 - Runtime
# ==========================================
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN useradd \
    --create-home \
    --uid 10001 \
    appuser

COPY --from=builder /app/.venv /app/.venv

COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser scripts ./scripts

USER appuser

EXPOSE 8000

CMD [
    "python",
    "-m",
    "uvicorn",
    "app.main:app",
    "--host",
    "0.0.0.0",
    "--port",
    "8000"
]
