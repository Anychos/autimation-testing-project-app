FROM python:3.12.13-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --create-home notifications
COPY pyproject.toml requirements.lock ./
COPY src ./src
COPY alembic.ini ./
COPY migrations ./migrations
COPY scripts ./scripts
COPY contracts ./contracts

FROM base AS test
COPY tests ./tests
RUN pip install --no-cache-dir -c requirements.lock ".[dev]"
ENV RUFF_CACHE_DIR=/tmp/ruff-cache
USER notifications
CMD ["pytest", "-q", "-p", "no:cacheprovider"]

FROM base AS runtime
RUN pip install --no-cache-dir -c requirements.lock .
USER notifications
EXPOSE 8000
CMD ["python", "-m", "notification_service"]
