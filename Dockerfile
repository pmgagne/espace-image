# Stage 1: Builder
FROM python:3.14-slim-trixie AS builder

COPY --from=ghcr.io/astral-sh/uv:0.4.8 /uv /bin/uv

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies using uv sync
# This uses uv.lock for deterministic builds and avoids manual export to requirements.txt
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY app ./app
# Ensure the local `espima` package sources are available for installation
COPY espima ./espima
RUN uv pip install --no-deps .

# Stage 2: Runtime
FROM python:3.14-slim-trixie

WORKDIR /app

# Copy the environment from the builder
# uv creates the venv at .venv by default
COPY --from=builder /app/.venv /app/.venv

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo \
    zlib1g \
    libpng16-16 \
    && rm -rf /var/lib/apt/lists/*

# Copy the application code
COPY app ./app
# Copy Alembic config and migrations so runtime can run migrations
COPY alembic.ini .
COPY alembic ./alembic
COPY init_db.py .
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Ensure the virtual environment is on the PATH
ENV PATH="/app/.venv/bin:$PATH"

# Create data directory for volume mounting
RUN mkdir -p /app/data

# Environment variables
ENV PYTHONUNBUFFERED=1

# Expose the port
EXPOSE 8000

# Use entrypoint to run DB init + migrations, then start app
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
