# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory in container
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies (if needed for lxml)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml first for better layer caching
COPY pyproject.toml ./

# Copy source code (needed for pip install -e .)
COPY stock_checker/ ./stock_checker/

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -e .

# Copy test files (optional, for testing in container)
COPY tests/ ./tests/

# Create data directory for SQLite database
RUN mkdir -p /app/data

# Set the database path to the volume mount
ENV DATABASE_PATH=/app/data/products.db

# Run the bot
CMD ["python", "-m", "stock_checker.bot"]
