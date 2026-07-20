# Production Dockerfile for Autonomous Multi-Agent Startup Generator
FROM python:3.11-slim as base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose backend port
EXPOSE 8000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/pipeline/status || exit 1

# Start FastAPI Uvicorn Server
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
