# Stage 1: Builder
FROM python:3.13-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

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

# Stage 2: Runtime
FROM python:3.13-slim-bookworm

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
COPY init_db.py .

# Ensure the virtual environment is on the PATH
ENV PATH="/app/.venv/bin:$PATH"

# Create data directory for volume mounting
RUN mkdir -p /app/data

# Environment variables
ENV PYTHONUNBUFFERED=1

# Expose the port
EXPOSE 8000

# Run the application
CMD ["sh", "-c", "python init_db.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]