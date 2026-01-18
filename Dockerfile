# Stage 1: Builder
FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment
RUN uv venv /app/.venv

# Install dependencies from requirements.txt
COPY requirements.txt ./
RUN uv pip install -r requirements.txt --python /app/.venv

# Stage 2: Runtime
FROM python:3.12-slim-bookworm

WORKDIR /app

# Copy the environment from the builder
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